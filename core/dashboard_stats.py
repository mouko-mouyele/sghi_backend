"""Statistiques tableau de bord adaptées au rôle utilisateur."""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone as dj_tz

from accounts.models import User
from billing.mobile_money import montant_restant
from billing.models import Invoice, Payment
from clinical.models import Appointment, Bed, Hospitalization, NursingCare, Patient
from laboratory.models import LabOrder
from pharmacy.models import PatientPharmacyRequest, StockLot


def _month_payments(now):
    return Payment.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
        statut=Payment.Statut.VALIDE,
    )


def _today_range(now):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59)
    return start, end


def build_role_dashboard(user: User) -> dict:
    now = dj_tz.now()
    today_start, today_end = _today_range(now)
    role = user.role

    lits_total = Bed.objects.count()
    lits_dispo = Bed.objects.filter(est_disponible=True).count()
    taux_occ = round((1 - lits_dispo / lits_total) * 100, 1) if lits_total else 0
    hosp_actives = Hospitalization.objects.filter(statut=Hospitalization.Statut.ACTIVE).count()
    patients_total = Patient.objects.filter(archived=False).count()
    examens_attente = LabOrder.objects.exclude(
        statut__in=[LabOrder.Statut.PUBLIE, LabOrder.Statut.ANNULE],
    ).count()
    recettes_mois = _month_payments(now).aggregate(t=Sum('montant'))['t'] or Decimal('0')
    recettes_jour = Payment.objects.filter(
        created_at__gte=today_start,
        created_at__lte=today_end,
        statut=Payment.Statut.VALIDE,
    ).aggregate(t=Sum('montant'))['t'] or Decimal('0')
    doses_omises = NursingCare.objects.filter(dose_omise=True, realise_a__isnull=True).count()
    alertes_stock = StockLot.objects.filter(quantite__lte=10).count()

    base = {
        'role': role,
        'role_label': user.get_role_display() if hasattr(user, 'get_role_display') else role,
        'taux_occupation': taux_occ,
        'lits_disponibles': lits_dispo,
        'lits_total': lits_total,
        'hospitalisations_actives': hosp_actives,
        'patients_total': patients_total,
        'examens_en_attente': examens_attente,
        'recettes_mois': recettes_mois,
        'recettes_jour': recettes_jour,
        'doses_omises': doses_omises,
        'alertes_stock': alertes_stock,
    }

    if role == User.Role.COMPTABLE or role == User.Role.ADMIN:
        impayees_qs = Invoice.objects.filter(statut__in=[Invoice.Statut.EMISE, Invoice.Statut.PARTIEL])
        base.update({
            'factures_impayees': impayees_qs.count(),
            'factures_payees_mois': Invoice.objects.filter(
                statut=Invoice.Statut.PAYEE,
                updated_at__year=now.year,
                updated_at__month=now.month,
            ).count(),
            'factures_brouillon': Invoice.objects.filter(statut=Invoice.Statut.BROUILLON).count(),
            'montant_impaye_total': sum(montant_restant(i) for i in impayees_qs.select_related('patient')[:500]),
            'paiements_jour': Payment.objects.filter(
                created_at__gte=today_start,
                created_at__lte=today_end,
                statut=Payment.Statut.VALIDE,
            ).count(),
        })

    if role in (User.Role.INFIRMIER, User.Role.ADMIN, User.Role.MEDECIN):
        pending = NursingCare.objects.filter(realise_a__isnull=True, dose_omise=False)
        base.update({
            'soins_en_attente': pending.filter(planifie_a__gte=now).count(),
            'soins_en_retard': pending.filter(planifie_a__lt=now).count(),
            'soins_realises_jour': NursingCare.objects.filter(
                realise_a__gte=today_start,
                realise_a__lte=today_end,
            ).count(),
        })

    if role in (User.Role.RECEPTIONNISTE, User.Role.ADMIN):
        base.update({
            'rdv_aujourdhui': Appointment.objects.filter(
                date_heure__gte=today_start,
                date_heure__lte=today_end,
            ).exclude(statut=Appointment.Statut.ANNULE).count(),
            'rdv_en_attente': Appointment.objects.filter(
                statut=Appointment.Statut.PLANIFIE,
                date_heure__gte=now,
            ).count(),
        })

    if role in (User.Role.PHARMACIEN, User.Role.ADMIN):
        base.update({
            'demandes_pharmacie': PatientPharmacyRequest.objects.exclude(
                statut__in=[
                    PatientPharmacyRequest.Statut.RETIREE,
                    PatientPharmacyRequest.Statut.ANNULEE,
                ],
            ).count(),
        })

    if role in (User.Role.BIOLOGISTE, User.Role.ADMIN):
        base.update({
            'labo_a_valider': LabOrder.objects.filter(statut=LabOrder.Statut.VALIDATION).count(),
            'labo_publies_jour': LabOrder.objects.filter(
                statut=LabOrder.Statut.PUBLIE,
                updated_at__gte=today_start,
            ).count(),
        })

    if role == User.Role.MEDECIN:
        base.update({
            'mes_rdv_jour': Appointment.objects.filter(
                medecin=user,
                date_heure__gte=today_start,
                date_heure__lte=today_end,
            ).exclude(statut=Appointment.Statut.ANNULE).count(),
        })

    return base
