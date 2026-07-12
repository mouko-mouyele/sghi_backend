"""Envoi SMTP Gmail — compatible Render / Gunicorn."""

import logging
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)


def sghi_from_email() -> str:
    """Gmail exige que l'expéditeur soit le compte SMTP authentifié."""
    user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if not user:
        return settings.DEFAULT_FROM_EMAIL
    return formataddr(('SGHL CHU Brazzaville', user))


def email_is_configured() -> bool:
    return bool(
        (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
        and (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()
    )


def send_sghi_email(subject: str, body: str, to: list[str]) -> tuple[bool, str]:
    """
    Envoie un email texte. Retourne (succès, message_erreur_ou_vide).
    """
    recipients = [e.strip() for e in to if e and '@' in e]
    if not recipients:
        return False, 'Aucun destinataire valide'

    if not (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip():
        preview = (
            f'\n{"=" * 60}\n[SGHL — Email simulé — configurez EMAIL_HOST_USER]\n'
            f'À : {", ".join(recipients)}\nObjet : {subject}\n{"-" * 60}\n{body}\n'
        )
        print(preview)
        logger.info(preview)
        return True, ''

    if not email_is_configured():
        return False, 'EMAIL_HOST_PASSWORD manquant sur le serveur (Render → Environment)'

    try:
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 15)
        connection = get_connection(fail_silently=False, timeout=timeout)
        message = EmailMessage(
            subject=subject,
            body=body.rstrip() + '\n\n— SGHL / CHU Brazzaville',
            from_email=sghi_from_email(),
            to=recipients,
            connection=connection,
        )
        sent = message.send(fail_silently=False)
        logger.info('Email SGHL envoyé (%s) → %s', sent, recipients)
        return True, ''
    except Exception as exc:
        err = str(exc).strip() or exc.__class__.__name__
        logger.exception('Échec envoi email SGHL vers %s', recipients)
        if '535' in err or 'Authentication' in err or 'authentication' in err.lower():
            return False, (
                'Authentification Gmail refusée — vérifiez EMAIL_HOST_PASSWORD '
                '(mot de passe d\'application, sans espaces) dans Render.'
            )
        return False, err
