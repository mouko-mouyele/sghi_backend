"""MFA par email — personnel → boîte hôpital, patient → email personnel."""

import logging
import secrets

from django.conf import settings

from accounts.models import User
from core.models import HospitalInfo
from core.sghi_mail import email_is_configured, send_sghi_email

logger = logging.getLogger(__name__)


def generate_login_code() -> str:
    return f'{secrets.randbelow(1_000_000):06d}'


def get_hospital_email() -> str:
    configured = getattr(settings, 'MFA_HOSPITAL_EMAIL', '') or ''
    if configured.strip():
        return configured.strip()
    info = HospitalInfo.get_instance()
    if info.email:
        return info.email.strip()
    if settings.EMAIL_HOST_USER:
        return settings.EMAIL_HOST_USER.strip()
    return ''


def get_patient_personal_email(user: User) -> str:
    email = (user.email or '').strip()
    if email:
        return email
    profile = getattr(user, 'patient_profile', None)
    if profile and profile.email:
        return profile.email.strip()
    return ''


def mfa_destination_for_user(user: User) -> tuple[str, str, str]:
    """
    Retourne (email_destinataire, canal, libellé affiché).
    canal: 'hopital' | 'personnel'
    """
    if user.role == User.Role.PATIENT:
        pe = get_patient_personal_email(user)
        return pe, 'personnel', mask_email(pe) if pe else ''

    hospital = get_hospital_email()
    return hospital, 'hopital', mask_email(hospital) if hospital else 'boîte mail de l\'hôpital'


def mask_email(email: str) -> str:
    if not email or '@' not in email:
        return email or ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    return f'{masked_local}@{domain}'


def send_login_mfa_code(user: User, code: str) -> tuple[bool, str, str, str]:
    """Envoie le code MFA. Retourne (succès, email_dest, canal, erreur)."""
    dest, channel, masked = mfa_destination_for_user(user)
    if not dest or '@' not in dest:
        if user.role == User.Role.PATIENT:
            return False, '', 'personnel', 'Aucune adresse email patient enregistrée.'
        return False, '', 'hopital', 'Boîte mail hôpital non configurée.'

    role_label = user.get_role_display() if hasattr(user, 'get_role_display') else user.role
    if channel == 'hopital':
        subject = f'[SGHL] Code de connexion personnel — {user.username}'
        intro = (
            f'Une connexion au système SGHL a été demandée pour le compte personnel suivant :\n\n'
            f'Utilisateur : {user.username}\n'
            f'Nom : {user.first_name} {user.last_name}\n'
            f'Rôle : {role_label}\n\n'
            f'Code de vérification (valide 5 minutes) : {code}\n\n'
            f'Si vous n\'êtes pas à l\'origine de cette demande, ignorez ce message.'
        )
    else:
        subject = '[SGHL] Votre code de connexion patient'
        intro = (
            f'Bonjour {user.first_name},\n\n'
            f'Voici votre code de connexion au portail patient SGHL (valide 5 minutes) :\n\n'
            f'  {code}\n\n'
            f'Ne partagez ce code avec personne.'
        )

    body = intro

    if not email_is_configured():
        preview = (
            f'\n{"=" * 60}\n'
            f'[SGHL — MFA email simulé]\n'
            f'À : {dest}\n'
            f'Objet : {subject}\n'
            f'Code : {code}\n'
            f'{"=" * 60}\n'
        )
        print(preview)
        logger.info(preview)
        return True, dest, channel, 'BREVO_API_KEY absent sur Render — email simulé uniquement.'

    ok, err = send_sghi_email(subject, body, [dest])
    if not ok:
        logger.error('MFA email non livré à %s : %s', dest, err)
        return False, dest, channel, err or 'Échec envoi email'
    return True, dest, channel, ''


def dispatch_login_mfa_email(user: User, code: str) -> tuple[bool, str]:
    """Envoie le code MFA (synchrone — fiable sur Render/Gunicorn)."""
    ok, _, _, err = send_login_mfa_code(user, code)
    return ok, err
