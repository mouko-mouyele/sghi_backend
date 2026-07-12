from datetime import date, datetime, timedelta, timezone

from django.core.files.base import ContentFile
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from accounts.models import User
from api.auth import jwt_auth
from api.permissions import can_access_patient, require_role
from api.schemas import (
    AppointmentIn,
    AppointmentOut,
    BedOut,
    ChatMessageIn,
    ChatMessageOut,
    ConsultationIn,
    ConsultationOut,
    DischargeIn,
    DocumentOut,
    HospitalizationIn,
    HospitalizationOut,
    HospitalizationDetailOut,
    HospitalizationUpdateIn,
    MedecinDispoOut,
    MedecinDisponibiliteIn,
    MessageOut,
    NursingCareIn,
    NursingCareOut,
    NursingCareDetailOut,
    PaginatedHospitalizationsOut,
    PaginatedMedecinsOut,
    PaginatedPatientsOut,
    PatientIn,
    PatientOut,
    PrescriptionIn,
    PrescriptionOut,
    ReminderIn,
    TransferIn,
    VitalSignIn,
    VitalSignOut,
)
from clinical.appointment_utils import (
    find_appointment_conflict,
    list_occupied_slots,
    normalize_appointment_datetime,
)
from clinical.models import (
    Appointment,
    Bed,
    ChatMessage,
    Consultation,
    Conversation,
    Hospitalization,
    HospitalService,
    MedicalDocument,
    MedicationReminder,
    NursingCare,
    Patient,
    Prescription,
    VitalSign,
)
from core.appointment_mail import notify_appointment_pending
from core.audit import log_audit, snapshot
from core.patient_mail import (
    notify_hospitalization_admitted,
    notify_hospitalization_discharged,
    notify_patient_new_message,
)
from core.middleware import get_audit_meta
from core.staff_photo import photo_url
from api.pagination import paginate_queryset, paginated

router = Router(tags=['Clinique & Hospitalisation'])


def _medecin_out(m: User) -> MedecinDispoOut:
    return MedecinDispoOut(
        id=m.id, username=m.username, first_name=m.first_name,
        last_name=m.last_name, specialty=m.specialty or 'Médecine générale',
        phone=m.phone or '', photo_url=photo_url(m), disponible_rdv=m.disponible_rdv,
    )


def _hosp_detail(h: Hospitalization) -> HospitalizationDetailOut:
    lit = h.lit
    return HospitalizationDetailOut(
        id=h.id,
        patient_id=h.patient_id,
        patient_nom=f'{h.patient.prenom} {h.patient.nom}',
        patient_dossier=h.patient.numero_dossier,
        lit_id=lit.id,
        lit_label=f'Lit {lit.numero_lit} — Ch. {lit.chambre.numero}',
        service_nom=lit.chambre.service.nom,
        medecin_referent_id=h.medecin_referent_id,
        medecin_nom=f'Dr {h.medecin_referent.first_name} {h.medecin_referent.last_name}',
        date_entree=h.date_entree,
        date_sortie_prevue=h.date_sortie_prevue,
        date_sortie_effective=h.date_sortie_effective,
        statut=h.statut,
        motif_admission=h.motif_admission,
        notes=h.notes or '',
    )


@router.get('/patients', response=PaginatedPatientsOut, auth=jwt_auth)
def list_patients(request, page: int = 1, page_size: int = 20, search: str = ''):
    require_role(
        request.auth,
        User.Role.ADMIN,
        User.Role.MEDECIN,
        User.Role.INFIRMIER,
        User.Role.RECEPTIONNISTE,
        User.Role.BIOLOGISTE,
        User.Role.COMPTABLE,
    )
    qs = Patient.objects.filter(archived=False).order_by('nom', 'prenom')
    if search:
        qs = qs.filter(Q(nom__icontains=search) | Q(prenom__icontains=search) | Q(numero_dossier__icontains=search))
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated(items, meta)


@router.post('/patients', response=PatientOut, auth=jwt_auth)
def create_patient(request, payload: PatientIn):
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE)
    if Patient.objects.filter(numero_dossier=payload.numero_dossier).exists():
        raise HttpError(400, 'Numéro de dossier déjà existant')
    patient = Patient.objects.create(**payload.dict())
    meta = get_audit_meta(request)
    log_audit(user=request.auth, action_type='CREATE', model_name='Patient',
              object_id=patient.id, new_value=snapshot(patient),
              ip_address=meta['ip_address'], user_agent=meta['user_agent'])
    return patient


