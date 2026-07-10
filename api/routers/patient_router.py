from urllib.parse import quote

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import Router
from ninja.errors import HttpError

from django.conf import settings
from accounts.models import User
from api.auth import jwt_auth
from api.permissions import require_role
from api.schemas import (
    ChatMessageIn,
    ChatMessageOut,
    InvoiceOut,
    MobileMoneyConfirmIn,
    MobileMoneyInitIn,
    MobileMoneyPhoneApproveIn,
    MobileMoneyStatusOut,
    MobileMoneyTransactionOut,
    PatientAppointmentDetailOut,
    PatientCardFullOut,
    PatientCardPdfLinkOut,
    PatientCarePlanOut,
    PatientCareItemOut,
    PatientConsultationSummaryOut,
    PatientConversationOut,
    PatientDashboardOut,
    PatientEstablishmentOut,
    PatientLabResultOut,
    PatientOut,
    PatientReminderOut,
    PrescriptionOut,
    ReminderIn,
    ReminderUpdateIn,
    PharmacyRequestIn,
    PharmacyRequestOut,
    MedicationOut,
)
from billing.mobile_money import montant_restant
from billing.models import Invoice, MobileMoneyTransaction
from billing.services import invoice_to_dict
from api.routers.billing_router import (
    _approve_from_phone,
    _confirm_mobile_payment,
    _init_mobile_payment,
    _transaction_status,
)
from api.routers.pharmacy_router import create_patient_pharmacy_request, list_medications, _request_out
from core.appointment_mail import notify_appointment_cancelled
from clinical.models import (
    Appointment,
    ChatMessage,
    Consultation,
    Conversation,
    Hospitalization,
    MedicationReminder,
    NursingCare,
    Patient,
    PatientCardToken,
    Prescription,
)
from core.models import HospitalInfo
from core.patient_care_plan import build_patient_care_plan
from core.patient_card import (
    build_patient_full_payload,
    build_qr_scan_url,
    generate_and_save_patient_card_pdf,
    get_or_create_card_token,
)
from laboratory.models import LabResult

router = Router(tags=['Portail Patient'])


def _establishment_payload(info: HospitalInfo) -> dict:
    query = info.google_maps_query or info.nom_etablissement
    encoded = quote(query)
    lat, lng = info.latitude, info.longitude
    return {
        'nom_etablissement': info.nom_etablissement,
        'adresse': info.adresse,
        'telephone': info.telephone,
        'email': info.email,
        'horaires': info.horaires,
        'urgences_telephone': info.urgences_telephone,
        'description': info.description,
        'site_web': info.site_web,
        'latitude': lat,
        'longitude': lng,
        'google_maps_query': query,
        'google_maps_embed_url': f'https://maps.google.com/maps?q={encoded}&hl=fr&z=16&output=embed',
        'google_maps_directions_url': (
            f'https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving'
        ),
    }


def _get_patient_user(request) -> Patient:
    require_role(request.auth, User.Role.PATIENT)
    return get_object_or_404(Patient, user=request.auth)


@router.get('/etablissement', response=PatientEstablishmentOut, auth=None)
def public_establishment_info(request):
    """Informations publiques — CHU Brazzaville, carte Google Maps."""
    info = HospitalInfo.get_instance()
    return _establishment_payload(info)


@router.get('/patient/etablissement', response=PatientEstablishmentOut, auth=jwt_auth)
def patient_establishment_info(request):
    _get_patient_user(request)
    info = HospitalInfo.get_instance()
    return _establishment_payload(info)


@router.get('/patient/moi', response=PatientOut, auth=jwt_auth)
def patient_profile(request):
    return _get_patient_user(request)


@router.get('/patient/tableau-de-bord', response=PatientDashboardOut, auth=jwt_auth)
def patient_dashboard(request):
    patient = _get_patient_user(request)
    now = dj_tz.now()
    upcoming = Appointment.objects.filter(
        patient=patient,
        statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
        date_heure__gte=now,
    ).select_related('medecin').order_by('date_heure')
    next_rdv = upcoming.first()
    prochain = None
    if next_rdv:
        prochain = {
            'id': next_rdv.id,
            'date_heure': next_rdv.date_heure.isoformat(),
            'motif': next_rdv.motif,
            'medecin': f'Dr {next_rdv.medecin.first_name} {next_rdv.medecin.last_name}',
            'specialty': next_rdv.medecin.specialty,
        }
    impayees = Invoice.objects.filter(
        patient=patient,
        statut__in=[Invoice.Statut.EMISE, Invoice.Statut.PARTIEL],
    )
    montant_du = sum(montant_restant(i) for i in impayees)
    return PatientDashboardOut(
        prochain_rdv=prochain,
        rdv_a_venir=upcoming.count(),
        resultats_disponibles=LabResult.objects.filter(
            commande__patient=patient, valide=True,
        ).count(),
        rappels_actifs=MedicationReminder.objects.filter(patient=patient, actif=True).count(),
        hospitalisation_active=Hospitalization.objects.filter(
            patient=patient, statut=Hospitalization.Statut.ACTIVE,
        ).exists(),
        factures_impayees=impayees.count(),
        montant_du=montant_du,
    )


