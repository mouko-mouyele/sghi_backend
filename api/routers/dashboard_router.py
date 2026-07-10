"""Statistiques tableau de bord — sans dépendance Redis."""
from decimal import Decimal



from django.db.models import Sum

from django.utils import timezone as dj_tz

from ninja.errors import HttpError



from accounts.models import User

from api.auth import jwt_auth
from api.permissions import require_role
from api.schemas import ComptableChartSeriesOut, DashboardKPIs, RoleDashboardOut
from billing.models import Payment
from clinical.models import Bed, Hospitalization, NursingCare, Patient
from core.billing_chart import build_comptable_chart_series
from core.dashboard_stats import build_role_dashboard

from laboratory.models import LabOrder

from pharmacy.models import StockLot



from ninja import Router



router = Router(tags=['RH & Pilotage'])





def _compute_kpis() -> DashboardKPIs:

    lits_total = Bed.objects.count()

    lits_dispo = Bed.objects.filter(est_disponible=True).count()

    taux_occ = round((1 - lits_dispo / lits_total) * 100, 1) if lits_total else 0

    examens_attente = LabOrder.objects.exclude(

        statut__in=[LabOrder.Statut.PUBLIE, LabOrder.Statut.ANNULE],

    ).count()

    now = dj_tz.now()

    recettes = Payment.objects.filter(

        created_at__year=now.year,

        created_at__month=now.month,

        statut=Payment.Statut.VALIDE,

    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

    alertes_stock = StockLot.objects.filter(quantite__lte=10).count()

    doses_omises = NursingCare.objects.filter(dose_omise=True, realise_a__isnull=True).count()

    return DashboardKPIs(

        taux_occupation=taux_occ,

        lits_disponibles=lits_dispo,

        lits_total=lits_total,

        examens_en_attente=examens_attente,

        recettes_mois=recettes,

        hospitalisations_actives=Hospitalization.objects.filter(

            statut=Hospitalization.Statut.ACTIVE,

        ).count(),

        patients_total=Patient.objects.filter(archived=False).count(),

        alertes_stock=alertes_stock,

        doses_omises=doses_omises,

    )





@router.get('/dashboard/kpis', response=DashboardKPIs, auth=jwt_auth)

def dashboard_kpis(request):

    if request.auth.role == User.Role.PATIENT:

        raise HttpError(403, 'Réservé au personnel hospitalier')

    return _compute_kpis()





@router.get('/dashboard/moi', response=RoleDashboardOut, auth=jwt_auth)

def dashboard_role_stats(request):

    if request.auth.role == User.Role.PATIENT:

        raise HttpError(403, 'Réservé au personnel hospitalier')

    return build_role_dashboard(request.auth)


@router.get('/dashboard/comptable-graphe', response=ComptableChartSeriesOut, auth=jwt_auth)
def comptable_chart_series(request, jours: int = 14):
    require_role(request.auth, User.Role.COMPTABLE, User.Role.ADMIN)
    return build_comptable_chart_series(jours)

