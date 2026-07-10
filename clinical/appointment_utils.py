from datetime import date, datetime, timedelta, time
from typing import Optional

from django.utils import timezone as dj_tz

from clinical.models import Appointment


def normalize_appointment_datetime(value: datetime) -> datetime:
    """Interprète les dates naïves dans le fuseau de l'hôpital."""
    if dj_tz.is_naive(value):
        return dj_tz.make_aware(value, dj_tz.get_current_timezone())
    return value


def find_appointment_conflict(
    medecin,
    start: datetime,
    duree_minutes: int,
    *,
    exclude_id: Optional[int] = None,
) -> Optional[Appointment]:
    """Retourne le RDV existant qui chevauche le créneau demandé."""
    start = normalize_appointment_datetime(start)
    end = start + timedelta(minutes=duree_minutes)
    qs = Appointment.objects.filter(
        medecin=medecin,
        statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)

    for rdv in qs:
        rdv_start = normalize_appointment_datetime(rdv.date_heure)
        rdv_end = rdv_start + timedelta(minutes=rdv.duree_minutes)
        if start < rdv_end and end > rdv_start:
            return rdv
    return None


def list_occupied_slots(medecin, day: date) -> list[dict]:
    """Créneaux déjà réservés pour un médecin un jour donné."""
    tz = dj_tz.get_current_timezone()
    day_start = dj_tz.make_aware(datetime.combine(day, time.min), tz)
    day_end = day_start + timedelta(days=1)
    rdvs = Appointment.objects.filter(
        medecin=medecin,
        statut__in=[Appointment.Statut.PLANIFIE, Appointment.Statut.CONFIRME],
        date_heure__gte=day_start,
        date_heure__lt=day_end,
    ).order_by('date_heure')
    slots = []
    for rdv in rdvs:
        start = normalize_appointment_datetime(rdv.date_heure)
        end = start + timedelta(minutes=rdv.duree_minutes)
        slots.append({
            'debut': start.isoformat(),
            'fin': end.isoformat(),
            'duree_minutes': rdv.duree_minutes,
        })
    return slots
