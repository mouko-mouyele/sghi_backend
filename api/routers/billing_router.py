import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import Router
from ninja.errors import HttpError

from accounts.models import User
from api.auth import jwt_auth
from api.pagination import paginate_queryset, paginated
from api.permissions import require_role
from api.schemas import (
    InvoiceCreateIn,
    InvoiceLineIn,
    InvoiceLineUpdateIn,
    InvoiceMontantUpdateIn,
    InvoiceOut,
    MessageOut,
    MobileMoneyConfirmIn,
    MobileMoneyInitIn,
    MobileMoneyPhoneApproveIn,
    MobileMoneyStatusOut,
    MobileMoneyTransactionOut,
    PaginatedInvoicesOut,
    PaymentIn,
)
from billing.mobile_money import (
    USSD_HINTS,
    detect_operateur,
    format_phone_display,
    generate_push_code,
    montant_restant,
    new_transaction_reference,
    normalize_phone,
    phones_equal,
    validate_confirmation_pin,
)
from billing.models import AccountingJournal, Invoice, InvoiceLine, MobileMoneyTransaction, PatientInsurance, Payment
from billing.services import (
    apply_payment,
    assert_invoice_editable,
    invoice_to_dict,
    mark_unpaid,
    refresh_invoice_status,
    resolve_amount_edit,
)
from clinical.models import Hospitalization, Patient
from core.pdf import generate_invoice_pdf
from laboratory.models import LabOrder

router = Router(tags=['Facturation & Finances'])


def _calc_hospitalization_cost(hosp: Hospitalization) -> list[dict]:
    lines = [{'type_ligne': 'NUITEE', 'libelle': 'Nuitée hospitalisation', 'quantite': 1, 'prix_unitaire': Decimal('25000')}]
    for exam in LabOrder.objects.filter(hospitalisation=hosp, statut='PUBLIE'):
        lines.append({
            'type_ligne': 'EXAMEN', 'libelle': exam.examen.libelle,
            'quantite': 1, 'prix_unitaire': exam.examen.prix,
        })
    return lines


def _invoice_qs():
    return Invoice.objects.select_related('patient').prefetch_related('lignes', 'paiements')


def _recalc_invoice(invoice: Invoice) -> None:
    total = invoice.lignes.aggregate(t=Sum('montant'))['t'] or Decimal('0')
    assurance = PatientInsurance.objects.filter(patient=invoice.patient, actif=True).first()
    montant_assurance = Decimal('0')
    if assurance:
        montant_assurance = total * assurance.assurance.taux_prise_en_charge / Decimal('100')
    invoice.montant_total = total
    invoice.montant_assurance = montant_assurance
    invoice.montant_patient = total - montant_assurance
    invoice.save()


@router.get('/factures', response=PaginatedInvoicesOut, auth=jwt_auth)
def list_invoices(request, patient_id: int = 0, statut: str = '', search: str = '',
                  page: int = 1, page_size: int = 15):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    qs = _invoice_qs().order_by('-created_at')
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if statut:
        qs = qs.filter(statut=statut)
    if search:
        qs = qs.filter(
            Q(numero__icontains=search)
            | Q(patient__nom__icontains=search)
            | Q(patient__prenom__icontains=search)
            | Q(patient__numero_dossier__icontains=search),
        )
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([InvoiceOut(**invoice_to_dict(i)) for i in items], meta)


