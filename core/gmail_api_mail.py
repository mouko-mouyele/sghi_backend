"""Envoi email via Gmail API (HTTPS) — fonctionne sur Render, livraison inbox Gmail."""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GMAIL_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GMAIL_SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'


def _clean(value: str) -> str:
    return (value or '').strip().strip('"').strip("'").replace('\n', '').replace('\r', '')


def gmail_api_is_configured() -> bool:
    return bool(
        _clean(getattr(settings, 'GMAIL_CLIENT_ID', ''))
        and _clean(getattr(settings, 'GMAIL_CLIENT_SECRET', ''))
        and _clean(getattr(settings, 'GMAIL_REFRESH_TOKEN', ''))
    )


def _get_access_token() -> tuple[str | None, str]:
    client_id = _clean(getattr(settings, 'GMAIL_CLIENT_ID', ''))
    client_secret = _clean(getattr(settings, 'GMAIL_CLIENT_SECRET', ''))
    refresh_token = _clean(getattr(settings, 'GMAIL_REFRESH_TOKEN', ''))
    try:
        response = requests.post(
            GMAIL_TOKEN_URL,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            },
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
        )
        if response.status_code != 200:
            detail = response.text[:300]
            logger.error('Gmail token HTTP %s : %s', response.status_code, detail)
            if response.status_code == 400 and 'invalid_grant' in detail:
                return None, (
                    'GMAIL_REFRESH_TOKEN expiré ou révoqué — regénérez-le via Google OAuth Playground.'
                )
            return None, f'Gmail OAuth HTTP {response.status_code}: {detail}'
        return response.json().get('access_token'), ''
    except requests.RequestException as exc:
        return None, f'Réseau Gmail OAuth : {exc}'


def verify_gmail_api() -> tuple[bool, str]:
    if not gmail_api_is_configured():
        return False, 'Gmail API non configurée (GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN)'
    token, err = _get_access_token()
    if token:
        return True, 'Gmail API OK — envoi direct depuis votre boîte Gmail'
    return False, err or 'Gmail API indisponible'


def send_via_gmail_api(subject: str, body: str, recipients: list[str], from_email: str) -> tuple[bool, str]:
    token, err = _get_access_token()
    if not token:
        return False, err or 'Impossible d\'obtenir le token Gmail'

    full_text = body.rstrip() + '\n\n— SGHL / CHU Brazzaville'
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = from_email
    message['To'] = ', '.join(recipients)
    message.attach(MIMEText(full_text, 'plain', 'utf-8'))
    html = (
        '<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.5;">'
        f'{full_text.replace(chr(10), "<br>")}'
        '</div>'
    )
    message.attach(MIMEText(html, 'html', 'utf-8'))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        response = requests.post(
            GMAIL_SEND_URL,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'raw': raw},
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
        )
        if response.status_code == 200:
            msg_id = response.json().get('id', '')
            logger.info('Email Gmail API envoyé → %s (id=%s)', recipients, msg_id)
            return True, ''
        detail = response.text[:400]
        logger.error('Gmail send HTTP %s → %s : %s', response.status_code, recipients, detail)
        return False, f'Gmail API HTTP {response.status_code}: {detail}'
    except requests.RequestException as exc:
        logger.exception('Erreur réseau Gmail send vers %s', recipients)
        return False, str(exc).strip() or exc.__class__.__name__
