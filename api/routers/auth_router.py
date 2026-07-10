import uuid
from datetime import datetime, timezone

from django.db import transaction
from django.utils import timezone as dj_tz
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from accounts.models import User
from api.auth import (
    authenticate_password,
    complete_mfa_login,
    create_token_pair,
    jwt_auth,
    logout_user,
    rotate_refresh_token,
    validate_password_strength,
)
from api.permissions import STAFF_ROLES, require_role
from api.schemas import (
    LoginIn,
    LoginMfaVerifyIn,
    LoginResultOut,
    LogoutIn,
    MfaSetupOut,
    PaginatedUsersOut,
    PatientRegisterIn,
    RefreshIn,
    StaffRegisterIn,
    TokenOut,
    UserOut,
)
from api.pagination import paginate_queryset, paginated
from clinical.models import Patient
from core.audit import log_audit
from core.middleware import get_audit_meta
from core.staff_photo import photo_url, save_staff_photo

router = Router(tags=['Authentification'])


def _next_dossier_number() -> str:
    count = Patient.objects.count() + 1
    return f'PAT-{datetime.now().year}-{count:05d}'


@router.post('/login', response=LoginResultOut, auth=None)
def auth_login(request, payload: LoginIn):
    result = authenticate_password(request, payload.username, payload.password)
    if not result:
        raise HttpError(401, 'Identifiants invalides')
    return result


@router.post('/login/mfa', response=TokenOut, auth=None)
def auth_login_mfa(request, payload: LoginMfaVerifyIn):
    return complete_mfa_login(request, payload.pending_token, payload.code)


@router.post('/refresh', response=TokenOut, auth=None)
def auth_refresh(request, payload: RefreshIn):
    tokens = rotate_refresh_token(payload.refresh_token)
    if not tokens:
        raise HttpError(401, 'Refresh token invalide ou expiré')
    return tokens


@router.post('/logout', response=dict, auth=jwt_auth)
def auth_logout(request, payload: LogoutIn):
    logout_user(request, request.auth, payload.refresh_token)
    return {'message': 'Déconnexion réussie'}


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        specialty=user.specialty or '',
        phone=user.phone or '',
        photo_url=photo_url(user),
        disponible_rdv=user.disponible_rdv,
        mfa_enabled=user.mfa_enabled,
    )


@router.get('/me', response=UserOut, auth=jwt_auth)
def auth_me(request):
    return _user_out(request.auth)


@router.post('/me/photo', auth=jwt_auth)
def upload_my_photo(request, photo: UploadedFile = File(...)):
    """Photo d'identité — personnel et admin."""
    if request.auth.role == User.Role.PATIENT:
        raise HttpError(403, 'Réservé au personnel hospitalier')
    url = save_staff_photo(request.auth, photo)
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth, action_type='UPDATE', model_name='User',
        object_id=request.auth.id, new_value={'photo': 'uploaded'},
        ip_address=meta['ip_address'], user_agent=meta['user_agent'],
    )
    return {'message': 'Photo d\'identité enregistrée', 'photo_url': url}


@router.post('/register/patient', response=TokenOut, auth=None)
def register_patient(request, payload: PatientRegisterIn):
    """Inscription publique — réservée aux patients."""
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, 'Nom d\'utilisateur déjà pris')
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, 'Email déjà utilisé')
    validate_password_strength(payload.password)

    with transaction.atomic():
        user = User.objects.create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            first_name=payload.prenom,
            last_name=payload.nom,
            role=User.Role.PATIENT,
        )
        patient = Patient.objects.create(
            user=user,
            numero_dossier=_next_dossier_number(),
            nom=payload.nom,
            prenom=payload.prenom,
            date_naissance=payload.date_naissance,
            sexe=payload.sexe,
            telephone=payload.telephone,
            email=payload.email,
            adresse=payload.adresse,
            consentement_traitement=payload.consentement_traitement,
            consentement_date=dj_tz.now() if payload.consentement_traitement else None,
        )
        meta = get_audit_meta(request)
        log_audit(
            user=user,
            action_type='CREATE',
            model_name='Patient',
            object_id=patient.id,
            new_value={'username': user.username, 'numero_dossier': patient.numero_dossier},
            ip_address=meta['ip_address'],
            user_agent=meta['user_agent'],
        )
    return create_token_pair(user)


@router.post('/register/staff', response=UserOut, auth=jwt_auth)
def register_staff(request, payload: StaffRegisterIn):
    """Création de compte personnel — admin uniquement."""
    require_role(request.auth, User.Role.ADMIN)
    if payload.role not in [r.value for r in STAFF_ROLES]:
        raise HttpError(400, 'Rôle personnel invalide')
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, 'Nom d\'utilisateur déjà pris')
    validate_password_strength(payload.password)

    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        specialty=payload.specialty,
        phone=payload.phone,
        is_staff=payload.role == User.Role.ADMIN,
        is_superuser=payload.role == User.Role.ADMIN,
    )
    meta = get_audit_meta(request)
    log_audit(
        user=request.auth,
        action_type='CREATE',
        model_name='User',
        object_id=user.id,
        new_value={'username': user.username, 'role': user.role},
        ip_address=meta['ip_address'],
        user_agent=meta['user_agent'],
    )
    return _user_out(user)


@router.get('/users', response=PaginatedUsersOut, auth=jwt_auth)
def list_users(request, role: str = '', page: int = 1, page_size: int = 10):
    require_role(request.auth, User.Role.ADMIN)
    qs = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    if role:
        qs = qs.filter(role=role)
    items, meta = paginate_queryset(qs, page, page_size)
    return paginated([_user_out(u) for u in items], meta)
