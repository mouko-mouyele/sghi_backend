"""Agrégation des données patient pour carte PDF et QR."""
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone as dj_tz

from billing.models import Invoice
from billing.services import invoice_to_dict
from clinical.models import (
    Appointment,
    Consultation,
    Hospitalization,
    MedicationReminder,
    NursingCare,
    Patient,
    PatientCardToken,
    Prescription,
)
from core.models import HospitalInfo
from laboratory.models import LabResult
from pharmacy.models import PatientPharmacyRequest


def _medecin_info(user) -> dict:
    if not user:
        return {}
    return {
        'id': user.id,
        'nom_complet': f'Dr {user.first_name} {user.last_name}'.strip(),
        'prenom': user.first_name or '',
        'nom': user.last_name or '',
        'email': user.email or '',
        'specialite': getattr(user, 'specialty', '') or 'Médecine générale',
        'telephone': getattr(user, 'phone', '') or '',
    }


def _lit_label(hosp: Hospitalization) -> str:
    lit = hosp.lit
    ch = lit.chambre
    svc = ch.service
    bat = svc.building
    return (
        f'Lit {lit.numero_lit} — Chambre {ch.numero} — '
        f'{svc.nom} ({svc.code}) — {bat.nom}'
    )


def build_patient_full_payload(patient: Patient) -> dict:
    info = HospitalInfo.get_instance()

    hospitalisations = []
    for h in Hospitalization.objects.filter(patient=patient).select_related(
        'lit__chambre__service__building', 'medecin_referent',
    ).order_by('-date_entree')[:10]:
        soins = [
            {
                'description': s.description,
                'planifie_a': s.planifie_a.isoformat() if s.planifie_a else None,
                'realise_a': s.realise_a.isoformat() if s.realise_a else None,
                'dose_omise': s.dose_omise,
            }
            for s in NursingCare.objects.filter(hospitalisation=h).order_by('planifie_a')[:20]
        ]
        hospitalisations.append({
            'id': h.id,
            'statut': h.statut,
            'statut_label': h.get_statut_display(),
            'date_entree': h.date_entree.isoformat(),
            'date_sortie_prevue': h.date_sortie_prevue.isoformat() if h.date_sortie_prevue else None,
            'date_sortie_effective': h.date_sortie_effective.isoformat() if h.date_sortie_effective else None,
            'motif_admission': h.motif_admission,
            'notes': h.notes or '',
            'localisation': _lit_label(h),
            'lit': h.lit.numero_lit,
            'chambre': h.lit.chambre.numero,
            'service': h.lit.chambre.service.nom,
            'service_code': h.lit.chambre.service.code,
            'batiment': h.lit.chambre.service.building.nom,
            'medecin_referent': _medecin_info(h.medecin_referent),
            'plan_soins': soins,
        })

    consultations = []
    for c in Consultation.objects.filter(patient=patient, validee=True).select_related('medecin').order_by('-date_consultation')[:30]:
        prescriptions = [
            {
                'id': p.id,
                'medicament': p.medicament_nom,
                'posologie': p.posologie,
                'duree_jours': p.duree_jours,
                'instructions': p.instructions or '',
                'validee': p.validee,
            }
            for p in Prescription.objects.filter(consultation=c, validee=True)
        ]
        consultations.append({
            'id': c.id,
            'date': c.date_consultation.isoformat(),
            'diagnostic_cim10': c.diagnostic_cim10,
            'diagnostic': c.diagnostic_libelle,
            'notes_cliniques': c.notes_cliniques or '',
            'medecin': _medecin_info(c.medecin),
            'ordonnances': prescriptions,
        })

    rendez_vous = [
        {
            'id': r.id,
            'date_heure': r.date_heure.isoformat(),
            'motif': r.motif,
            'statut': r.statut,
            'medecin': _medecin_info(r.medecin),
        }
        for r in Appointment.objects.filter(patient=patient).select_related('medecin').order_by('-date_heure')[:20]
    ]

    factures = [
        invoice_to_dict(inv, include_lines=True)
        for inv in Invoice.objects.filter(patient=patient).prefetch_related('lignes', 'paiements').order_by('-created_at')[:20]
    ]

    resultats_labo = [
        {
            'id': r.id,
            'examen': r.commande.examen.libelle,
            'code_examen': r.commande.examen.code,
            'valeur': r.valeur,
            'unite': r.unite,
            'reference': r.valeur_reference,
            'commentaire': r.commentaire or '',
            'date_validation': r.date_validation.isoformat() if r.date_validation else None,
            'medecin_prescripteur': _medecin_info(r.commande.medecin_prescripteur),
        }
        for r in LabResult.objects.filter(
            commande__patient=patient, valide=True,
        ).select_related('commande__examen', 'commande__medecin_prescripteur').order_by('-date_validation')[:20]
    ]

    demandes_pharmacie = []
    for req in PatientPharmacyRequest.objects.filter(patient=patient).prefetch_related('lignes__medicament').order_by('-created_at')[:10]:
        demandes_pharmacie.append({
            'reference': req.reference,
            'statut': req.statut,
            'montant_total': float(req.montant_total),
            'lignes': [
                {
                    'medicament': l.medicament.nom,
                    'quantite': l.quantite,
                    'prix_unitaire': float(l.prix_unitaire),
                }
                for l in req.lignes.all()
            ],
        })

    rappels = [
        {
            'medicament': r.medicament,
            'heure_prise': r.heure_prise.isoformat(),
            'actif': r.actif,
        }
        for r in MedicationReminder.objects.filter(patient=patient, actif=True)[:20]
    ]

    return {
        'genere_le': dj_tz.now().isoformat(),
        'etablissement': {
            'nom': info.nom_etablissement,
            'adresse': info.adresse,
            'telephone': info.telephone,
            'urgences': info.urgences_telephone,
        },
        'identite': {
            'numero_dossier': patient.numero_dossier,
            'nom': patient.nom,
            'prenom': patient.prenom,
            'nom_complet': patient.nom_complet,
            'date_naissance': patient.date_naissance.isoformat(),
            'sexe': patient.sexe,
            'telephone': patient.telephone or '',
            'email': patient.email or '',
            'adresse': patient.adresse or '',
            'groupe_sanguin': patient.groupe_sanguin or '',
        },
        'hospitalisations': hospitalisations,
        'consultations': consultations,
        'rendez_vous': rendez_vous,
        'factures': factures,
        'resultats_laboratoire': resultats_labo,
        'demandes_pharmacie': demandes_pharmacie,
        'rappels_medicaments': rappels,
    }