@router.get('/patients/{patient_id}', response=PatientOut, auth=jwt_auth)
def get_patient(request, patient_id: int):
    patient = get_object_or_404(Patient, id=patient_id, archived=False)
    if not can_access_patient(request.auth, patient):
        raise HttpError(403, 'Accès refusé au dossier patient')
    return patient


@router.get('/lits/disponibles', response=list[BedOut], auth=jwt_auth)
def list_available_beds(request, service_id: int = 0):
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE, User.Role.MEDECIN)
    beds = Bed.objects.filter(est_disponible=True).select_related('chambre__service')
    if service_id:
        beds = beds.filter(chambre__service_id=service_id)
    return [
        BedOut(
            id=b.id, numero_lit=b.numero_lit, est_disponible=b.est_disponible,
            chambre_numero=b.chambre.numero, service_nom=b.chambre.service.nom,
            service_id=b.chambre.service_id,
        ) for b in beds
    ]


@router.post('/hospitalisations', response=HospitalizationOut, auth=jwt_auth)
def create_hospitalization(request, payload: HospitalizationIn):
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE, User.Role.MEDECIN)
    lit = get_object_or_404(Bed, id=payload.lit_id)
    if not lit.est_disponible:
        raise HttpError(400, 'Lit non disponible — admission conditionnée par disponibilité réelle')
    medecin = get_object_or_404(User, id=payload.medecin_referent_id, role=User.Role.MEDECIN)
    hosp = Hospitalization(
        patient_id=payload.patient_id, lit=lit, medecin_referent=medecin,
        date_entree=payload.date_entree, date_sortie_prevue=payload.date_sortie_prevue,
        motif_admission=payload.motif_admission,
    )
    try:
        hosp.save()
    except Exception as e:
        raise HttpError(400, str(e))
    meta = get_audit_meta(request)
    log_audit(user=request.auth, action_type='CREATE', model_name='Hospitalization',
              object_id=hosp.id, new_value=snapshot(hosp),
              ip_address=meta['ip_address'], user_agent=meta['user_agent'])
    hosp = Hospitalization.objects.select_related(
        'patient', 'lit__chambre__service', 'medecin_referent',
    ).get(pk=hosp.pk)
    notify_hospitalization_admitted(hosp)
    return HospitalizationOut(
        id=hosp.id, patient_id=hosp.patient_id, lit_id=hosp.lit_id, statut=hosp.statut,
        date_entree=hosp.date_entree, date_sortie_prevue=hosp.date_sortie_prevue,
        motif_admission=hosp.motif_admission, medecin_referent_id=hosp.medecin_referent_id,
    )


@router.get('/hospitalisations/actives', response=list[HospitalizationDetailOut], auth=jwt_auth)
def list_active_hospitalizations(request):
    require_role(
        request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE,
        User.Role.MEDECIN, User.Role.INFIRMIER,
    )
    qs = Hospitalization.objects.filter(
        statut=Hospitalization.Statut.ACTIVE,
    ).select_related('patient', 'lit__chambre__service', 'medecin_referent')
    return [_hosp_detail(h) for h in qs[:100]]


@router.get('/hospitalisations', response=PaginatedHospitalizationsOut, auth=jwt_auth)
def list_hospitalizations(request, statut: str = '', page: int = 1, page_size: int = 15):
    require_role(
        request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE,
        User.Role.MEDECIN, User.Role.INFIRMIER,
    )
    qs = Hospitalization.objects.select_related(
        'patient', 'lit__chambre__service', 'medecin_referent',
    ).order_by('-date_entree')
    if statut:
        qs = qs.filter(statut=statut)
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([_hosp_detail(h) for h in items], meta)


@router.patch('/hospitalisations/{hosp_id}', response=HospitalizationDetailOut, auth=jwt_auth)
def update_hospitalization(request, hosp_id: int, payload: HospitalizationUpdateIn):
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE)
    hosp = get_object_or_404(
        Hospitalization.objects.select_related(
            'patient', 'lit__chambre__service', 'medecin_referent',
        ),
        id=hosp_id,
    )
    if hosp.statut == Hospitalization.Statut.SORTIE:
        raise HttpError(400, 'Hospitalisation clôturée — modification impossible')
    if payload.date_sortie_prevue is not None:
        hosp.date_sortie_prevue = payload.date_sortie_prevue
    if payload.motif_admission is not None:
        hosp.motif_admission = payload.motif_admission
    if payload.notes is not None:
        hosp.notes = payload.notes
    if payload.statut is not None:
        if payload.statut not in (
            Hospitalization.Statut.ACTIVE,
            Hospitalization.Statut.TRANSFERT,
        ):
            raise HttpError(400, 'Statut non modifiable via cette route — utilisez la sortie patient')
        hosp.statut = payload.statut
    hosp.save()
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='Hospitalization',
        object_id=hosp.id, ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return _hosp_detail(hosp)


