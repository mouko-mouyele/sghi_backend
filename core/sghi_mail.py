"""Envoi email — Brevo API (HTTPS, Render free) ou SMTP Gmail."""

import logging
import os

import requests
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
BREVO_ACCOUNT_URL = 'https://api.brevo.com/v3/account'


def _clean_secret(value: str) -> str:
    cleaned = (value or '').strip().strip('"').strip("'")
    return cleaned.replace('\n', '').replace('\r', '')


def sghi_from_email() -> str:
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


def brevo_api_key() -> str:
    return _clean_secret(getattr(settings, 'BREVO_API_KEY', '') or '')


def brevo_is_configured() -> bool:
    return bool(brevo_api_key())


def brevo_key_format_ok() -> bool:
    key = brevo_api_key()
    return key.startswith('xkeysib-')


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
    return bool(os.environ.get('RENDER')) and not brevo_is_configured()


def verify_brevo_account() -> tuple[bool, str]:
    """Teste la clé API Brevo (GET /v3/account)."""
    key = brevo_api_key()
    if not key:
        return False, 'BREVO_API_KEY absente sur Render'
    if not brevo_key_format_ok():
        return False, (
            'Clé invalide : utilisez une clé API (xkeysib-…) depuis Brevo → SMTP et API → '
            'Clés API — pas la clé SMTP (xsmtpsib-…).'
        )
    try:
        response = requests.get(
            BREVO_ACCOUNT_URL,
            headers={'accept': 'application/json', 'api-key': key},
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
        )
        if response.status_code == 200:
            data = response.json()
            plan = data.get('plan', [{}])
            plan_type = plan[0].get('type', '') if plan else ''
            return True, f'Compte Brevo OK ({plan_type or "actif"})'
        if response.status_code in (401, 403):
            return False, 'Clé API Brevo refusée — recréez une clé API (xkeysib-) dans Brevo.'
        if response.status_code == 402:
            return False, 'Compte Brevo à activer — vérifiez votre email Brevo ou contactez le support.'
        return False, f'Brevo compte HTTP {response.status_code}: {response.text[:200]}'
    except requests.RequestException as exc:
        return False, f'Réseau Brevo : {exc}'


def email_diagnostic_message() -> str:
    if brevo_is_configured():
        if not brevo_key_format_ok():
            return (
                'BREVO_API_KEY présente mais format incorrect — '
                'utilisez une clé API xkeysib- (pas xsmtpsib- SMTP).'
            )
        ok, detail = verify_brevo_account()
        if ok:
            return f'Email via API Brevo (HTTPS) — {detail}. Testez l\'envoi ci-dessous.'
        return detail
    if smtp_is_configured() and render_smtp_likely_blocked():
        return (
            'SMTP Gmail configuré MAIS Render (plan gratuit) bloque le port 587. '
            'Ajoutez BREVO_API_KEY (clé xkeysib-) dans Render → Environment.'
        )
    if smtp_is_configured():
        return 'SMTP Gmail configuré — utilisez « Tester l\'envoi » pour valider la réception.'
    if (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip():
        return 'EMAIL_HOST_PASSWORD manquant — mot de passe d\'application Gmail dans Render.'
    return 'BREVO_API_KEY manquante dans Render → Environment.'


def _simulate_email(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    preview = (
        f'\n{"=" * 60}\n[SGHL — Email simulé — configurez BREVO_API_KEY]\n'
        f'À : {", ".join(recipients)}\nObjet : {subject}\n{"-" * 60}\n{body}\n'
    )
    print(preview)
    logger.info(preview)
    return True, ''


def _html_body(text: str) -> str:
    escaped = (
        text.rstrip()
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.5;color:#222;">'
        f'{escaped.replace(chr(10), "<br>")}'
        '<p style="color:#666;margin-top:16px;">— SGHL / CHU Brazzaville</p></div>'
    )


def _send_via_brevo(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    key = brevo_api_key()
    sender = sghi_sender_address()
    if not sender or '@' not in sender:
        return False, 'EMAIL_HOST_USER ou DEFAULT_FROM_EMAIL requis comme expéditeur Brevo'
    if not brevo_key_format_ok():
        return False, (
            'BREVO_API_KEY invalide — copiez une clé API xkeysib- depuis '
            'Brevo → SMTP et API → Clés API (pas la clé SMTP xsmtpsib-).'
        )

    full_text = body.rstrip() + '\n\n— SGHL / CHU Brazzaville'
    sender_id = getattr(settings, 'BREVO_SENDER_ID', None)
    sender_payload: dict = {'name': 'SGHL CHU Brazzaville', 'email': sender}
    if sender_id:
        try:
            sender_payload = {'id': int(sender_id)}
        except (TypeError, ValueError):
            pass

    payload = {
        'sender': sender_payload,
        'to': [{'email': email} for email in recipients],
        'subject': subject,
        'textContent': full_text,
        'htmlContent': _html_body(body),
        'tags': ['sghl', 'transactional'],
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            headers={
                'accept': 'application/json',
                'api-key': key,
                'content-type': 'application/json',
            },
            json=payload,
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
        )
        if response.status_code in (200, 201, 202):
            try:
                message_id = response.json().get('messageId', '')
            except Exception:
                message_id = ''
            logger.info('Email Brevo envoyé → %s (messageId=%s)', recipients, message_id)
            return True, ''

        detail = response.text[:400]
        logger.error('Brevo HTTP %s → %s : %s', response.status_code, recipients, detail)
        if response.status_code in (401, 403):
            return False, 'Clé API Brevo refusée — recréez une clé xkeysib- dans Brevo.'
        if response.status_code == 402:
            return False, 'Compte Brevo non activé — vérifiez votre compte sur brevo.com.'
        if response.status_code == 400:
            lowered = detail.lower()
            if 'sender' in lowered or 'from' in lowered:
                return False, (
                    f'Expéditeur {sender} non autorisé — vérifiez qu\'il est '
                    f'"Vérifié" dans Brevo → Expéditeurs.'
                )
        return False, f'Brevo HTTP {response.status_code}: {detail}'
    except requests.RequestException as exc:
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
                'Connexion SMTP impossible — Render bloque le port 587. '
                'Ajoutez BREVO_API_KEY (xkeysib-) dans Render.'
            )
        if '535' in err or 'authentication' in err.lower():
            return False, (
                'Authentification Gmail refusée — mot de passe d\'application Gmail requis.'
            )
        return False, err


def send_sghi_email(subject: str, body: str, to: list[str]) -> tuple[bool, str]:
    recipients = [e.strip() for e in to if e and '@' in e]
    if not recipients:
        return False, 'Aucun destinataire valide'

    if brevo_is_configured():
        return _send_via_brevo(subject, body, recipients)

    if not (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip():
        return _simulate_email(subject, body, recipients)

    return _send_via_smtp(subject, body, recipients)
