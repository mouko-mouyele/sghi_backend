from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from accounts.models import LoginJournal, User
from api.auth import jwt_auth, validate_password_strength
from api.permissions import require_role
from api.schemas_admin import (
    AdminAppointmentEdit,
    AdminAppointmentIn,
    AdminAppointmentOut,
    AdminAppointmentUpdate,
    AdminMedecinOut,
    AdminPatientEdit,
    AdminServiceIn,
    AdminServiceOut,
    AdminStaffEdit,
    AdminStatsOut,
    AdminTeamMemberOut,
    AdminUrgenceOut,
    HospitalInfoIn,
    HospitalInfoOut,
    LoginJournalOut,
    PaginatedAdminAppointmentOut,
    PaginatedAdminMedecinOut,
    PaginatedAdminTeamMemberOut,
    PaginatedLoginJournalOut,
)
from api.pagination import paginate_queryset, paginated
from api.schemas import MfaSetupOut, MessageOut, PatientOut, EmailDiagnosticOut, EmailTestOut
from billing.models import Payment
from clinical.appointment_utils import find_appointment_conflict, normalize_appointment_datetime
from clinical.models import Appointment, Bed, Building, Hospitalization, HospitalService, Patient, Room
from core.appointment_mail import (
    notify_appointment_cancelled,
    notify_appointment_created,
    notify_appointment_updated,
)
from core.audit import log_audit, snapshot
from core.mfa_email import get_hospital_email, mask_email
from core.gmail_api_mail import gmail_api_is_configured, verify_gmail_api
from core.sghi_mail import (
    brevo_is_configured,
    brevo_key_format_ok,
    email_diagnostic_message,
    email_is_configured,
    email_provider,
    render_smtp_likely_blocked,
    send_sghi_email,
    sghi_from_email,
    verify_brevo_account,
)
from core.middleware import get_audit_meta
from core.models import HospitalInfo
from core.pdf import generate_admin_stats_pdf
from core.staff_photo import photo_url, save_staff_photo
from laboratory.models import LabOrder

router = Router(tags=['Administration SGHL'])


def _require_admin(request):
    require_role(request.auth, User.Role.ADMIN)


def _require_rdv_staff(request):
    """Admin et secrétaire — gestion des rendez-vous."""
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE)


def _appointment_out(rdv: Appointment) -> AdminAppointmentOut:
    return AdminAppointmentOut(
        id=rdv.id, patient_id=rdv.patient_id,
        patient_nom=f'{rdv.patient.prenom} {rdv.patient.nom}',
        medecin_id=rdv.medecin_id, medecin_nom=f'Dr {rdv.medecin.first_name} {rdv.medecin.last_name}',
        date_heure=rdv.date_heure, motif=rdv.motif,
        statut=rdv.statut, duree_minutes=rdv.duree_minutes,
    )


def _get_stats_data() -> AdminStatsOut:
    now = dj_tz.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    lits_total = Bed.objects.count()
    lits_dispo = Bed.objects.filter(est_disponible=True).count()
    taux = round((1 - lits_dispo / lits_total) * 100, 1) if lits_total else 0

    urg_service = HospitalService.objects.filter(code='URG').first()
    urg_count = 0
    if urg_service:
        urg_count = Hospitalization.objects.filter(
            statut=Hospitalization.Statut.ACTIVE,
            lit__chambre__service=urg_service,
        ).count()

    recettes = Payment.objects.filter(
        created_at__year=now.year, created_at__month=now.month,
    ).aggregate(t=Sum('montant'))['t'] or Decimal('0')

    return AdminStatsOut(
        patients_total=Patient.objects.filter(archived=False).count(),
        medecins_total=User.objects.filter(role=User.Role.MEDECIN, is_active=True).count(),
        personnel_total=User.objects.filter(is_active=True).exclude(role=User.Role.PATIENT).count(),
        rdv_aujourdhui=Appointment.objects.filter(
            date_heure__gte=today_start, date_heure__lte=today_end,
        ).exclude(statut=Appointment.Statut.ANNULE).count(),
        rdv_en_attente=Appointment.objects.filter(
            statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
            date_heure__gte=now,
        ).count(),
        hospitalisations_actives=Hospitalization.objects.filter(statut=Hospitalization.Statut.ACTIVE).count(),
        taux_occupation=taux,
        examens_en_attente=LabOrder.objects.exclude(
            statut__in=[LabOrder.Statut.PUBLIE, LabOrder.Statut.ANNULE],
        ).count(),
        recettes_mois=recettes,
        urgences_actives=urg_count,
    )


