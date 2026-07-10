"""Construction du plan de soins patient."""
from django.utils import timezone as dj_tz

from clinical.models import (
    Consultation,
    Hospitalization,
    MedicationReminder,
    NursingCare,
    Patient,
    Prescription,
    VitalSign,
)

SOIN_STATUTS = {
    'REALISE': 'Réalisé',
    'OMIS': 'Dose omise',
    'EN_RETARD': 'En retard',
    'PLANIFIE': 'Planifié',
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


def _soin_statut(soin: NursingCare) -> tuple[str, str]:
    now = dj_tz.now()
    if soin.realise_a:
        return 'REALISE', SOIN_STATUTS['REALISE']
    if soin.dose_omise:
        return 'OMIS', SOIN_STATUTS['OMIS']
    if soin.planifie_a < now:
        return 'EN_RETARD', SOIN_STATUTS['EN_RETARD']
    return 'PLANIFIE', SOIN_STATUTS['PLANIFIE']


def build_patient_care_plan(patient: Patient) -> dict:
    hosp = Hospitalization.objects.filter(
        patient=patient, statut=Hospitalization.Statut.ACTIVE,
    ).select_related(
        'lit__chambre__service__building', 'medecin_referent',
    ).first()

    hospitalisation = None
    soins = []
    constantes = []

    if hosp:
        lit = hosp.lit
        ch = lit.chambre
        svc = ch.service
        hospitalisation = {
            'id': hosp.id,
            'statut': hosp.statut,
            'statut_label': hosp.get_statut_display(),
            'localisation': _lit_label(hosp),
            'service': svc.nom,
            'chambre': ch.numero,
            'lit': lit.numero_lit,
            'batiment': svc.building.nom,
            'medecin_referent': f'Dr {hosp.medecin_referent.first_name} {hosp.medecin_referent.last_name}'.strip(),
            'motif_admission': hosp.motif_admission,
            'date_entree': hosp.date_entree,
            'date_sortie_prevue': hosp.date_sortie_prevue,
            'notes': hosp.notes or '',
        }

        for s in NursingCare.objects.filter(hospitalisation=hosp).select_related(
            'infirmier', 'prescription',
        ).order_by('planifie_a')[:50]:
            statut, statut_label = _soin_statut(s)
            soins.append({
                'id': s.id,
                'description': s.description,
                'planifie_a': s.planifie_a,
                'realise_a': s.realise_a,
                'dose_omise': s.dose_omise,
                'infirmier_nom': f'{s.infirmier.first_name} {s.infirmier.last_name}'.strip() or s.infirmier.username,
                'statut': statut,
                'statut_label': statut_label,
                'medicament_lie': s.prescription.medicament_nom if s.prescription_id else '',
            })

        constantes = [
            {
                'id': v.id,
                'temperature': float(v.temperature) if v.temperature else None,
                'tension_systolique': v.tension_systolique,
                'tension_diastolique': v.tension_diastolique,
                'frequence_cardiaque': v.frequence_cardiaque,
                'saturation_o2': v.saturation_o2,
                'date_prise': v.date_prise,
            }
            for v in VitalSign.objects.filter(hospitalisation=hosp).order_by('-date_prise')[:10]
        ]

    ordonnances = []
    for c in Consultation.objects.filter(patient=patient, validee=True).select_related('medecin').order_by('-date_consultation')[:15]:
        medecin = f'Dr {c.medecin.first_name} {c.medecin.last_name}'.strip()
        for p in Prescription.objects.filter(consultation=c, validee=True):
            ordonnances.append({
                'id': p.id,
                'medicament': p.medicament_nom,
                'posologie': p.posologie,
                'duree_jours': p.duree_jours,
                'instructions': p.instructions or '',
                'medecin': medecin,
                'date_consultation': c.date_consultation,
            })

    rappels = [
        {
            'id': r.id,
            'medicament': r.medicament,
            'heure_prise': r.heure_prise,
            'actif': r.actif,
        }
        for r in MedicationReminder.objects.filter(patient=patient).order_by('heure_prise')
    ]

    realises = sum(1 for s in soins if s['statut'] == 'REALISE')
    omis = sum(1 for s in soins if s['statut'] == 'OMIS')
    en_attente = sum(1 for s in soins if s['statut'] in ('PLANIFIE', 'EN_RETARD'))

    return {
        'hospitalisation': hospitalisation,
        'soins': soins,
        'constantes': constantes,
        'ordonnances': ordonnances,
        'rappels': rappels,
        'soins_total': len(soins),
        'soins_realises': realises,
        'soins_en_attente': en_attente,
        'soins_omis': omis,
    }