@router.post('/hospitalisations/{hosp_id}/transfert', response=MessageOut, auth=jwt_auth)
def transfer_hospitalization(request, hosp_id: int, payload: TransferIn):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    hosp = get_object_or_404(Hospitalization, id=hosp_id, statut=Hospitalization.Statut.ACTIVE)
    old_lit = hosp.lit
    new_lit = get_object_or_404(Bed, id=payload.nouveau_lit_id, est_disponible=True)
    old_lit.est_disponible = True
    old_lit.save(update_fields=['est_disponible', 'updated_at'])
    hosp.lit = new_lit
    hosp.statut = Hospitalization.Statut.TRANSFERT
    hosp.notes = (hosp.notes + '\n' + payload.notes).strip()
    hosp.save()
    hosp.statut = Hospitalization.Statut.ACTIVE
    hosp.save()
    return MessageOut(message='Transfert inter-services effectué', detail=f'Lit {new_lit.numero_lit}')


@router.post('/hospitalisations/{hosp_id}/sortie', response=MessageOut, auth=jwt_auth)
def discharge_patient(request, hosp_id: int, payload: DischargeIn):
    require_role(
        request.auth, User.Role.MEDECIN, User.Role.ADMIN, User.Role.RECEPTIONNISTE,
    )
    hosp = get_object_or_404(Hospitalization, id=hosp_id, statut=Hospitalization.Statut.ACTIVE)
    hosp.statut = Hospitalization.Statut.SORTIE
    hosp.date_sortie_effective = payload.date_sortie_effective or dj_tz.now()
    if payload.notes:
        hosp.notes = (hosp.notes + '\n' + payload.notes).strip()
    hosp.save()
    hosp = Hospitalization.objects.select_related('patient').get(pk=hosp.pk)
    notify_hospitalization_discharged(hosp)
    return MessageOut(message='Sortie enregistrée — patient notifié par email')


@router.post('/consultations', response=ConsultationOut, auth=jwt_auth)
def create_consultation(request, payload: ConsultationIn):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    if payload.hospitalisation_id:
        hosp = get_object_or_404(Hospitalization, id=payload.hospitalisation_id)
        if hosp.statut != Hospitalization.Statut.ACTIVE:
            raise HttpError(400, 'Hospitalisation non active')
    return Consultation.objects.create(
        patient_id=payload.patient_id, hospitalisation_id=payload.hospitalisation_id,
        medecin=request.auth, diagnostic_cim10=payload.diagnostic_cim10,
        diagnostic_libelle=payload.diagnostic_libelle, notes_cliniques=payload.notes_cliniques,
    )


@router.post('/consultations/{consultation_id}/valider', response=MessageOut, auth=jwt_auth)
def validate_consultation(request, consultation_id: int):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    c = get_object_or_404(Consultation, id=consultation_id)
    c.validee = True
    c.date_validation = dj_tz.now()
    c.save()
    return MessageOut(message='Consultation validée')


@router.post('/prescriptions', response=PrescriptionOut, auth=jwt_auth)
def create_prescription(request, payload: PrescriptionIn):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    consultation = get_object_or_404(Consultation, id=payload.consultation_id)
    if not consultation.validee:
        raise HttpError(400, 'Validez la consultation avant de prescrire')
    return Prescription.objects.create(**payload.dict())


@router.post('/prescriptions/{prescription_id}/valider', response=MessageOut, auth=jwt_auth)
def validate_prescription(request, prescription_id: int):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    p = get_object_or_404(Prescription, id=prescription_id)
    p.validee = True
    p.verrouillee = True
    p.save()
    return MessageOut(message='Prescription validée et verrouillée')