@router.get('/factures/{invoice_id}', response=InvoiceOut, auth=jwt_auth)
def get_invoice(request, invoice_id: int):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.post('/factures', response=InvoiceOut, auth=jwt_auth)
def create_invoice(request, payload: InvoiceCreateIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    patient = get_object_or_404(Patient, id=payload.patient_id)
    numero = f'FAC-{dj_tz.now().year}-{uuid.uuid4().hex[:8].upper()}'
    invoice = Invoice.objects.create(
        numero=numero, patient=patient,
        hospitalisation_id=payload.hospitalisation_id,
        statut=Invoice.Statut.BROUILLON,
    )
    if payload.hospitalisation_id:
        hosp = get_object_or_404(Hospitalization, id=payload.hospitalisation_id)
        for lg in _calc_hospitalization_cost(hosp):
            InvoiceLine.objects.create(facture=invoice, **lg)
    _recalc_invoice(invoice)
    invoice.refresh_from_db()
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.post('/factures/{invoice_id}/lignes', response=InvoiceOut, auth=jwt_auth)
def add_invoice_line(request, invoice_id: int, payload: InvoiceLineIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    assert_invoice_editable(invoice)
    data = payload.dict()
    reset = data.pop('reinitialiser_paiements', False)
    InvoiceLine.objects.create(facture=invoice, **data)
    _recalc_invoice(invoice)
    invoice.refresh_from_db()
    resolve_amount_edit(invoice, invoice.montant_patient, reset)
    refresh_invoice_status(invoice)
    invoice.refresh_from_db()
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.patch('/factures/{invoice_id}/lignes/{line_id}', response=InvoiceOut, auth=jwt_auth)
def update_invoice_line(request, invoice_id: int, line_id: int, payload: InvoiceLineUpdateIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    assert_invoice_editable(invoice)
    line = get_object_or_404(InvoiceLine, id=line_id, facture=invoice)
    data = payload.dict(exclude_unset=True)
    reset = data.pop('reinitialiser_paiements', False)
    if 'libelle' in data and data['libelle'] is not None:
        line.libelle = data['libelle']
    if 'quantite' in data and data['quantite'] is not None:
        if data['quantite'] < 1:
            raise HttpError(400, 'La quantité doit être au moins 1')
        line.quantite = data['quantite']
    if 'prix_unitaire' in data and data['prix_unitaire'] is not None:
        if data['prix_unitaire'] < 0:
            raise HttpError(400, 'Le prix unitaire ne peut pas être négatif')
        line.prix_unitaire = data['prix_unitaire']
    line.save()
    _recalc_invoice(invoice)
    invoice.refresh_from_db()
    resolve_amount_edit(invoice, invoice.montant_patient, reset)
    refresh_invoice_status(invoice)
    invoice.refresh_from_db()
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.delete('/factures/{invoice_id}/lignes/{line_id}', response=InvoiceOut, auth=jwt_auth)
def delete_invoice_line(request, invoice_id: int, line_id: int, reinitialiser_paiements: bool = False):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    assert_invoice_editable(invoice)
    line = get_object_or_404(InvoiceLine, id=line_id, facture=invoice)
    if invoice.lignes.count() <= 1:
        raise HttpError(400, 'La facture doit conserver au moins une ligne')
    line.delete()
    _recalc_invoice(invoice)
    invoice.refresh_from_db()
    resolve_amount_edit(invoice, invoice.montant_patient, reinitialiser_paiements)
    refresh_invoice_status(invoice)
    invoice.refresh_from_db()
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.patch('/factures/{invoice_id}/montant', response=InvoiceOut, auth=jwt_auth)
def update_invoice_amount(request, invoice_id: int, payload: InvoiceMontantUpdateIn):
    """Ajuste le montant dû par le patient (remise, correction comptable)."""
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    assert_invoice_editable(invoice)
    resolve_amount_edit(invoice, payload.montant_patient, payload.reinitialiser_paiements)
    invoice.montant_patient = payload.montant_patient
    invoice.montant_total = payload.montant_patient + invoice.montant_assurance
    invoice.save(update_fields=['montant_patient', 'montant_total'])
    refresh_invoice_status(invoice)
    motif = f' — {payload.motif}' if payload.motif else ''
    AccountingJournal.objects.create(
        reference=f'AJ-{uuid.uuid4().hex[:8].upper()}',
        type_operation='AJUSTEMENT',
        debit=Decimal('0'),
        credit=Decimal('0'),
        libelle=f'Ajustement montant facture {invoice.numero}{motif}',
        facture=invoice,
    )
    invoice.refresh_from_db()
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.post('/factures/{invoice_id}/emettre', response=MessageOut, auth=jwt_auth)
def emit_invoice(request, invoice_id: int):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN)
    invoice = get_object_or_404(_invoice_qs(), id=invoice_id)
    if not invoice.lignes.exists():
        raise HttpError(400, 'Ajoutez au moins une ligne avant émission')
    invoice.statut = Invoice.Statut.EMISE
    invoice.emise_le = dj_tz.now()
    lignes = [{'libelle': l.libelle, 'quantite': l.quantite, 'montant': l.montant} for l in invoice.lignes.all()]
    pdf = generate_invoice_pdf(
        numero=invoice.numero,
        patient_nom=f'{invoice.patient.prenom} {invoice.patient.nom}',
        lignes=lignes, montant_total=invoice.montant_total, montant_paye=invoice.montant_paye,
    )
    invoice.pdf.save(f'{invoice.numero}.pdf', ContentFile(pdf), save=False)
    invoice.save()
    AccountingJournal.objects.create(
        reference=f'JNL-{invoice.numero}', type_operation='FACTURATION',
        debit=invoice.montant_total, credit=Decimal('0'),
        libelle=f'Émission facture {invoice.numero}', facture=invoice,
    )
    from core.patient_mail import notify_invoice_issued
    notify_invoice_issued(invoice)
    return MessageOut(message='Facture émise — patient notifié par email')


@router.post('/factures/{invoice_id}/paiements', response=MessageOut, auth=jwt_auth)
def record_payment(request, invoice_id: int, payload: PaymentIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN, User.Role.RECEPTIONNISTE)
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.statut == Invoice.Statut.ANNULEE:
        raise HttpError(400, 'Facture annulée')
    if invoice.statut == Invoice.Statut.BROUILLON:
        raise HttpError(400, 'Émettez la facture avant encaissement')
    reste = montant_restant(invoice)
    if payload.montant <= 0 or payload.montant > reste:
        raise HttpError(400, f'Montant invalide. Reste à payer : {reste} FCFA')
    apply_payment(
        invoice, payload.montant, payload.mode, payload.reference, encaisse_par=request.auth,
    )
    invoice.refresh_from_db()
    return MessageOut(
        message='Paiement enregistré',
        detail=f'Statut : {invoice.statut} — Reste : {montant_restant(invoice)} FCFA',
    )


@router.post('/factures/{invoice_id}/marquer-impayee', response=MessageOut, auth=jwt_auth)
def mark_invoice_unpaid(request, invoice_id: int):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN)
    invoice = get_object_or_404(Invoice, id=invoice_id)
    try:
        mark_unpaid(invoice)
    except ValueError as e:
        raise HttpError(400, str(e)) from e
    return MessageOut(message='Facture marquée impayée', detail=invoice.numero)


@router.post('/factures/{invoice_id}/marquer-payee', response=MessageOut, auth=jwt_auth)
def mark_invoice_paid(request, invoice_id: int):
    """Solde manuel — comptable confirme le règlement intégral."""
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN)
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.statut == Invoice.Statut.ANNULEE:
        raise HttpError(400, 'Facture annulée')
    reste = montant_restant(invoice)
    if reste > 0:
        apply_payment(invoice, reste, 'ESPECES', f'MANUEL-{uuid.uuid4().hex[:6].upper()}', encaisse_par=request.auth)
    else:
        invoice.statut = Invoice.Statut.PAYEE
        invoice.save(update_fields=['statut'])
    return MessageOut(message='Facture marquée payée')