@router.get('/patient/rendez-vous', response=list[PatientAppointmentDetailOut], auth=jwt_auth)
def patient_appointments(request):
    patient = _get_patient_user(request)
    rdvs = Appointment.objects.filter(patient=patient).select_related('medecin').order_by('-date_heure')
    return [
        PatientAppointmentDetailOut(
            id=r.id, medecin_id=r.medecin_id,
            medecin_nom=f'Dr {r.medecin.first_name} {r.medecin.last_name}',
            medecin_specialty=r.medecin.specialty or 'Médecine générale',
            date_heure=r.date_heure, motif=r.motif, statut=r.statut,
            duree_minutes=r.duree_minutes,
        ) for r in rdvs[:50]
    ]


@router.delete('/patient/rendez-vous/{rdv_id}', auth=jwt_auth)
def patient_cancel_appointment(request, rdv_id: int):
    patient = _get_patient_user(request)
    rdv = get_object_or_404(Appointment, id=rdv_id, patient=patient)
    if rdv.statut in [Appointment.Statut.TERMINE, Appointment.Statut.ANNULE]:
        raise HttpError(400, 'Ce rendez-vous ne peut plus être annulé')
    rdv.statut = Appointment.Statut.ANNULE
    rdv.save(update_fields=['statut', 'updated_at'])
    notify_appointment_cancelled(rdv, reason='Annulé par le patient')
    return {'message': 'Demande annulée — l\'accueil a été notifié'}


@router.get('/patient/dossier/consultations', response=list[PatientConsultationSummaryOut], auth=jwt_auth)
def patient_consultations(request):
    patient = _get_patient_user(request)
    consultations = Consultation.objects.filter(
        patient=patient, validee=True,
    ).select_related('medecin').order_by('-date_consultation')[:30]
    result = []
    for c in consultations:
        prescriptions = [
            PrescriptionOut(
                id=p.id, consultation_id=p.consultation_id,
                medicament_nom=p.medicament_nom, posologie=p.posologie,
                validee=p.validee, verrouillee=p.verrouillee,
            ) for p in Prescription.objects.filter(consultation=c, validee=True)
        ]
        result.append(PatientConsultationSummaryOut(
            id=c.id, date_consultation=c.date_consultation,
            diagnostic_cim10=c.diagnostic_cim10, diagnostic_libelle=c.diagnostic_libelle,
            medecin_nom=f'Dr {c.medecin.first_name} {c.medecin.last_name}',
            prescriptions=prescriptions,
        ))
    return result


@router.get('/patient/plan-soins', response=PatientCarePlanOut, auth=jwt_auth)
def patient_care_plan(request):
    patient = _get_patient_user(request)
    return build_patient_care_plan(patient)


@router.get('/patient/rappels-medicaments', response=list[PatientReminderOut], auth=jwt_auth)
def patient_reminders(request):
    patient = _get_patient_user(request)
    return [
        PatientReminderOut(
            id=r.id, medicament=r.medicament, heure_prise=r.heure_prise, actif=r.actif,
        ) for r in MedicationReminder.objects.filter(patient=patient).order_by('heure_prise')
    ]


@router.post('/patient/rappels-medicaments', auth=jwt_auth)
def patient_create_reminder(request, payload: ReminderIn):
    patient = _get_patient_user(request)
    r = MedicationReminder.objects.create(
        patient=patient, prescription_id=payload.prescription_id,
        medicament=payload.medicament, heure_prise=payload.heure_prise,
    )
    return PatientReminderOut(
        id=r.id, medicament=r.medicament, heure_prise=r.heure_prise, actif=r.actif,
    )