@router.post('/constantes', response=VitalSignOut, auth=jwt_auth)
def record_vital_signs(request, payload: VitalSignIn):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.ADMIN)
    hosp = get_object_or_404(Hospitalization, id=payload.hospitalisation_id)
    vs = VitalSign.objects.create(
        hospitalisation=hosp, infirmier=request.auth,
        temperature=payload.temperature, tension_systolique=payload.tension_systolique,
        tension_diastolique=payload.tension_diastolique,
        frequence_cardiaque=payload.frequence_cardiaque,
        saturation_o2=payload.saturation_o2, notes=payload.notes,
    )
    return VitalSignOut(
        id=vs.id, hospitalisation_id=vs.hospitalisation_id,
        temperature=float(vs.temperature) if vs.temperature else None,
        tension_systolique=vs.tension_systolique,
        frequence_cardiaque=vs.frequence_cardiaque, date_prise=vs.date_prise,
    )


@router.get('/constantes/{hospitalisation_id}', response=list[VitalSignOut], auth=jwt_auth)
def list_vital_signs(request, hospitalisation_id: int):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.MEDECIN, User.Role.ADMIN)
    return [
        VitalSignOut(
            id=v.id, hospitalisation_id=v.hospitalisation_id,
            temperature=float(v.temperature) if v.temperature else None,
            tension_systolique=v.tension_systolique,
            frequence_cardiaque=v.frequence_cardiaque, date_prise=v.date_prise,
        ) for v in VitalSign.objects.filter(hospitalisation_id=hospitalisation_id)
    ]


@router.post('/soins', response=NursingCareOut, auth=jwt_auth)
def create_nursing_care(request, payload: NursingCareIn):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.ADMIN)
    soin = NursingCare.objects.create(
        hospitalisation_id=payload.hospitalisation_id, infirmier=request.auth,
        prescription_id=payload.prescription_id, description=payload.description,
        planifie_a=payload.planifie_a,
    )
    return soin


@router.post('/soins/{soin_id}/realiser', response=MessageOut, auth=jwt_auth)
def complete_nursing_care(request, soin_id: int):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.ADMIN)
    soin = get_object_or_404(NursingCare, id=soin_id)
    soin.realise_a = dj_tz.now()
    soin.save()
    return MessageOut(message='Soin réalisé')


@router.get('/soins/alertes-doses-omises', response=list[NursingCareOut], auth=jwt_auth)
def missed_doses_alerts(request):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.MEDECIN, User.Role.ADMIN)
    now = dj_tz.now()
    overdue = NursingCare.objects.filter(
        realise_a__isnull=True, planifie_a__lt=now, dose_omise=False,
    )
    for s in overdue:
        s.dose_omise = True
        s.save(update_fields=['dose_omise', 'updated_at'])
    return list(NursingCare.objects.filter(dose_omise=True, realise_a__isnull=True)[:50])


def _nursing_care_detail(soin: NursingCare, now=None) -> NursingCareDetailOut:
    now = now or dj_tz.now()
    hosp = soin.hospitalisation
    patient = hosp.patient
    service = ''
    if hosp.lit_id and hosp.lit.chambre_id:
        service = hosp.lit.chambre.service.nom
    if soin.realise_a:
        statut = 'REALISE'
    elif soin.dose_omise:
        statut = 'OMIS'
    elif soin.planifie_a < now:
        statut = 'EN_RETARD'
    else:
        statut = 'PLANIFIE'
    return NursingCareDetailOut(
        id=soin.id,
        hospitalisation_id=hosp.id,
        patient_nom=f'{patient.prenom} {patient.nom}',
        patient_dossier=patient.numero_dossier,
        service=service,
        description=soin.description,
        planifie_a=soin.planifie_a,
        realise_a=soin.realise_a,
        dose_omise=soin.dose_omise,
        statut=statut,
    )


@router.get('/soins/planning', response=list[NursingCareDetailOut], auth=jwt_auth)
def nursing_care_planning(request, statut: str = ''):
    require_role(request.auth, User.Role.INFIRMIER, User.Role.ADMIN, User.Role.MEDECIN)
    now = dj_tz.now()
    qs = NursingCare.objects.filter(
        hospitalisation__statut=Hospitalization.Statut.ACTIVE,
    ).select_related(
        'hospitalisation__patient',
        'hospitalisation__lit__chambre__service',
    ).order_by('planifie_a')
    if statut == 'OMIS':
        qs = qs.filter(dose_omise=True, realise_a__isnull=True)
    elif statut == 'EN_RETARD':
        qs = qs.filter(realise_a__isnull=True, dose_omise=False, planifie_a__lt=now)
    elif statut == 'PLANIFIE':
        qs = qs.filter(realise_a__isnull=True, dose_omise=False, planifie_a__gte=now)
    elif statut == 'REALISE':
        qs = qs.filter(realise_a__isnull=False)
    return [_nursing_care_detail(s, now) for s in qs[:100]]