@router.post('/factures/{invoice_id}/mobile-money/initier', response=MobileMoneyTransactionOut, auth=jwt_auth)
def staff_init_mobile_money(request, invoice_id: int, payload: MobileMoneyInitIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    return _init_mobile_payment(get_object_or_404(_invoice_qs(), id=invoice_id), payload)


@router.post('/factures/{invoice_id}/mobile-money/confirmer', response=MobileMoneyStatusOut, auth=jwt_auth)
def staff_confirm_mobile_money(request, invoice_id: int, payload: MobileMoneyConfirmIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    return _confirm_mobile_payment(payload)


@router.get('/mobile-money/{transaction_id}/statut', response=MobileMoneyStatusOut, auth=jwt_auth)
def mobile_money_status(request, transaction_id: int):
    require_role(
        request.auth,
        User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN, User.Role.PATIENT,
    )
    return _transaction_status(transaction_id, request.auth)


@router.post('/mobile-money/{transaction_id}/approuver', response=MobileMoneyStatusOut, auth=jwt_auth)
def staff_approve_mobile_money(request, transaction_id: int, payload: MobileMoneyPhoneApproveIn):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.RECEPTIONNISTE, User.Role.ADMIN, User.Role.PATIENT)
    tx = get_object_or_404(
        MobileMoneyTransaction.objects.select_related('facture', 'facture__patient'),
        id=transaction_id,
    )
    if request.auth.role == User.Role.PATIENT and tx.patient.user_id != request.auth.id:
        raise HttpError(403, 'Accès refusé')
    return _approve_from_phone(tx, payload.numero_mobile)


def _tx_response(tx: MobileMoneyTransaction, montant, operateur, label) -> MobileMoneyTransactionOut:
    return MobileMoneyTransactionOut(
        id=tx.id,
        reference=tx.reference,
        operateur=operateur,
        numero_mobile=tx.numero_mobile,
        numero_mobile_affiche=format_phone_display(tx.numero_mobile),
        montant=montant,
        statut=tx.statut,
        message=f'Notification {label} envoyée au {format_phone_display(tx.numero_mobile)}.',
        instruction_ussd=USSD_HINTS[operateur],
        expire_le=tx.expire_le,
        facture_id=tx.facture_id,
        facture_numero=tx.facture.numero,
        code_push=tx.code_push,
        push_message=(
            f'CHU Brazzaville : payez {montant} FCFA. '
            f'Code {tx.code_push}. Validez sur ce numéro ou composez {USSD_HINTS[operateur].split("—")[0].strip()}.'
        ),
    )


def _init_mobile_payment(invoice: Invoice, payload: MobileMoneyInitIn) -> MobileMoneyTransactionOut:
    if invoice.statut in (Invoice.Statut.BROUILLON, Invoice.Statut.ANNULEE, Invoice.Statut.PAYEE):
        raise HttpError(400, 'Cette facture ne peut pas être payée en ligne')
    reste = montant_restant(invoice)
    if reste <= 0:
        raise HttpError(400, 'Facture déjà soldée')
    montant = payload.montant or reste
    if montant <= 0 or montant > reste:
        raise HttpError(400, f'Montant invalide. Maximum : {reste} FCFA')

    phone = normalize_phone(payload.numero_mobile)
    operateur = detect_operateur(phone)

    MobileMoneyTransaction.objects.filter(
        facture=invoice,
        statut=MobileMoneyTransaction.Statut.EN_ATTENTE_CONFIRMATION,
    ).update(statut=MobileMoneyTransaction.Statut.EXPIRE)

    ref = new_transaction_reference()
    push_code = generate_push_code()
    tx = MobileMoneyTransaction.objects.create(
        facture=invoice,
        patient=invoice.patient,
        numero_mobile=phone,
        operateur=operateur,
        montant=montant,
        reference=ref,
        statut=MobileMoneyTransaction.Statut.EN_ATTENTE_CONFIRMATION,
        message_operateur=f'Demande de {montant} FCFA envoyée au {format_phone_display(phone)}',
        expire_le=dj_tz.now() + timedelta(minutes=10),
        code_push=push_code,
    )
    label = 'MTN MoMo' if operateur == 'MTN' else 'Airtel Money'
    from core.patient_mail import notify_mobile_money_pending
    notify_mobile_money_pending(tx)
    return _tx_response(tx, montant, operateur, label)


def _check_tx_active(tx: MobileMoneyTransaction) -> None:
    if tx.statut == MobileMoneyTransaction.Statut.CONFIRME:
        return
    if tx.statut != MobileMoneyTransaction.Statut.EN_ATTENTE_CONFIRMATION:
        raise HttpError(400, 'Transaction expirée ou annulée')
    if dj_tz.now() > tx.expire_le:
        tx.statut = MobileMoneyTransaction.Statut.EXPIRE
        tx.save(update_fields=['statut'])
        raise HttpError(400, 'Délai dépassé. Relancez le paiement.')


def _finalize_mobile_payment(tx: MobileMoneyTransaction) -> MobileMoneyStatusOut:
    mode = 'MTN_MOMO' if tx.operateur == 'MTN' else 'AIRTEL_MONEY'
    payment = apply_payment(
        tx.facture,
        tx.montant,
        mode,
        reference=tx.reference,
        numero_mobile=tx.numero_mobile,
        operateur=tx.operateur,
    )
    tx.statut = MobileMoneyTransaction.Statut.CONFIRME
    tx.confirme_le = dj_tz.now()
    tx.paiement = payment
    tx.message_operateur = f'Paiement confirmé depuis {format_phone_display(tx.numero_mobile)}.'
    tx.save()
    return _transaction_status(tx.id, None)


def _approve_from_phone(tx: MobileMoneyTransaction, raw_phone: str) -> MobileMoneyStatusOut:
    if tx.statut == MobileMoneyTransaction.Statut.CONFIRME:
        return _transaction_status(tx.id, None)
    _check_tx_active(tx)
    if not phones_equal(raw_phone, tx.numero_mobile):
        raise HttpError(
            400,
            'Ce numéro ne correspond pas à la demande envoyée. '
            'Saisissez le même numéro Mobile Money que lors de l\'étape précédente.',
        )
    tx.approuve_telephone_le = dj_tz.now()
    tx.save(update_fields=['approuve_telephone_le'])
    return _finalize_mobile_payment(tx)


def _confirm_mobile_payment(payload: MobileMoneyConfirmIn) -> MobileMoneyStatusOut:
    tx = get_object_or_404(
        MobileMoneyTransaction.objects.select_related('facture', 'facture__patient'),
        id=payload.transaction_id,
    )
    if tx.statut == MobileMoneyTransaction.Statut.CONFIRME:
        return _transaction_status(tx.id, None)
    _check_tx_active(tx)

    code = (payload.code_push or payload.code_pin or '').strip()
    if tx.approuve_telephone_le and code.isdigit() and 4 <= len(code) <= 6:
        return _finalize_mobile_payment(tx)
    validate_confirmation_pin(
        code,
        tx.numero_mobile,
        push_code=tx.code_push,
        phone_approved=bool(tx.approuve_telephone_le),
    )
    return _finalize_mobile_payment(tx)


def _transaction_status(transaction_id: int, user) -> MobileMoneyStatusOut:
    tx = get_object_or_404(
        MobileMoneyTransaction.objects.select_related('facture'),
        id=transaction_id,
    )
    if user and getattr(user, 'role', None) == User.Role.PATIENT:
        if tx.patient.user_id != user.id:
            raise HttpError(403, 'Accès refusé')
    invoice = tx.facture
    messages = {
        MobileMoneyTransaction.Statut.EN_ATTENTE_CONFIRMATION: 'En attente de validation sur votre téléphone…',
        MobileMoneyTransaction.Statut.CONFIRME: 'Paiement confirmé avec succès.',
        MobileMoneyTransaction.Statut.REFUSE: 'Paiement refusé.',
        MobileMoneyTransaction.Statut.EXPIRE: 'Transaction expirée.',
    }
    return MobileMoneyStatusOut(
        id=tx.id,
        statut=tx.statut,
        message=messages.get(tx.statut, tx.message_operateur),
        facture_statut=invoice.statut,
        montant_paye=invoice.montant_paye,
        montant_restant=montant_restant(invoice),
    )


@router.get('/journal', auth=jwt_auth)
def accounting_journal(request, page: int = 1, page_size: int = 20):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN)
    qs = AccountingJournal.objects.order_by('-created_at')
    items, meta = paginate_queryset(qs, page, page_size)
    rows = [
        {
            'reference': j.reference,
            'type_operation': j.type_operation,
            'debit': j.debit,
            'credit': j.credit,
            'libelle': j.libelle,
            'created_at': j.created_at,
        }
        for j in items
    ]
    return paginated(rows, meta)
