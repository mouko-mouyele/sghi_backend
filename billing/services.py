"""Services facturation partagés."""
import uuid
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone as dj_tz

from billing.models import AccountingJournal, Invoice, Payment
from billing.mobile_money import montant_restant


def invoice_to_dict(invoice: Invoice, include_lines: bool = False) -> dict:
    reste = montant_restant(invoice)
    paye = invoice.statut == Invoice.Statut.PAYEE
    data = {
        'id': invoice.id,
        'numero': invoice.numero,
        'patient_id': invoice.patient_id,
        'patient_nom': f'{invoice.patient.prenom} {invoice.patient.nom}',
        'patient_dossier': invoice.patient.numero_dossier,
        'statut': invoice.statut,
        'statut_libelle': _statut_libelle(invoice.statut),
        'est_payee': paye,
        'est_impayee': invoice.statut in (Invoice.Statut.EMISE, Invoice.Statut.PARTIEL),
        'montant_total': invoice.montant_total,
        'montant_assurance': invoice.montant_assurance,
        'montant_patient': invoice.montant_patient,
        'montant_paye': invoice.montant_paye,
        'montant_restant': reste,
        'emise_le': invoice.emise_le,
        'created_at': invoice.created_at,
        'pdf_url': invoice.pdf.url if invoice.pdf else '',
    }
    if include_lines:
        data['lignes'] = [
            {
                'id': l.id,
                'type_ligne': l.type_ligne,
                'libelle': l.libelle,
                'quantite': l.quantite,
                'prix_unitaire': l.prix_unitaire,
                'montant': l.montant,
            }
            for l in invoice.lignes.all()
        ]
        data['paiements'] = [
            {
                'id': p.id,
                'montant': p.montant,
                'mode': p.mode,
                'reference': p.reference,
                'numero_mobile': p.numero_mobile,
                'operateur': p.operateur,
                'statut': p.statut,
                'created_at': p.created_at,
            }
            for p in invoice.paiements.filter(statut=Payment.Statut.VALIDE).order_by('-created_at')
        ]
    return data


def _statut_libelle(statut: str) -> str:
    return {
        Invoice.Statut.BROUILLON: 'Brouillon',
        Invoice.Statut.EMISE: 'Impayée',
        Invoice.Statut.PARTIEL: 'Partiellement payée',
        Invoice.Statut.PAYEE: 'Payée',
        Invoice.Statut.ANNULEE: 'Annulée',
    }.get(statut, statut)


def apply_payment(invoice: Invoice, montant: Decimal, mode: str, reference: str = '',
                  numero_mobile: str = '', operateur: str = '', encaisse_par=None) -> Payment:
    payment = Payment.objects.create(
        facture=invoice,
        montant=montant,
        mode=mode,
        reference=reference,
        numero_mobile=numero_mobile,
        operateur=operateur,
        statut=Payment.Statut.VALIDE,
        encaisse_par=encaisse_par,
    )
    invoice.montant_paye += montant
    if invoice.montant_paye >= invoice.montant_patient:
        invoice.statut = Invoice.Statut.PAYEE
    else:
        invoice.statut = Invoice.Statut.PARTIEL
    invoice.save(update_fields=['montant_paye', 'statut'])
    AccountingJournal.objects.create(
        reference=f'PAY-{uuid.uuid4().hex[:8].upper()}',
        type_operation='PAIEMENT',
        debit=Decimal('0'),
        credit=montant,
        libelle=f'Paiement {mode} facture {invoice.numero}',
        facture=invoice,
    )
    try:
        from core.patient_mail import notify_payment_received
        notify_payment_received(invoice, payment)
    except Exception:
        pass
    return payment


def mark_unpaid(invoice: Invoice) -> None:
    if invoice.statut == Invoice.Statut.ANNULEE:
        raise ValueError('Facture annulée')
    invoice.montant_paye = Decimal('0')
    invoice.statut = Invoice.Statut.EMISE if invoice.emise_le else Invoice.Statut.BROUILLON
    invoice.save(update_fields=['montant_paye', 'statut'])


def assert_invoice_editable(invoice: Invoice) -> None:
    from ninja.errors import HttpError
    if invoice.statut == Invoice.Statut.ANNULEE:
        raise HttpError(400, 'Facture annulée — modification impossible')


def resolve_amount_edit(invoice: Invoice, new_montant_patient: Decimal, reset_payments: bool = False) -> None:
    """Valide ou réinitialise les encaissements avant un nouvel montant."""
    from ninja.errors import HttpError
    if new_montant_patient < 0:
        raise HttpError(400, 'Montant invalide')
    if new_montant_patient < invoice.montant_paye:
        if reset_payments:
            invoice.montant_paye = Decimal('0')
            invoice.save(update_fields=['montant_paye'])
        else:
            raise HttpError(
                400,
                f'Impossible : {new_montant_patient} FCFA est inférieur au déjà encaissé '
                f'({invoice.montant_paye} FCFA). '
                f'Cochez « Réinitialiser les encaissements » ou cliquez « Marquer impayée » d\'abord.',
            )


def assert_amount_not_below_paid(invoice: Invoice, new_montant_patient: Decimal) -> None:
    resolve_amount_edit(invoice, new_montant_patient, reset_payments=False)


def refresh_invoice_status(invoice: Invoice) -> None:
    if invoice.montant_paye <= 0:
        if invoice.emise_le:
            invoice.statut = Invoice.Statut.EMISE
        else:
            invoice.statut = Invoice.Statut.BROUILLON
    elif invoice.montant_paye >= invoice.montant_patient:
        invoice.statut = Invoice.Statut.PAYEE
    else:
        invoice.statut = Invoice.Statut.PARTIEL
    invoice.save(update_fields=['statut'])
