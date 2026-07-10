"""Séries temporelles pour le graphique financier comptable."""

from datetime import datetime, time, timedelta

from decimal import Decimal



from django.db.models import Count, Sum

from django.utils import timezone as dj_tz



from billing.mobile_money import montant_restant

from billing.models import Invoice, Payment





def build_comptable_chart_series(days: int = 14) -> dict:

    """Courbes journalières : recettes, impayés, payées, brouillons, opérations."""

    days = max(7, min(days, 31))

    today = dj_tz.localdate()

    start_date = today - timedelta(days=days - 1)



    labels = []

    recettes = []

    impayes = []

    payees = []

    brouillons = []

    operations = []



    for i in range(days):

        d = start_date + timedelta(days=i)

        labels.append(d.strftime('%d/%m'))

        start_dt = dj_tz.make_aware(datetime.combine(d, time.min))

        end_dt = dj_tz.make_aware(datetime.combine(d, time.max))



        pay_agg = Payment.objects.filter(

            created_at__gte=start_dt,

            created_at__lte=end_dt,

            statut=Payment.Statut.VALIDE,

        ).aggregate(total=Sum('montant'), cnt=Count('id'))

        recettes.append(float(pay_agg['total'] or 0))

        operations.append(pay_agg['cnt'] or 0)



        payee_agg = Invoice.objects.filter(

            statut=Invoice.Statut.PAYEE,

            updated_at__gte=start_dt,

            updated_at__lte=end_dt,

        ).aggregate(total=Sum('montant_paye'))

        payees.append(float(payee_agg['total'] or 0))



        brou_agg = Invoice.objects.filter(

            statut=Invoice.Statut.BROUILLON,

            created_at__gte=start_dt,

            created_at__lte=end_dt,

        ).aggregate(total=Sum('montant_patient'))

        brouillons.append(float(brou_agg['total'] or 0))



        impaye_total = Decimal('0')

        for inv in Invoice.objects.filter(

            statut__in=[Invoice.Statut.EMISE, Invoice.Statut.PARTIEL],

            created_at__gte=start_dt,

            created_at__lte=end_dt,

        ):

            impaye_total += montant_restant(inv)

        impayes.append(float(impaye_total))



    return {

        'labels': labels,

        'recettes': recettes,

        'impayes': impayes,

        'payees': payees,

        'brouillons': brouillons,

        'operations': operations,

        'periode_jours': days,

    }