@router.patch('/patient/rappels-medicaments/{reminder_id}', response=PatientReminderOut, auth=jwt_auth)
def patient_update_reminder(request, reminder_id: int, payload: ReminderUpdateIn):
    patient = _get_patient_user(request)
    r = get_object_or_404(MedicationReminder, id=reminder_id, patient=patient)
    if payload.actif is not None:
        r.actif = payload.actif
        r.save(update_fields=['actif', 'updated_at'])
    return PatientReminderOut(
        id=r.id, medicament=r.medicament, heure_prise=r.heure_prise, actif=r.actif,
    )


@router.delete('/patient/rappels-medicaments/{reminder_id}', auth=jwt_auth)
def patient_delete_reminder(request, reminder_id: int):
    patient = _get_patient_user(request)
    r = get_object_or_404(MedicationReminder, id=reminder_id, patient=patient)
    r.delete()
    return {'message': 'Rappel supprimé'}


@router.get('/patient/resultats-labo', response=list[PatientLabResultOut], auth=jwt_auth)
def patient_lab_results(request):
    patient = _get_patient_user(request)
    results = LabResult.objects.filter(
        commande__patient=patient, valide=True,
    ).select_related('commande__examen')
    return [
        PatientLabResultOut(
            id=r.id, examen=r.commande.examen.libelle,
            valeur=r.valeur, unite=r.unite,
            date_validation=r.date_validation,
            pdf_url=r.rapport_pdf.url if r.rapport_pdf else '',
        ) for r in results
    ]


@router.get('/patient/conversations', response=list[PatientConversationOut], auth=jwt_auth)
def patient_conversations(request):
    patient = _get_patient_user(request)
    convs = Conversation.objects.filter(patient=patient).select_related('medecin')
    out = []
    for conv in convs:
        last = conv.messages.order_by('-created_at').first()
        non_lus = conv.messages.filter(lu=False).exclude(auteur=patient.user).count()
        out.append(PatientConversationOut(
            id=conv.id, medecin_id=conv.medecin_id,
            medecin_nom=f'Dr {conv.medecin.first_name} {conv.medecin.last_name}',
            medecin_specialty=conv.medecin.specialty or '',
            dernier_message=last.contenu[:120] if last else '',
            non_lus=non_lus,
        ))
    return out


@router.post('/patient/conversations/{medecin_id}', auth=jwt_auth)
def patient_start_conversation(request, medecin_id: int):
    patient = _get_patient_user(request)
    medecin = get_object_or_404(User, id=medecin_id, role=User.Role.MEDECIN)
    conv, _ = Conversation.objects.get_or_create(patient=patient, medecin=medecin)
    return {'conversation_id': conv.id}


@router.get('/patient/conversations/{conv_id}/messages', response=list[ChatMessageOut], auth=jwt_auth)
def patient_list_messages(request, conv_id: int):
    patient = _get_patient_user(request)
    conv = get_object_or_404(Conversation, id=conv_id, patient=patient)
    return [
        ChatMessageOut(
            id=m.id, auteur_id=m.auteur_id, contenu=m.contenu,
            lu=m.lu, created_at=m.created_at,
        ) for m in conv.messages.all()
    ]


@router.post('/patient/conversations/{conv_id}/messages', response=ChatMessageOut, auth=jwt_auth)
def patient_send_message(request, conv_id: int, payload: ChatMessageIn):
    patient = _get_patient_user(request)
    conv = get_object_or_404(Conversation, id=conv_id, patient=patient)
    msg = ChatMessage.objects.create(
        conversation=conv, auteur=request.auth, contenu=payload.contenu,
    )
    return ChatMessageOut(
        id=msg.id, auteur_id=msg.auteur_id, contenu=msg.contenu,
        lu=msg.lu, created_at=msg.created_at,
    )


# ── Facturation patient ───────────────────────────────────────────────────────

@router.get('/patient/factures', response=list[InvoiceOut], auth=jwt_auth)
def patient_invoices(request):
    patient = _get_patient_user(request)
    qs = Invoice.objects.filter(patient=patient).select_related('patient').prefetch_related('lignes', 'paiements')
    return [InvoiceOut(**invoice_to_dict(i, include_lines=True)) for i in qs.order_by('-created_at')]


@router.get('/patient/factures/{invoice_id}', response=InvoiceOut, auth=jwt_auth)
def patient_invoice_detail(request, invoice_id: int):
    patient = _get_patient_user(request)
    invoice = get_object_or_404(
        Invoice.objects.select_related('patient').prefetch_related('lignes', 'paiements'),
        id=invoice_id,
        patient=patient,
    )
    return InvoiceOut(**invoice_to_dict(invoice, include_lines=True))


