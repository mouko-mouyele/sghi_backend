import uuid
from decimal import Decimal

from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from ninja import Router
from ninja.errors import HttpError

from accounts.models import User
from api.auth import jwt_auth
from api.permissions import require_role
from api.schemas import (
    DispenseIn,
    MedicationOut,
    MessageOut,
    PharmacyRequestLineOut,
    PharmacyRequestOut,
    PharmacyRequestStatusIn,
    StockAlertOut,
)
from clinical.models import Prescription
from pharmacy.models import (
    Dispensation,
    Medication,
    PatientPharmacyRequest,
    PatientPharmacyRequestLine,
    StockLot,
    StockMovement,
)
from core.patient_mail import notify_pharmacy_request_submitted, notify_pharmacy_status_updated

router = Router(tags=['Pharmacie'])

STATUT_LABELS = dict(PatientPharmacyRequest.Statut.choices)


def _medication_out(med: Medication) -> MedicationOut:
    stock = med.lots.aggregate(total=Sum('quantite'))['total'] or 0
    return MedicationOut(
        id=med.id,
        code=med.code,
        nom=med.nom,
        forme=med.forme or '',
        categorie=med.categorie,
        categorie_label=med.get_categorie_display(),
        description=med.description or '',
        prix_unitaire=med.prix_unitaire,
        stock_disponible=stock,
        disponible=stock > 0,
        seuil_alerte=med.seuil_alerte,
    )


def _request_out(req: PatientPharmacyRequest, include_patient: bool = True) -> PharmacyRequestOut:
    patient = req.patient
    lignes = [
        {
            'id': l.id,
            'medicament_id': l.medicament_id,
            'medicament_nom': l.medicament.nom,
            'medicament_code': l.medicament.code,
            'forme': l.medicament.forme or '',
            'quantite': l.quantite,
            'prix_unitaire': l.prix_unitaire,
            'sous_total': l.sous_total,
        }
        for l in req.lignes.select_related('medicament')
    ]
    return PharmacyRequestOut(
        id=req.id,
        reference=req.reference,
        statut=req.statut,
        statut_label=STATUT_LABELS.get(req.statut, req.statut),
        notes=req.notes or '',
        montant_total=req.montant_total,
        created_at=req.created_at,
        patient_id=patient.id if include_patient else None,
        patient_nom=f'{patient.prenom} {patient.nom}' if include_patient else None,
        patient_dossier=patient.numero_dossier if include_patient else None,
        lignes=[PharmacyRequestLineOut(**x) for x in lignes],
    )


@router.get('/medicaments', response=list[MedicationOut], auth=jwt_auth)
def list_medications(request, categorie: str = '', q: str = ''):
    """Catalogue complet — accessible à tout utilisateur authentifié."""
    qs = Medication.objects.prefetch_related('lots').order_by('categorie', 'nom')
    if categorie:
        qs = qs.filter(categorie=categorie)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    return [_medication_out(m) for m in qs]


@router.get('/medicaments/categories', auth=jwt_auth)
def medication_categories(request):
    return [
        {'code': code, 'label': label, 'count': Medication.objects.filter(categorie=code).count()}
        for code, label in Medication.Categorie.choices
        if Medication.objects.filter(categorie=code).exists()
    ]


@router.get('/stocks', auth=jwt_auth)
def pharmacy_stock(request):
    require_role(
        request.auth,
        User.Role.PHARMACIEN, User.Role.ADMIN, User.Role.MEDECIN,
        User.Role.INFIRMIER, User.Role.RECEPTIONNISTE,
    )
    lots = StockLot.objects.select_related('medicament').order_by('medicament__nom')
    return [
        {
            'id': l.id,
            'medicament': l.medicament.nom,
            'medicament_id': l.medicament_id,
            'code': l.medicament.code,
            'forme': l.medicament.forme,
            'prix_unitaire': l.medicament.prix_unitaire,
            'lot': l.numero_lot,
            'quantite': l.quantite,
            'peremption': l.date_peremption.isoformat(),
            'alerte': l.en_rupture,
            'seuil': l.medicament.seuil_alerte,
        }
        for l in lots
    ]


@router.get('/alertes', response=list[StockAlertOut], auth=jwt_auth)
def stock_alerts(request):
    require_role(request.auth, User.Role.PHARMACIEN, User.Role.ADMIN)
    alerts = []
    for lot in StockLot.objects.select_related('medicament'):
        if lot.en_rupture:
            alerts.append(StockAlertOut(
                medicament=lot.medicament.nom,
                lot=lot.numero_lot,
                quantite=lot.quantite,
                seuil=lot.medicament.seuil_alerte,
                en_rupture=True,
                date_peremption=lot.date_peremption,
            ))
    return alerts