@router.post('/documents/{patient_id}', response=DocumentOut, auth=jwt_auth)
def upload_document(request, patient_id: int, titre: str, file: UploadedFile = File(...)):
    require_role(request.auth, User.Role.MEDECIN, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    patient = get_object_or_404(Patient, id=patient_id)
    allowed = {'application/pdf', 'image/jpeg', 'image/png'}
    if file.content_type not in allowed:
        raise HttpError(400, 'Type MIME non autorisé')
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, 'Fichier trop volumineux (max 10 Mo)')
    doc = MedicalDocument.objects.create(
        patient=patient, titre=titre, fichier=file, mime_type=file.content_type,
        taille_octets=file.size, uploaded_by=request.auth,
        signe_electroniquement=request.auth.role == User.Role.MEDECIN,
    )
    return DocumentOut(
        id=doc.id, titre=doc.titre, mime_type=doc.mime_type,
        taille_octets=doc.taille_octets, signe_electroniquement=doc.signe_electroniquement,
        created_at=doc.created_at,
    )


@router.get('/documents/{patient_id}', response=list[DocumentOut], auth=jwt_auth)
def list_documents(request, patient_id: int):
    patient = get_object_or_404(Patient, id=patient_id)
    if not can_access_patient(request.auth, patient):
        raise HttpError(403, 'Accès refusé')
    return [
        DocumentOut(
            id=d.id, titre=d.titre, mime_type=d.mime_type,
            taille_octets=d.taille_octets, signe_electroniquement=d.signe_electroniquement,
            created_at=d.created_at,
        ) for d in patient.documents.all()
    ]


# ── RDV ───────────────────────────────────────────────────────────────────────

@router.get('/medecins', response=PaginatedMedecinsOut, auth=jwt_auth)
def list_all_medecins(request, page: int = 1, page_size: int = 12, search: str = ''):
    """Liste paginée des médecins — secrétaire / admin."""
    require_role(request.auth, User.Role.ADMIN, User.Role.RECEPTIONNISTE, User.Role.MEDECIN)
    qs = User.objects.filter(role=User.Role.MEDECIN, is_active=True).order_by('last_name', 'first_name')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(specialty__icontains=search),
        )
    disponibles_total = qs.filter(disponible_rdv=True).count()
    indisponibles_total = qs.filter(disponible_rdv=False).count()
    items, meta = paginate_queryset(qs, page, page_size)
    return {
        **paginated([_medecin_out(m) for m in items], meta),
        'disponibles_total': disponibles_total,
        'indisponibles_total': indisponibles_total,
    }


@router.get('/medecins/disponibles', response=list[MedecinDispoOut], auth=jwt_auth)
def list_medecins(request):
    qs = User.objects.filter(
        role=User.Role.MEDECIN, is_active=True, disponible_rdv=True,
    ).order_by('last_name')
    return [_medecin_out(m) for m in qs]


