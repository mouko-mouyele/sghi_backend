from datetime import datetime, timezone

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import Router
from ninja.errors import HttpError

from accounts.models import User
from api.auth import jwt_auth
from api.permissions import require_role
from api.schemas import (
    LabDashboardOut,
    LabOrderDetailOut,
    LabOrderIn,
    LabOrderOut,
    LabResultBriefOut,
    LabResultIn,
    LabWorkflowStepIn,
    MessageOut,
)
from clinical.models import Patient
from core.audit import log_audit
from core.csv_export import excel_csv_response
from core.middleware import get_audit_meta
from core.pdf import generate_lab_report_pdf
from core.patient_mail import notify_lab_result_published
from laboratory.models import LabOrder, LabResult, LabResultAudit, LabTestCatalog

router = Router(tags=['Laboratoire LIS'])

WORKFLOW_TRANSITIONS = {
    LabOrder.Statut.COMMANDE: [LabOrder.Statut.PRELEVEMENT],
    LabOrder.Statut.PRELEVEMENT: [LabOrder.Statut.AFFECTATION],
    LabOrder.Statut.AFFECTATION: [LabOrder.Statut.SAISIE],
}

STATUT_LABELS = {
    LabOrder.Statut.COMMANDE: 'Commandé',
    LabOrder.Statut.PRELEVEMENT: 'Prélèvement effectué',
    LabOrder.Statut.AFFECTATION: 'Affecté au labo',
    LabOrder.Statut.SAISIE: 'Résultats saisis',
    LabOrder.Statut.VALIDATION: 'En attente validation',
    LabOrder.Statut.PUBLIE: 'Publié',
    LabOrder.Statut.ANNULE: 'Annulé',
}


def _result_brief(result: LabResult | None) -> LabResultBriefOut | None:
    if not result:
        return None
    pdf_url = result.rapport_pdf.url if result.rapport_pdf else None
    return LabResultBriefOut(
        id=result.id,
        valeur=result.valeur,
        unite=result.unite,
        valeur_reference=result.valeur_reference,
        commentaire=result.commentaire,
        valide=result.valide,
        date_validation=result.date_validation,
        pdf_url=pdf_url,
    )


def _order_detail(order: LabOrder) -> LabOrderDetailOut:
    patient = order.patient
    result = getattr(order, 'resultat', None)
    return LabOrderDetailOut(
        id=order.id,
        patient_id=order.patient_id,
        patient_nom=f'{patient.prenom} {patient.nom}',
        patient_dossier=patient.numero_dossier,
        examen_code=order.examen.code,
        examen_libelle=order.examen.libelle,
        statut=order.statut,
        date_commande=order.date_commande,
        date_prelevement=order.date_prelevement,
        notes=order.notes or '',
        resultat=_result_brief(result),
    )


@router.get('/examens', auth=jwt_auth)
def list_lab_tests(request):
    return list(LabTestCatalog.objects.values('id', 'code', 'libelle', 'prix', 'delai_heures'))


@router.get('/tableau-de-bord', response=LabDashboardOut, auth=jwt_auth)
def lab_dashboard(request):
    require_role(
        request.auth,
        User.Role.MEDECIN,
        User.Role.BIOLOGISTE,
        User.Role.ADMIN,
        User.Role.RECEPTIONNISTE,
    )
    today = dj_tz.localdate()
    qs = LabOrder.objects.all()
    en_analyse = qs.filter(
        statut__in=[
            LabOrder.Statut.PRELEVEMENT,
            LabOrder.Statut.AFFECTATION,
            LabOrder.Statut.SAISIE,
        ],
    ).count()
    return LabDashboardOut(
        total_commandes=qs.count(),
        commandes_jour=qs.filter(date_commande__date=today).count(),
        en_attente_prelevement=qs.filter(statut=LabOrder.Statut.COMMANDE).count(),
        en_analyse=en_analyse,
        a_valider=qs.filter(statut=LabOrder.Statut.VALIDATION).count(),
        publies_jour=qs.filter(
            statut=LabOrder.Statut.PUBLIE,
            resultat__date_validation__date=today,
        ).count(),
        publies_total=qs.filter(statut=LabOrder.Statut.PUBLIE).count(),
        examens_catalogue=LabTestCatalog.objects.count(),
    )


