import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone as dj_tz
from ninja.errors import HttpError
from ninja.security import HttpBearer

from accounts.models import LoginJournal, LoginMfaChallenge, RefreshToken, User
from core.audit import log_audit
from core.mfa_email import generate_login_code, mask_email, mfa_destination_for_user, send_login_mfa_code
from core.middleware import get_audit_meta

MFA_PENDING_TTL = 300  # 5 minutes — code invalide après expiration


def _normalize_mfa_code(code: str) -> str:
    """Accepte 123456 ou 012345 — normalise en 6 chiffres."""
    digits = re.sub(r'\D', '', code or '')
    if not digits or len(digits) > 6:
        return ''
    return digits.zfill(6)


def _create_access_token(user: User) -> str:
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'role': user.role,
        'type': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_LIFETIME_MINUTES),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_password_strength(password: str, user=None):
    try:
        validate_password(password, user)
    except DjangoValidationError as e:
        raise HttpError(400, ' '.join(e.messages))
    if not re.search(r'[A-Z]', password):
        raise HttpError(400, 'Le mot de passe doit contenir une majuscule')
    if not re.search(r'[a-z]', password):
        raise HttpError(400, 'Le mot de passe doit contenir une minuscule')
    if not re.search(r'\d', password):
        raise HttpError(400, 'Le mot de passe doit contenir un chiffre')