@router.patch('/medecins/{medecin_id}/disponibilite', auth=jwt_auth)
def set_medecin_disponibilite(request, medecin_id: int, payload: MedecinDisponibiliteIn):
    require_role(request.auth, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
    medecin = get_object_or_404(User, id=medecin_id, role=User.Role.MEDECIN)
    medecin.disponible_rdv = payload.disponible_rdv
    medecin.save(update_fields=['disponible_rdv'])
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='User',
        object_id=medecin.id,
        new_value={'disponible_rdv': payload.disponible_rdv},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return {
        'message': 'Disponibilité mise à jour',
        'disponible_rdv': medecin.disponible_rdv,
    }


@router.get('/medecins/{medecin_id}/creneaux', auth=jwt_auth)
def medecin_busy_slots(request, medecin_id: int, jour: date):
    """Créneaux déjà pris — aide le patient à choisir un horaire libre."""
    medecin = get_object_or_404(User, id=medecin_id, role=User.Role.MEDECIN)
    return list_occupied_slots(medecin, jour)


@router.post('/rendez-vous', response=AppointmentOut, auth=jwt_auth)
def create_appointment(request, payload: AppointmentIn):
    if request.auth.role == User.Role.PATIENT:
        patient = get_object_or_404(Patient, user=request.auth)
    else:
        raise HttpError(403, 'Seuls les patients prennent RDV via cette route')
    medecin = get_object_or_404(User, id=payload.medecin_id, role=User.Role.MEDECIN)

    start = normalize_appointment_datetime(payload.date_heure)
    if start < dj_tz.now():
        raise HttpError(400, 'La date doit être dans le futur')

    conflict = find_appointment_conflict(medecin, start, payload.duree_minutes)
    if conflict:
        local = dj_tz.localtime(conflict.date_heure)
        fin = local + timedelta(minutes=conflict.duree_minutes)
        raise HttpError(
            400,
            f'Créneau indisponible : le Dr {medecin.last_name} est déjà pris '
            f'le {local.strftime("%d/%m/%Y à %H:%M")}–{fin.strftime("%H:%M")}. '
            f'Choisissez un autre horaire.',
        )

    rdv = Appointment.objects.create(
        patient=patient, medecin=medecin, date_heure=start,
        motif=payload.motif, duree_minutes=payload.duree_minutes,
        statut=Appointment.Statut.PLANIFIE,
    )
    notify_appointment_pending(rdv)
    return AppointmentOut(
        id=rdv.id, medecin_id=rdv.medecin_id, date_heure=rdv.date_heure,
        motif=rdv.motif, statut=rdv.statut,
    )


@router.get('/rendez-vous', response=list[AppointmentOut], auth=jwt_auth)
def list_appointments(request):
    if request.auth.role == User.Role.PATIENT:
        patient = get_object_or_404(Patient, user=request.auth)
        qs = Appointment.objects.filter(patient=patient)
    elif request.auth.role == User.Role.MEDECIN:
        qs = Appointment.objects.filter(medecin=request.auth)
    else:
        require_role(request.auth, User.Role.RECEPTIONNISTE, User.Role.ADMIN)
        qs = Appointment.objects.all()
    return [
        AppointmentOut(
            id=r.id, medecin_id=r.medecin_id, date_heure=r.date_heure,
            motif=r.motif, statut=r.statut,
        ) for r in qs.order_by('date_heure')[:50]
    ]


# ── Chat médecin-patient ──────────────────────────────────────────────────────

@router.post('/conversations/{medecin_id}', response=dict, auth=jwt_auth)
def start_conversation(request, medecin_id: int):
    patient = get_object_or_404(Patient, user=request.auth)
    medecin = get_object_or_404(User, id=medecin_id, role=User.Role.MEDECIN)
    conv, _ = Conversation.objects.get_or_create(patient=patient, medecin=medecin)
    return {'conversation_id': conv.id}


@router.post('/conversations/{conv_id}/messages', response=ChatMessageOut, auth=jwt_auth)
def send_message(request, conv_id: int, payload: ChatMessageIn):
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.auth.role == User.Role.PATIENT:
        if conv.patient.user_id != request.auth.id:
            raise HttpError(403, 'Accès refusé')
    elif request.auth.role == User.Role.MEDECIN:
        if conv.medecin_id != request.auth.id:
            raise HttpError(403, 'Accès refusé')
    else:
        raise HttpError(403, 'Accès refusé')
    msg = ChatMessage.objects.create(conversation=conv, auteur=request.auth, contenu=payload.contenu)
    if request.auth.role == User.Role.MEDECIN:
        notify_patient_new_message(msg)
    return ChatMessageOut(
        id=msg.id, auteur_id=msg.auteur_id, contenu=msg.contenu,
        lu=msg.lu, created_at=msg.created_at,
    )


@router.get('/conversations/{conv_id}/messages', response=list[ChatMessageOut], auth=jwt_auth)
def list_messages(request, conv_id: int):
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.auth.role == User.Role.PATIENT and conv.patient.user_id != request.auth.id:
        raise HttpError(403, 'Accès refusé')
    if request.auth.role == User.Role.MEDECIN and conv.medecin_id != request.auth.id:
        raise HttpError(403, 'Accès refusé')
    return [
        ChatMessageOut(
            id=m.id, auteur_id=m.auteur_id, contenu=m.contenu,
            lu=m.lu, created_at=m.created_at,
        ) for m in conv.messages.all()
    ]


@router.post('/rappels-medicaments', response=dict, auth=jwt_auth)
def create_reminder(request, payload: ReminderIn):
    patient = get_object_or_404(Patient, user=request.auth)
    r = MedicationReminder.objects.create(
        patient=patient, prescription_id=payload.prescription_id,
        medicament=payload.medicament, heure_prise=payload.heure_prise,
    )
    return {'id': r.id, 'medicament': r.medicament}