@router.get('/commandes', response=list[LabOrderDetailOut], auth=jwt_auth)
def list_lab_orders(request, statut: str = ''):
    require_role(
        request.auth,
        User.Role.MEDECIN,
        User.Role.BIOLOGISTE,
        User.Role.ADMIN,
        User.Role.RECEPTIONNISTE,
    )
    qs = LabOrder.objects.select_related('patient', 'examen', 'resultat', 'resultat__valide_par')
    if statut:
        qs = qs.filter(statut=statut)
    return [_order_detail(o) for o in qs.order_by('-date_commande')[:100]]


@router.get('/commandes/export/csv', auth=jwt_auth)
def export_lab_orders_csv(request, statut: str = ''):
    """Export CSV (séparateur ; + BOM UTF-8) compatible Excel."""
    require_role(
        request.auth,
        User.Role.BIOLOGISTE,
        User.Role.ADMIN,
        User.Role.RECEPTIONNISTE,
    )
    qs = LabOrder.objects.select_related(
        'patient', 'examen', 'resultat', 'resultat__valide_par',
    ).order_by('-date_commande')
    if statut:
        qs = qs.filter(statut=statut)

    headers = [
        'N° commande', 'Date commande', 'N° dossier', 'Patient', 'Examen',
        'Statut', 'Valeur', 'Unité', 'Référence', 'Commentaire',
        'Validé', 'Date validation', 'Biologiste',
    ]
    rows = []
    for order in qs[:500]:
        result = getattr(order, 'resultat', None)
        statut_label = STATUT_LABELS.get(order.statut, order.statut)
        rows.append([
            order.id,
            order.date_commande.strftime('%d/%m/%Y %H:%M'),
            order.patient.numero_dossier,
            f'{order.patient.prenom} {order.patient.nom}',
            order.examen.libelle,
            statut_label,
            result.valeur if result else '',
            result.unite if result else '',
            result.valeur_reference if result else '',
            result.commentaire if result else '',
            'Oui' if result and result.valide else 'Non',
            result.date_validation.strftime('%d/%m/%Y %H:%M') if result and result.date_validation else '',
            (result.valide_par.get_full_name() or result.valide_par.username) if result and result.valide_par else '',
        ])

    csv_bytes = excel_csv_response(rows, headers)
    filename = f'sghl-laboratoire-{dj_tz.now().strftime("%Y%m%d")}.csv'
    response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='ACCESS', model_name='LabOrderExport',
        object_id='csv', ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return response


@router.post('/commandes', response=LabOrderOut, auth=jwt_auth)
def create_lab_order(request, payload: LabOrderIn):
    require_role(request.auth, User.Role.MEDECIN, User.Role.ADMIN)
    examen = get_object_or_404(LabTestCatalog, id=payload.examen_id)
    get_object_or_404(Patient, id=payload.patient_id)
    order = LabOrder.objects.create(
        patient_id=payload.patient_id, examen=examen,
        hospitalisation_id=payload.hospitalisation_id,
        medecin_prescripteur=request.auth, notes=payload.notes,
    )
    return LabOrderOut(
        id=order.id, patient_id=order.patient_id, examen_code=examen.code,
        statut=order.statut, date_commande=order.date_commande,
    )


@router.post('/commandes/{order_id}/workflow', response=MessageOut, auth=jwt_auth)
def advance_lab_workflow(request, order_id: int, payload: LabWorkflowStepIn):
    require_role(request.auth, User.Role.BIOLOGISTE, User.Role.ADMIN)
    order = get_object_or_404(LabOrder, id=order_id)
    allowed = WORKFLOW_TRANSITIONS.get(order.statut, [])
    if payload.statut not in [s.value for s in allowed]:
        raise HttpError(400, f'Transition invalide depuis {order.statut}')
    if payload.statut == LabOrder.Statut.PRELEVEMENT.value:
        order.date_prelevement = dj_tz.now()
        order.technicien = request.auth
    order.statut = payload.statut
    order.save()
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='LabOrder',
        object_id=order.id, new_value={'statut': payload.statut},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return MessageOut(message=f'Étape {payload.statut} enregistrée')