def create_token_pair(user: User) -> dict:
    access = _create_access_token(user)
    refresh_raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_LIFETIME_DAYS)
    RefreshToken.objects.create(
        user=user,
        token_hash=_hash_token(refresh_raw),
        expires_at=expires,
    )
    return {
        'access_token': access,
        'refresh_token': refresh_raw,
        'token_type': 'bearer',
        'expires_in': settings.JWT_ACCESS_LIFETIME_MINUTES * 60,
        'role': user.role,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def rotate_refresh_token(old_raw: str) -> dict | None:
    token_hash = _hash_token(old_raw)
    try:
        old = RefreshToken.objects.select_related('user').get(
            token_hash=token_hash, revoked=False,
        )
    except RefreshToken.DoesNotExist:
        return None
    if old.expires_at < datetime.now(timezone.utc):
        old.revoked = True
        old.save(update_fields=['revoked'])
        return None
    old.revoked = True
    old.save(update_fields=['revoked'])
    pair = create_token_pair(old.user)
    new_hash = _hash_token(pair['refresh_token'])
    new_token = RefreshToken.objects.get(token_hash=new_hash)
    old.replaced_by = new_token
    old.save(update_fields=['replaced_by'])
    return pair


def revoke_refresh_token(raw: str) -> bool:
    token_hash = _hash_token(raw)
    updated = RefreshToken.objects.filter(token_hash=token_hash, revoked=False).update(revoked=True)
    return updated > 0


class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('type') != 'access':
                return None
            try:
                user_id = int(payload['sub'])
            except (TypeError, ValueError, KeyError):
                return None
            user = User.objects.filter(id=user_id, is_active=True).first()
            if user:
                request.user = user
            return user
        except jwt.PyJWTError:
            return None


jwt_auth = JWTAuth()


def _store_mfa_challenge(user: User, pending: str, code: str) -> datetime:
    expires = dj_tz.now() + timedelta(seconds=MFA_PENDING_TTL)
    LoginMfaChallenge.objects.filter(user=user).delete()
    LoginMfaChallenge.objects.create(
        pending_token=pending,
        user=user,
        code=code,
        expires_at=expires,
    )
    return expires


def _create_mfa_challenge(user: User) -> dict:
    dest, channel, masked = mfa_destination_for_user(user)
    if not dest or '@' not in dest:
        if user.role == User.Role.PATIENT:
            raise HttpError(
                400,
                'Aucune adresse email personnelle enregistrée pour ce compte patient.',
            )
        raise HttpError(
            400,
            'Boîte mail de l\'hôpital non configurée (MFA_HOSPITAL_EMAIL ou Admin → Infos pratiques).',
        )

    with transaction.atomic():
        now = dj_tz.now()
        existing = (
            LoginMfaChallenge.objects.select_for_update()
            .filter(user=user, expires_at__gt=now)
            .order_by('-created_at')
            .first()
        )

        send_email = True
        if existing:
            code = existing.code
            pending = existing.pending_token
            existing.expires_at = now + timedelta(seconds=MFA_PENDING_TTL)
            existing.save(update_fields=['expires_at'])
            expires_at = existing.expires_at
            send_email = False
        else:
            code = generate_login_code()
            pending = secrets.token_urlsafe(32)
            expires_at = _store_mfa_challenge(user, pending, code)

    if send_email:
        ok, _, sent_channel = send_login_mfa_code(user, code)
        if not ok:
            LoginMfaChallenge.objects.filter(pending_token=pending).delete()
            if user.role == User.Role.PATIENT:
                raise HttpError(400, 'Impossible d\'envoyer le code à votre email personnel.')
            raise HttpError(400, 'Impossible d\'envoyer le code à la boîte mail de l\'hôpital.')
    else:
        sent_channel = channel

    hint = masked or mask_email(dest)
    if channel == 'hopital':
        hint_msg = f'boîte mail de l\'hôpital ({hint})'
    else:
        hint_msg = f'votre email personnel ({hint})'

    result = {
        'requires_mfa': True,
        'pending_token': pending,
        'mfa_sent_to': hint,
        'mfa_channel': sent_channel,
        'mfa_hint': hint_msg if send_email else f'{hint_msg} — utilisez le code déjà envoyé par email',
        'mfa_expires_in': MFA_PENDING_TTL,
        'mfa_expires_at': expires_at.isoformat(),
        'access_token': '',
        'refresh_token': '',
        'token_type': 'bearer',
        'expires_in': 0,
        'role': user.role,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'mfa_dev_code': '',
    }
    if settings.DEBUG:
        result['mfa_dev_code'] = code
    return result


def authenticate_password(request, username: str, password: str) -> dict | None:
    """Vérifie identifiants — envoie code MFA par email pour tous les utilisateurs."""
    meta = get_audit_meta(request)
    user = authenticate(request, username=username, password=password)
    LoginJournal.objects.create(
        user=user if user else User.objects.filter(username=username).first(),
        ip_address=meta['ip_address'],
        user_agent=meta['user_agent'],
        success=bool(user),
    )
    if not user or not user.is_active:
        return None
    return _create_mfa_challenge(user)


def complete_mfa_login(request, pending_token: str, code: str) -> dict:
    token = (pending_token or '').strip()
    challenge = LoginMfaChallenge.objects.select_related('user').filter(
        pending_token=token,
    ).first()
    if not challenge:
        raise HttpError(
            401,
            'Session expirée. Reconnectez-vous pour recevoir un nouveau code.',
        )
    if challenge.expires_at <= dj_tz.now():
        challenge.delete()
        raise HttpError(
            401,
            'Code expiré — validité de 5 minutes dépassée. Reconnectez-vous pour un nouveau code.',
        )
    user = challenge.user
    if not user.is_active:
        challenge.delete()
        raise HttpError(401, 'Compte désactivé.')
    cleaned = _normalize_mfa_code(code)
    if not cleaned:
        raise HttpError(401, 'Saisissez les 6 chiffres du code reçu par email.')
    if cleaned != challenge.code:
        raise HttpError(
            401,
            'Code incorrect — utilisez le dernier email reçu (un seul code actif à la fois).',
        )
    challenge.delete()
    meta = get_audit_meta(request)
    log_audit(
        user=user,
        action_type='LOGIN',
        model_name='User',
        object_id=user.id,
        ip_address=meta['ip_address'],
        user_agent=meta['user_agent'],
    )
    return create_token_pair(user)


def login_user(request, username: str, password: str) -> dict | None:
    """Compatibilité mobile ancienne — échec si MFA requis."""
    result = authenticate_password(request, username, password)
    if not result:
        return None
    if result.get('requires_mfa'):
        return None
    return result


def logout_user(request, user, refresh_token: str):
    revoke_refresh_token(refresh_token)
    meta = get_audit_meta(request)
    log_audit(
        user=user,
        action_type='LOGOUT',
        model_name='User',
        object_id=user.id,
        ip_address=meta['ip_address'],
        user_agent=meta['user_agent'],
    )
