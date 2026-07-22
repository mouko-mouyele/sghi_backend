"""Envoi email — Brevo API (HTTPS, Render free) ou SMTP Gmail."""

import json
import logging
import os
import urllib.error
import urllib.request
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)


def sghi_from_email() -> str:
    """Gmail/Brevo : l'expéditeur doit correspondre au compte vérifié."""
    user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if not user:
        return settings.DEFAULT_FROM_EMAIL
    return formataddr(('SGHL CHU Brazzaville', user))


def sghi_sender_address() -> str:
    user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if user:
        return user
    default = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    if '<' in default and '>' in default:
        return default.split('<', 1)[1].split('>', 1)[0].strip()
    return default


def brevo_is_configured() -> bool:
    return bool((getattr(settings, 'BREVO_API_KEY', '') or '').strip())


def smtp_is_configured() -> bool:
    return bool(
        (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
        and (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()
    )


def email_is_configured() -> bool:
    return brevo_is_configured() or smtp_is_configured()


def email_provider() -> str:
    if brevo_is_configured():
        return 'brevo'
    if smtp_is_configured():
        return 'smtp'
    return 'none'


def render_smtp_likely_blocked() -> bool:
    """Render free bloque les ports SMTP 25/465/587 depuis sept. 2025."""
    return bool(os.environ.get('RENDER')) and not brevo_is_configured()


def email_diagnostic_message() -> str:
    if brevo_is_configured():
        return (
            'Email via API Brevo (HTTPS) — compatible Render gratuit. '
            'Utilisez « Tester l\'envoi » pour valider.'
        )
    if smtp_is_configured() and render_smtp_likely_blocked():
        return (
            'SMTP Gmail configuré MAIS Render (plan gratuit) bloque le port 587 — '
            'les emails ne partent pas. Ajoutez BREVO_API_KEY dans Render → Environment '
            '(compte gratuit sur brevo.com) ou passez au plan Render payant.'
        )
    if smtp_is_configured():
        return 'SMTP Gmail configuré — utilisez « Tester l\'envoi » pour valider la réception.'
    if (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip():
        return 'EMAIL_HOST_PASSWORD manquant — mot de passe d\'application Gmail dans Render.'
    return 'EMAIL_HOST_USER manquant dans Render → Environment.'


def _simulate_email(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    preview = (
        f'\n{"=" * 60}\n[SGHL — Email simulé — configurez BREVO_API_KEY ou EMAIL_*]\n'
        f'À : {", ".join(recipients)}\nObjet : {subject}\n{"-" * 60}\n{body}\n'
    )
    print(preview)
    logger.info(preview)
    return True, ''


def _send_via_brevo(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    api_key = (getattr(settings, 'BREVO_API_KEY', '') or '').strip()
    sender = sghi_sender_address()
    if not sender or '@' not in sender:
        return False, 'EMAIL_HOST_USER ou DEFAULT_FROM_EMAIL requis comme expéditeur Brevo'

    payload = {
        'sender': {'name': 'SGHL CHU Brazzaville', 'email': sender},
        'to': [{'email': email} for email in recipients],
        'subject': subject,
        'textContent': body.rstrip() + '\n\n— SGHL / CHU Brazzaville',
    }
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email',
        data=data,
        headers={
            'accept': 'application/json',
            'api-key': api_key,
            'content-type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=getattr(settings, 'EMAIL_TIMEOUT', 15)) as response:
            if 200 <= response.status < 300:
                logger.info('Email Brevo envoyé → %s', recipients)
                return True, ''
            return False, f'Brevo HTTP {response.status}'
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:400]
        logger.exception('Échec Brevo vers %s', recipients)
        if exc.code in (401, 403):
            return False, 'Clé API Brevo invalide — vérifiez BREVO_API_KEY dans Render.'
        if exc.code == 400 and 'sender' in detail.lower():
            return False, (
                f'Expéditeur {sender} non vérifié dans Brevo — '
                'ajoutez et validez cette adresse sur brevo.com.'
            )
        return False, f'Brevo : {detail or exc.reason}'
    except Exception as exc:
        logger.exception('Erreur réseau Brevo vers %s', recipients)
        return False, str(exc).strip() or exc.__class__.__name__


def _send_via_smtp(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    if not smtp_is_configured():
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
        logger.info('Email SMTP envoyé (%s) → %s', sent, recipients)
        return True, ''
    except Exception as exc:
        err = str(exc).strip() or exc.__class__.__name__
        logger.exception('Échec SMTP vers %s', recipients)
        if render_smtp_likely_blocked() and any(
            token in err.lower() for token in ('timed out', 'timeout', 'network', 'unreachable', 'connect')
        ):
            return False, (
                'Connexion SMTP impossible — Render (plan gratuit) bloque le port 587. '
                'Ajoutez BREVO_API_KEY (gratuit, brevo.com) dans Render → Environment.'
            )
        if '535' in err or 'authentication' in err.lower():
            return False, (
                'Authentification Gmail refusée — utilisez un mot de passe d\'application Gmail '
                '(sans espaces) dans EMAIL_HOST_PASSWORD.'
            )
        return False, err


def send_sghi_email(subject: str, body: str, to: list[str]) -> tuple[bool, str]:
    """Envoie un email texte. Retourne (succès, message_erreur_ou_vide)."""
    recipients = [e.strip() for e in to if e and '@' in e]
    if not recipients:
        return False, 'Aucun destinataire valide'

    if brevo_is_configured():
        return _send_via_brevo(subject, body, recipients)

    if not (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip():
        return _simulate_email(subject, body, recipients)

    return _send_via_smtp(subject, body, recipients)