@router.get('/admin/statistiques', response=AdminStatsOut, auth=jwt_auth)
def admin_statistics(request):
    _require_admin(request)
    return _get_stats_data()


@router.get('/admin/statistiques/pdf', auth=jwt_auth)
def admin_statistics_pdf(request):
    _require_admin(request)
    stats = _get_stats_data()
    stats_dict = stats.model_dump() if hasattr(stats, 'model_dump') else stats.dict()
    now = dj_tz.now().strftime('%d/%m/%Y %H:%M')
    admin_name = request.auth.get_full_name() or request.auth.username
    pdf_bytes = generate_admin_stats_pdf(
        stats=stats_dict, generated_at=now, admin_name=admin_name,
    )
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sghl-statistiques-{dj_tz.now().strftime("%Y%m%d")}.pdf"'
    log_audit(
        user=request.auth, action_type='ACCESS', model_name='AdminStats',
        object_id='pdf', ip_address=get_audit_meta(request)['ip_address'],
        user_agent=get_audit_meta(request)['user_agent'],
    )
    return response


@router.get('/admin/rendez-vous', response=PaginatedAdminAppointmentOut, auth=jwt_auth)
def admin_list_appointments(request, statut: str = '', date: str = '', page: int = 1, page_size: int = 10):
    _require_rdv_staff(request)
    qs = Appointment.objects.select_related('patient', 'medecin').order_by('date_heure')
    if statut:
        qs = qs.filter(statut=statut)
    if date:
        qs = qs.filter(date_heure__date=date)
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([
        AdminAppointmentOut(
            id=r.id, patient_id=r.patient_id,
            patient_nom=f'{r.patient.prenom} {r.patient.nom}',
            medecin_id=r.medecin_id,
            medecin_nom=f'Dr {r.medecin.first_name} {r.medecin.last_name}',
            date_heure=r.date_heure, motif=r.motif,
            statut=r.statut, duree_minutes=r.duree_minutes,
        ) for r in items
    ], meta)


@router.post('/admin/rendez-vous', response=AdminAppointmentOut, auth=jwt_auth)
def admin_create_appointment(request, payload: AdminAppointmentIn):
    _require_rdv_staff(request)
    patient = get_object_or_404(Patient, id=payload.patient_id)
    medecin = get_object_or_404(User, id=payload.medecin_id, role=User.Role.MEDECIN)
    start = normalize_appointment_datetime(payload.date_heure)
    conflict = find_appointment_conflict(medecin, start, payload.duree_minutes)
    if conflict:
        raise HttpError(400, 'Créneau déjà réservé pour ce médecin à cet horaire')
    rdv = Appointment.objects.create(
        patient=patient, medecin=medecin,
        date_heure=start, motif=payload.motif,
        duree_minutes=payload.duree_minutes, statut=payload.statut,
    )
    notify_appointment_created(rdv)
    return AdminAppointmentOut(
        id=rdv.id, patient_id=patient.id, patient_nom=f'{patient.prenom} {patient.nom}',
        medecin_id=medecin.id, medecin_nom=f'Dr {medecin.first_name} {medecin.last_name}',
        date_heure=rdv.date_heure, motif=rdv.motif,
        statut=rdv.statut, duree_minutes=rdv.duree_minutes,
    )


@router.patch('/admin/rendez-vous/{rdv_id}', response=AdminAppointmentOut, auth=jwt_auth)
def admin_update_appointment_status(request, rdv_id: int, payload: AdminAppointmentUpdate):
    _require_rdv_staff(request)
    rdv = get_object_or_404(Appointment.objects.select_related('patient', 'medecin'), id=rdv_id)
    old = {'statut': rdv.statut, 'date_heure': rdv.date_heure, 'medecin_id': rdv.medecin_id}
    rdv.statut = payload.statut
    rdv.save(update_fields=['statut', 'updated_at'])
    notify_appointment_updated(rdv, old, reason=f'Statut : {payload.statut}')
    return _appointment_out(rdv)