@router.post('/commandes/{order_id}/resultats', auth=jwt_auth)
def submit_lab_result(request, order_id: int, payload: LabResultIn):
    require_role(request.auth, User.Role.BIOLOGISTE, User.Role.ADMIN)
    order = get_object_or_404(LabOrder, id=order_id)
    if order.statut not in (
        LabOrder.Statut.SAISIE, LabOrder.Statut.VALIDATION,
    ):
        raise HttpError(400, 'La commande doit être en saisie avant d\'enregistrer un résultat')
    if hasattr(order, 'resultat'):
        result = order.resultat
        if result.valide:
            raise HttpError(400, 'Résultat validé = immuable')
        old = result.valeur
        result.valeur = payload.valeur
        result.unite = payload.unite
        result.valeur_reference = payload.valeur_reference
        result.commentaire = payload.commentaire
        result.save()
        LabResultAudit.objects.create(
            resultat=result, modifie_par=request.auth,
            ancienne_valeur=old, nouvelle_valeur=payload.valeur,
        )
        meta = get_audit_meta(request)
        log_audit(user=request.auth, action_type='UPDATE', model_name='LabResult',
                  object_id=result.id, old_value={'valeur': old}, new_value={'valeur': payload.valeur},
                  ip_address=meta['ip_address'], user_agent=meta['user_agent'])
    else:
        LabResult.objects.create(
            commande=order, valeur=payload.valeur, unite=payload.unite,
            valeur_reference=payload.valeur_reference, commentaire=payload.commentaire,
            saisi_par=request.auth,
        )
    order.statut = LabOrder.Statut.VALIDATION
    order.save(update_fields=['statut', 'updated_at'])
    return {'message': 'Résultat enregistré — en attente de validation biologiste'}


@router.post('/resultats/{result_id}/valider', auth=jwt_auth)
def validate_lab_result(request, result_id: int):
    require_role(request.auth, User.Role.BIOLOGISTE, User.Role.ADMIN)
    result = get_object_or_404(LabResult, id=result_id)
    if result.valide:
        raise HttpError(400, 'Déjà validé')
    result.valide = True
    result.valide_par = request.auth
    result.date_validation = dj_tz.now()

    patient = result.commande.patient
    pdf_bytes = generate_lab_report_pdf(
        patient_nom=f'{patient.prenom} {patient.nom}',
        examen=result.commande.examen.libelle,
        valeur=result.valeur, unite=result.unite,
        reference=result.valeur_reference,
        biologiste=request.auth.get_full_name() or request.auth.username,
    )
    result.rapport_pdf.save(
        f'rapport_{result.id}.pdf', ContentFile(pdf_bytes), save=False,
    )
    result.save()

    meta = get_audit_meta(request)
    log_audit(user=request.auth, action_type='VALIDATE', model_name='LabResult',
              object_id=result.id, ip_address=meta['ip_address'], user_agent=meta['user_agent'])
    notify_lab_result_published(result)
    return {'message': 'Résultat validé, publié et PDF généré — patient notifié par email'}


@router.get('/resultats/patient/{patient_id}', auth=jwt_auth)
def patient_lab_results(request, patient_id: int):
    patient = get_object_or_404(Patient, id=patient_id)
    if request.auth.role == User.Role.PATIENT:
        if not hasattr(request.auth, 'patient_profile') or request.auth.patient_profile.id != patient_id:
            raise HttpError(403, 'Accès refusé')
    results = LabResult.objects.filter(
        commande__patient=patient, valide=True,
    ).select_related('commande__examen')
    return [
        {
            'id': r.id, 'examen': r.commande.examen.libelle,
            'valeur': r.valeur, 'unite': r.unite,
            'date_validation': r.date_validation.isoformat() if r.date_validation else None,
            'pdf_url': r.rapport_pdf.url if r.rapport_pdf else None,
        } for r in results
    ]