@router.get('/mouvements', auth=jwt_auth)
def stock_movements(request):
    require_role(request.auth, User.Role.PHARMACIEN, User.Role.ADMIN)
    return list(StockMovement.objects.select_related('lot__medicament').order_by('-created_at')[:100].values(
        'id', 'type_mouvement', 'quantite', 'motif', 'created_at',
        'lot__medicament__nom', 'lot__numero_lot',
    ))


@router.get('/demandes', response=list[PharmacyRequestOut], auth=jwt_auth)
def list_pharmacy_requests(request, statut: str = ''):
    require_role(
        request.auth,
        User.Role.PHARMACIEN, User.Role.ADMIN, User.Role.MEDECIN,
        User.Role.RECEPTIONNISTE,
    )
    qs = PatientPharmacyRequest.objects.select_related('patient').prefetch_related('lignes__medicament')
    if statut:
        qs = qs.filter(statut=statut)
    return [_request_out(r) for r in qs.order_by('-created_at')[:200]]


@router.patch('/demandes/{request_id}/statut', response=PharmacyRequestOut, auth=jwt_auth)
def update_pharmacy_request_status(request, request_id: int, payload: PharmacyRequestStatusIn):
    require_role(request.auth, User.Role.PHARMACIEN, User.Role.ADMIN)
    req = get_object_or_404(
        PatientPharmacyRequest.objects.select_related('patient').prefetch_related('lignes__medicament'),
        id=request_id,
    )
    allowed = {s.value for s in PatientPharmacyRequest.Statut}
    if payload.statut not in allowed:
        raise HttpError(400, f'Statut invalide. Valeurs : {", ".join(sorted(allowed))}')
    if req.statut in (PatientPharmacyRequest.Statut.RETIREE, PatientPharmacyRequest.Statut.ANNULEE):
        raise HttpError(400, 'Cette demande est clôturée')
    old_statut = req.statut
    req.statut = payload.statut
    req.save(update_fields=['statut', 'updated_at'])
    notify_pharmacy_status_updated(req, old_statut=old_statut)
    return _request_out(req)


@router.post('/dispenser', response=MessageOut, auth=jwt_auth)
def dispense_prescription(request, payload: DispenseIn):
    """Décrémentation automatique lors validation prescription."""
    require_role(request.auth, User.Role.PHARMACIEN, User.Role.ADMIN)
    prescription = get_object_or_404(Prescription, id=payload.prescription_id)
    if not prescription.validee:
        raise HttpError(400, 'Prescription non validée par le médecin')
    lot = get_object_or_404(StockLot, id=payload.lot_id)
    if lot.quantite < payload.quantite:
        raise HttpError(400, 'Stock insuffisant')
    Dispensation.objects.create(
        prescription=prescription,
        lot=lot,
        quantite=payload.quantite,
        pharmacien=request.auth,
        validee=True,
    )
    return MessageOut(message='Dispensation validée', detail=f'Stock restant : {lot.quantite}')


def new_pharmacy_request_reference() -> str:
    return f'PH-{dj_tz.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}'


def create_patient_pharmacy_request(patient, payload) -> PharmacyRequestOut:
    from api.schemas import PharmacyRequestIn
    if not isinstance(payload, PharmacyRequestIn):
        raise HttpError(400, 'Données invalides')
    if not payload.lignes:
        raise HttpError(400, 'Sélectionnez au moins un produit')

    seen = set()
    lines_data = []
    for line in payload.lignes:
        if line.medicament_id in seen:
            raise HttpError(400, 'Produit en double dans la demande')
        seen.add(line.medicament_id)
        if line.quantite < 1 or line.quantite > 99:
            raise HttpError(400, 'Quantité invalide (1 à 99 par produit)')
        med = get_object_or_404(Medication, id=line.medicament_id)
        stock = med.stock_total
        if stock < line.quantite:
            raise HttpError(400, f'Stock insuffisant pour {med.nom} (disponible : {stock})')
        lines_data.append((med, line.quantite))

    req = PatientPharmacyRequest.objects.create(
        patient=patient,
        reference=new_pharmacy_request_reference(),
        notes=(payload.notes or '').strip(),
        statut=PatientPharmacyRequest.Statut.SOUMISE,
    )
    for med, qty in lines_data:
        PatientPharmacyRequestLine.objects.create(
            demande=req,
            medicament=med,
            quantite=qty,
            prix_unitaire=med.prix_unitaire,
        )
    req = PatientPharmacyRequest.objects.select_related('patient').prefetch_related('lignes__medicament').get(id=req.id)
    notify_pharmacy_request_submitted(req)
    return _request_out(req)