@router.post('/patient/factures/{invoice_id}/mobile-money/initier', response=MobileMoneyTransactionOut, auth=jwt_auth)
def patient_init_mobile_money(request, invoice_id: int, payload: MobileMoneyInitIn):
    patient = _get_patient_user(request)
    invoice = get_object_or_404(
        Invoice.objects.select_related('patient'),
        id=invoice_id,
        patient=patient,
    )
    return _init_mobile_payment(invoice, payload)


@router.post('/patient/factures/{invoice_id}/mobile-money/confirmer', response=MobileMoneyStatusOut, auth=jwt_auth)
def patient_confirm_mobile_money(request, invoice_id: int, payload: MobileMoneyConfirmIn):
    patient = _get_patient_user(request)
    tx = get_object_or_404(MobileMoneyTransaction, id=payload.transaction_id, patient=patient)
    if tx.facture_id != invoice_id:
        raise HttpError(403, 'Transaction invalide pour cette facture')
    return _confirm_mobile_payment(payload)


@router.get('/patient/mobile-money/{transaction_id}/statut', response=MobileMoneyStatusOut, auth=jwt_auth)
def patient_mobile_money_status(request, transaction_id: int):
    patient = _get_patient_user(request)
    tx = get_object_or_404(MobileMoneyTransaction, id=transaction_id, patient=patient)
    return _transaction_status(tx.id, request.auth)


@router.post('/patient/mobile-money/{transaction_id}/approuver', response=MobileMoneyStatusOut, auth=jwt_auth)
def patient_approve_mobile_money(request, transaction_id: int, payload: MobileMoneyPhoneApproveIn):
    patient = _get_patient_user(request)
    tx = get_object_or_404(
        MobileMoneyTransaction.objects.select_related('facture'),
        id=transaction_id,
        patient=patient,
    )
    return _approve_from_phone(tx, payload.numero_mobile)


@router.get('/patient/pharmacie/medicaments', response=list[MedicationOut], auth=jwt_auth)
def patient_list_medications(request, categorie: str = '', q: str = ''):
    _get_patient_user(request)
    return list_medications(request, categorie=categorie, q=q)


@router.get('/patient/pharmacie/demandes', response=list[PharmacyRequestOut], auth=jwt_auth)
def patient_pharmacy_requests(request):
    patient = _get_patient_user(request)
    from pharmacy.models import PatientPharmacyRequest
    qs = PatientPharmacyRequest.objects.filter(patient=patient).select_related('patient').prefetch_related('lignes__medicament')
    return [_request_out(r) for r in qs.order_by('-created_at')[:50]]


@router.post('/patient/pharmacie/demandes', response=PharmacyRequestOut, auth=jwt_auth)
def patient_submit_pharmacy_request(request, payload: PharmacyRequestIn):
    patient = _get_patient_user(request)
    return create_patient_pharmacy_request(patient, payload)


@router.get('/patient/carte-pdf/lien', response=PatientCardPdfLinkOut, auth=jwt_auth)
def patient_card_pdf_link(request):
    """Génère (ou régénère) la carte PDF et retourne l'URL de téléchargement."""
    patient = _get_patient_user(request)
    card_token = get_or_create_card_token(patient)
    _, filename = generate_and_save_patient_card_pdf(patient, card_token)
    media_url = card_token.pdf_file.url
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    pdf_url = f'{site}{media_url}' if site else media_url
    return PatientCardPdfLinkOut(
        pdf_url=pdf_url,
        media_url=media_url,
        filename=filename,
        qr_url=build_qr_scan_url(card_token.token),
        chemin=card_token.pdf_file.name,
    )


@router.get('/patient/carte-pdf', auth=jwt_auth)
def patient_card_pdf(request):
    """Téléchargement direct du PDF carte patient."""
    patient = _get_patient_user(request)
    card_token = get_or_create_card_token(patient)
    pdf_bytes, filename = generate_and_save_patient_card_pdf(patient, card_token)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = str(len(pdf_bytes))
    response['X-PDF-Media-Url'] = card_token.pdf_file.url
    response['X-PDF-Path'] = card_token.pdf_file.name
    return response


@router.get('/carte-patient/{token}', response=PatientCardFullOut, auth=None)
def public_patient_card_by_qr(request, token: str):
    """Données médicales complètes — accessible via scan du QR code (sans connexion)."""
    card_token = get_object_or_404(PatientCardToken, token=token, active=True)
    if card_token.expires_at < dj_tz.now():
        raise HttpError(410, 'Ce QR code a expiré. Demandez une nouvelle carte PDF au patient.')
    return build_patient_full_payload(card_token.patient)