@router.put('/admin/rendez-vous/{rdv_id}', response=AdminAppointmentOut, auth=jwt_auth)
def admin_edit_appointment(request, rdv_id: int, payload: AdminAppointmentEdit):
    _require_rdv_staff(request)
    rdv = get_object_or_404(Appointment.objects.select_related('patient', 'medecin'), id=rdv_id)
    meta = get_audit_meta(request)
    old = {
        'motif': rdv.motif, 'statut': rdv.statut,
        'date_heure': rdv.date_heure, 'medecin_id': rdv.medecin_id,
    }

    if payload.patient_id is not None:
        rdv.patient = get_object_or_404(Patient, id=payload.patient_id)
    if payload.medecin_id is not None:
        rdv.medecin = get_object_or_404(User, id=payload.medecin_id, role=User.Role.MEDECIN)
    if payload.date_heure is not None:
        start = normalize_appointment_datetime(payload.date_heure)
        duree = payload.duree_minutes or rdv.duree_minutes
        conflict = find_appointment_conflict(rdv.medecin, start, duree, exclude_id=rdv.pk)
        if conflict:
            raise HttpError(400, 'Créneau déjà réservé pour ce médecin')
        rdv.date_heure = start
    if payload.motif is not None:
        rdv.motif = payload.motif
    if payload.statut is not None:
        rdv.statut = payload.statut
    if payload.duree_minutes is not None:
        rdv.duree_minutes = payload.duree_minutes
    rdv.save()

    raison = payload.raison_modification or ''
    if not raison and old['medecin_id'] != rdv.medecin_id:
        raison = 'Médecin indisponible au créneau prévu — réaffectation'
    notify_appointment_updated(rdv, old, reason=raison)

    log_audit(
        user=request.auth, action_type='UPDATE', model_name='Appointment',
        object_id=rdv.id, old_value={k: str(v) for k, v in old.items()},
        new_value={'motif': rdv.motif, 'statut': rdv.statut, 'date_heure': str(rdv.date_heure)},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    rdv.refresh_from_db()
    rdv = Appointment.objects.select_related('patient', 'medecin').get(pk=rdv.pk)
    return _appointment_out(rdv)


@router.delete('/admin/rendez-vous/{rdv_id}', auth=jwt_auth)
def admin_delete_appointment(request, rdv_id: int):
    _require_rdv_staff(request)
    rdv = get_object_or_404(Appointment.objects.select_related('patient', 'medecin'), id=rdv_id)
    meta = get_audit_meta(request)
    notify_appointment_cancelled(rdv, reason='Annulation par l\'accueil')
    log_audit(
        user=request.auth, action_type='DELETE', model_name='Appointment',
        object_id=rdv.id,
        old_value={'patient': f'{rdv.patient.nom}', 'date': str(rdv.date_heure), 'motif': rdv.motif},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    rdv.delete()
    return {'message': 'Rendez-vous supprimé — notification email envoyée'}


@router.patch('/admin/utilisateurs/{user_id}/desactiver', auth=jwt_auth)
def admin_deactivate_user(request, user_id: int):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    if user.id == request.auth.id:
        raise HttpError(400, 'Impossible de désactiver votre propre compte')
    user.is_active = False
    user.save(update_fields=['is_active'])
    return {'message': f'Compte {user.username} désactivé'}


def _update_staff_user(request, user: User, payload: AdminStaffEdit, expected_role: str):
    meta = get_audit_meta(request)
    old = {'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name}
    if user.role != expected_role:
        raise HttpError(400, f'Utilisateur non {expected_role}')
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.email is not None:
        if User.objects.filter(email=payload.email).exclude(pk=user.pk).exists():
            raise HttpError(400, 'Email déjà utilisé')
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.specialty is not None and expected_role == User.Role.MEDECIN:
        user.specialty = payload.specialty
    if payload.password:
        validate_password_strength(payload.password, user)
        user.set_password(payload.password)
    user.save()
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='User',
        object_id=user.id, old_value=old,
        new_value={'email': user.email, 'first_name': user.first_name},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return user


def _delete_staff_user(request, user: User, expected_role: str):
    if user.id == request.auth.id:
        raise HttpError(400, 'Impossible de supprimer votre propre compte')
    if user.role != expected_role:
        raise HttpError(400, f'Utilisateur non {expected_role}')
    if expected_role == User.Role.MEDECIN:
        if Hospitalization.objects.filter(
            medecin_referent=user, statut=Hospitalization.Statut.ACTIVE,
        ).exists():
            raise HttpError(400, 'Médecin référent d\'hospitalisations actives')
    meta = get_audit_meta(request)
    username = user.username
    log_audit(
        user=request.auth, action_type='DELETE', model_name='User',
        object_id=user.id, old_value={'username': username, 'role': user.role},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    user.delete()
    return {'message': f'Compte {username} supprimé'}


# ── Patients (admin CRUD complet) ─────────────────────────────────────────────

@router.put('/admin/patients/{patient_id}', response=PatientOut, auth=jwt_auth)
def admin_update_patient(request, patient_id: int, payload: AdminPatientEdit):
    _require_admin(request)
    patient = get_object_or_404(Patient, id=patient_id, archived=False)
    meta = get_audit_meta(request)
    old = snapshot(patient)
    data = payload.model_dump(exclude_unset=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_unset=True)
    if 'numero_dossier' in data:
        if Patient.objects.filter(numero_dossier=data['numero_dossier']).exclude(pk=patient.pk).exists():
            raise HttpError(400, 'Numéro de dossier déjà utilisé')
    for field, value in data.items():
        setattr(patient, field, value)
    patient.save()
    if patient.user and ('nom' in data or 'prenom' in data or 'email' in data):
        if 'prenom' in data:
            patient.user.first_name = patient.prenom
        if 'nom' in data:
            patient.user.last_name = patient.nom
        if 'email' in data:
            patient.user.email = patient.email
        patient.user.save()
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='Patient',
        object_id=patient.id, old_value=old, new_value=snapshot(patient),
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return patient


@router.delete('/admin/patients/{patient_id}', auth=jwt_auth)
def admin_delete_patient(request, patient_id: int):
    _require_admin(request)
    patient = get_object_or_404(Patient, id=patient_id)
    if Hospitalization.objects.filter(
        patient=patient, statut=Hospitalization.Statut.ACTIVE,
    ).exists():
        raise HttpError(400, 'Patient hospitalisé — sortie requise avant suppression')
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='DELETE', model_name='Patient',
        object_id=patient.id,
        old_value={'numero_dossier': patient.numero_dossier, 'nom': patient.nom},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    if patient.user:
        patient.user.delete()
    else:
        patient.delete()
    return {'message': 'Patient supprimé'}


# ── Médecins (admin CRUD complet) ─────────────────────────────────────────────

@router.post('/admin/utilisateurs/{user_id}/photo', auth=jwt_auth)
def admin_upload_user_photo(request, user_id: int, photo: UploadedFile = File(...)):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    if user.role == User.Role.PATIENT:
        raise HttpError(400, 'Photo réservée au personnel hospitalier')
    url = save_staff_photo(user, photo)
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='User',
        object_id=user.id, new_value={'photo': 'uploaded'},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return {'message': 'Photo d\'identité enregistrée', 'photo_url': url}


@router.put('/admin/medecins/{user_id}', response=AdminMedecinOut, auth=jwt_auth)
def admin_update_medecin(request, user_id: int, payload: AdminStaffEdit):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    _update_staff_user(request, user, payload, User.Role.MEDECIN)
    rdv_count = Appointment.objects.filter(
        medecin=user,
        statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
        date_heure__gte=dj_tz.now(),
    ).count()
    return AdminMedecinOut(
        id=user.id, username=user.username, first_name=user.first_name,
        last_name=user.last_name, email=user.email, specialty=user.specialty or '—',
        rdv_count=rdv_count, phone=user.phone,
        photo_url=photo_url(user), disponible_rdv=user.disponible_rdv,
    )


@router.delete('/admin/medecins/{user_id}', auth=jwt_auth)
def admin_delete_medecin(request, user_id: int):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    return _delete_staff_user(request, user, User.Role.MEDECIN)


# ── Secrétaires (admin CRUD complet) ──────────────────────────────────────────

@router.get('/admin/secretaires', response=PaginatedAdminTeamMemberOut, auth=jwt_auth)
def admin_list_secretaires(request, page: int = 1, page_size: int = 10):
    _require_admin(request)
    qs = User.objects.filter(role=User.Role.RECEPTIONNISTE).order_by('last_name')
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([
        AdminTeamMemberOut(
            id=u.id, username=u.username, first_name=u.first_name,
            last_name=u.last_name, role=u.role, email=u.email,
            specialty='', phone=u.phone, photo_url=photo_url(u),
        ) for u in items
    ], meta)


@router.put('/admin/secretaires/{user_id}', response=AdminTeamMemberOut, auth=jwt_auth)
def admin_update_secretaire(request, user_id: int, payload: AdminStaffEdit):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    _update_staff_user(request, user, payload, User.Role.RECEPTIONNISTE)
    return AdminTeamMemberOut(
        id=user.id, username=user.username, first_name=user.first_name,
        last_name=user.last_name, role=user.role, email=user.email,
        specialty='', phone=user.phone, photo_url=photo_url(user),
    )


@router.delete('/admin/secretaires/{user_id}', auth=jwt_auth)
def admin_delete_secretaire(request, user_id: int):
    _require_admin(request)
    user = get_object_or_404(User, id=user_id)
    return _delete_staff_user(request, user, User.Role.RECEPTIONNISTE)


@router.get('/admin/medecins', response=PaginatedAdminMedecinOut, auth=jwt_auth)
def admin_list_medecins(request, page: int = 1, page_size: int = 9):
    _require_rdv_staff(request)
    qs = User.objects.filter(role=User.Role.MEDECIN).order_by('last_name', 'first_name')
    items, meta = paginate_queryset(qs, page, page_size)
    result = []
    for m in items:
        rdv_count = Appointment.objects.filter(
            medecin=m,
            statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
            date_heure__gte=dj_tz.now(),
        ).count()
        result.append(AdminMedecinOut(
            id=m.id, username=m.username, first_name=m.first_name,
            last_name=m.last_name, email=m.email, specialty=m.specialty or '—',
            rdv_count=rdv_count, phone=m.phone,
            photo_url=photo_url(m), disponible_rdv=m.disponible_rdv,
        ))
    return paginated(result, meta)


@router.get('/admin/equipe', response=PaginatedAdminTeamMemberOut, auth=jwt_auth)
def admin_medical_team(request, role: str = '', page: int = 1, page_size: int = 12):
    _require_admin(request)
    qs = User.objects.filter(is_active=True).exclude(role=User.Role.PATIENT)
    if role:
        qs = qs.filter(role=role)
    qs = qs.order_by('role', 'last_name')
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([
        AdminTeamMemberOut(
            id=u.id, username=u.username, first_name=u.first_name,
            last_name=u.last_name, role=u.role, email=u.email,
            specialty=u.specialty or '', phone=u.phone or '',
            photo_url=photo_url(u),
        ) for u in items
    ], meta)


@router.get('/admin/services', response=list[AdminServiceOut], auth=jwt_auth)
def admin_list_services(request):
    _require_admin(request)
    services = HospitalService.objects.select_related('building').prefetch_related('chambres__lits')
    result = []
    for s in services:
        lits = Bed.objects.filter(chambre__service=s)
        actives = Hospitalization.objects.filter(
            statut=Hospitalization.Statut.ACTIVE, lit__chambre__service=s,
        ).count()
        result.append(AdminServiceOut(
            id=s.id, code=s.code, nom=s.nom, building=s.building.nom,
            chambres=s.chambres.count(),
            lits_total=lits.count(),
            lits_disponibles=lits.filter(est_disponible=True).count(),
            hospitalisations_actives=actives,
        ))
    return result


@router.post('/admin/services', response=AdminServiceOut, auth=jwt_auth)
def admin_create_service(request, payload: AdminServiceIn):
    _require_admin(request)
    building = get_object_or_404(Building, id=payload.building_id)
    if HospitalService.objects.filter(code=payload.code).exists():
        raise HttpError(400, 'Code service déjà utilisé')
    s = HospitalService.objects.create(code=payload.code, nom=payload.nom, building=building)
    return AdminServiceOut(
        id=s.id, code=s.code, nom=s.nom, building=building.nom,
        chambres=0, lits_total=0, lits_disponibles=0, hospitalisations_actives=0,
    )


@router.get('/admin/urgences', auth=jwt_auth)
def admin_emergencies(request):
    _require_admin(request)
    urg = HospitalService.objects.filter(code='URG').first()
    if not urg:
        return {'service': None, 'hospitalisations': [], 'lits_disponibles': 0, 'lits_total': 0}

    hosps = Hospitalization.objects.filter(
        statut=Hospitalization.Statut.ACTIVE, lit__chambre__service=urg,
    ).select_related('patient', 'lit', 'medecin_referent')

    lits = Bed.objects.filter(chambre__service=urg)
    return {
        'service': {'code': urg.code, 'nom': urg.nom},
        'lits_total': lits.count(),
        'lits_disponibles': lits.filter(est_disponible=True).count(),
        'hospitalisations': [
            AdminUrgenceOut(
                hospitalisation_id=h.id,
                patient_nom=f'{h.patient.prenom} {h.patient.nom}',
                numero_dossier=h.patient.numero_dossier,
                lit=f'{h.lit.chambre.numero}/{h.lit.numero_lit}',
                medecin=f'Dr {h.medecin_referent.last_name}',
                date_entree=h.date_entree,
                motif=h.motif_admission,
            ).dict() for h in hosps
        ],
    }


@router.get('/admin/infos-pratiques', response=HospitalInfoOut, auth=jwt_auth)
def get_hospital_info(request):
    _require_admin(request)
    info = HospitalInfo.get_instance()
    return info


@router.put('/admin/infos-pratiques', response=HospitalInfoOut, auth=jwt_auth)
def update_hospital_info(request, payload: HospitalInfoIn):
    _require_admin(request)
    info = HospitalInfo.get_instance()
    for field, value in payload.dict().items():
        setattr(info, field, value)
    info.save()
    return info


@router.get('/admin/journal-connexions', response=PaginatedLoginJournalOut, auth=jwt_auth)
def admin_login_journal(request, page: int = 1, page_size: int = 15):
    _require_admin(request)
    qs = LoginJournal.objects.select_related('user').order_by('-timestamp')
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([
        LoginJournalOut(
            user__username=entry.user.username if entry.user_id else None,
            ip_address=entry.ip_address,
            success=entry.success,
            timestamp=entry.timestamp,
            user_agent=entry.user_agent,
        ) for entry in items
    ], meta)


@router.get('/admin/email/diagnostic', response=EmailDiagnosticOut, auth=jwt_auth)
def admin_email_diagnostic(request):
    _require_admin(request)
    hospital = get_hospital_email()
    pwd_set = bool((getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip())
    configured = email_is_configured()
    brevo_valid = False
    if brevo_is_configured() and brevo_key_format_ok():
        brevo_valid, _ = verify_brevo_account()
    gmail_set = gmail_api_is_configured()
    gmail_valid = False
    if gmail_set:
        gmail_valid, _ = verify_gmail_api()
    return EmailDiagnosticOut(
        configured=configured,
        provider=email_provider(),
        brevo_key_set=brevo_is_configured(),
        brevo_key_valid=brevo_valid,
        gmail_api_set=gmail_set,
        gmail_api_valid=gmail_valid,
        smtp_host=settings.EMAIL_HOST,
        smtp_port=settings.EMAIL_PORT,
        smtp_user=(settings.EMAIL_HOST_USER or '').strip(),
        from_email=sghi_from_email(),
        hospital_email=hospital or '',
        password_set=pwd_set,
        render_smtp_blocked=render_smtp_likely_blocked(),
        message=email_diagnostic_message(),
    )


@router.post('/admin/email/test', response=EmailTestOut, auth=jwt_auth)
def admin_email_test(request):
    _require_admin(request)
    dest = get_hospital_email() or (settings.EMAIL_HOST_USER or '').strip()
    if not dest:
        raise HttpError(400, 'Aucune adresse destinataire — configurez MFA_HOSPITAL_EMAIL dans Render.')
    ok, err = send_sghi_email(
        subject='[SGHL] Test email — configuration Gmail',
        body=(
            'Ceci est un email de test depuis SGHL (Render).\n\n'
            'Si vous recevez ce message, les codes MFA et notifications '
            'seront bien délivrés dans cette boîte mail.'
        ),
        to=[dest],
    )
    if ok:
        return EmailTestOut(
            success=True,
            detail=f'Email de test envoyé à {mask_email(dest)} — vérifiez la boîte de réception et les spams.',
            sent_to=dest,
        )
    raise HttpError(400, err or 'Échec envoi email')


@router.get('/admin/mfa', response=MfaSetupOut, auth=jwt_auth)
def admin_mfa_status(request):
    _require_admin(request)
    hospital = get_hospital_email()
    masked = mask_email(hospital) if hospital else ''
    return MfaSetupOut(
        mfa_enabled=True,
        hospital_email=hospital,
        hospital_email_masked=masked,
        message=(
            'MFA par email activé pour tout le personnel : le code de connexion '
            f'est envoyé à la boîte mail de l\'hôpital ({masked or "non configurée"}). '
            'Les patients reçoivent le code sur leur email personnel.'
        ),
    )


@router.post('/admin/mfa/enable', response=MfaSetupOut, auth=jwt_auth)
def admin_mfa_enable(request):
    _require_admin(request)
    return admin_mfa_status(request)


@router.post('/admin/mfa/disable', response=MfaSetupOut, auth=jwt_auth)
def admin_mfa_disable(request):
    _require_admin(request)
    raise HttpError(
        400,
        'Le MFA par email est obligatoire pour tous les utilisateurs et ne peut pas être désactivé.',
    )
