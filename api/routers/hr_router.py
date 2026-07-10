from django.db import connection

from django.shortcuts import get_object_or_404

from django.utils import timezone as dj_tz

from ninja import Router
from ninja.errors import HttpError

from accounts.models import LoginJournal, User

from api.auth import jwt_auth

from api.permissions import require_role

from api.schemas import ShiftIn, ShiftOut

from hr.models import ShiftSchedule



router = Router(tags=['RH & Pilotage'])





def _shift_out(shift: ShiftSchedule) -> ShiftOut:

    p = shift.personnel

    s = shift.service

    return ShiftOut(

        id=shift.id,

        personnel_id=shift.personnel_id,

        personnel_nom=f'{p.first_name} {p.last_name}'.strip() or p.username,

        service_id=shift.service_id,

        service_nom=s.nom,

        service_code=s.code,

        date_debut=shift.date_debut,

        date_fin=shift.date_fin,

        type_garde=shift.type_garde,

        notes=shift.notes or '',

    )



@router.get('/gardes', response=list[ShiftOut], auth=jwt_auth)

def list_shifts(request, service_id: int = 0):

    require_role(request.auth, User.Role.ADMIN, User.Role.MEDECIN, User.Role.INFIRMIER)

    qs = ShiftSchedule.objects.select_related('personnel', 'service')

    if service_id:

        qs = qs.filter(service_id=service_id)

    return [_shift_out(s) for s in qs.order_by('date_debut')[:100]]





@router.post('/gardes', response=ShiftOut, auth=jwt_auth)

def create_shift(request, payload: ShiftIn):

    require_role(request.auth, User.Role.ADMIN)

    personnel = get_object_or_404(User, id=payload.personnel_id, is_active=True)

    if personnel.role == User.Role.PATIENT:

        raise HttpError(400, 'Le personnel de garde doit être un membre du staff')

    shift = ShiftSchedule.objects.create(**payload.dict())

    shift = ShiftSchedule.objects.select_related('personnel', 'service').get(pk=shift.pk)

    return _shift_out(shift)





@router.get('/journal-connexions', auth=jwt_auth)

def login_journal(request):

    require_role(request.auth, User.Role.ADMIN)

    return list(LoginJournal.objects.select_related('user').order_by('-timestamp')[:100].values(

        'user__username', 'ip_address', 'success', 'timestamp', 'user_agent',

    ))