def get_or_create_card_token(patient: Patient) -> PatientCardToken:
    valid_days = getattr(settings, 'PATIENT_CARD_TOKEN_DAYS', 365)
    existing = PatientCardToken.objects.filter(
        patient=patient, active=True, expires_at__gt=dj_tz.now(),
    ).order_by('-created_at').first()
    if existing:
        return existing
    PatientCardToken.objects.filter(patient=patient, active=True).update(active=False)
    return PatientCardToken.objects.create(
        patient=patient,
        token=uuid.uuid4().hex,
        expires_at=dj_tz.now() + timedelta(days=valid_days),
        active=True,
    )


def build_qr_scan_url(token: str) -> str:
    base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')
    return f'{base}/qr/{token}'


def generate_and_save_patient_card_pdf(patient: Patient, card_token: PatientCardToken) -> tuple[bytes, str]:
    """Génère le PDF, l'enregistre sous media/cartes_patient/ et retourne (bytes, nom_fichier)."""
    from django.core.files.base import ContentFile

    from core.models import HospitalInfo
    from core.pdf import generate_patient_card_pdf

    info = HospitalInfo.get_instance()
    qr_url = build_qr_scan_url(card_token.token)
    filename = f'carte-{patient.numero_dossier}.pdf'
    pdf_bytes = generate_patient_card_pdf(
        prenom=patient.prenom,
        nom=patient.nom,
        email=patient.email or (patient.user.email if patient.user_id else ''),
        adresse=patient.adresse or '',
        numero_dossier=patient.numero_dossier,
        qr_url=qr_url,
        etablissement=info.nom_etablissement or 'CHU de Brazzaville',
    )
    card_token.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return pdf_bytes, filename
