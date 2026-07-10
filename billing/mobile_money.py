"""Validation et simulation Mobile Money — Congo (MTN / Airtel)."""
import re
import uuid
from decimal import Decimal

from django.utils import timezone as dj_tz
from ninja.errors import HttpError

OPERATEUR_MTN = 'MTN'
OPERATEUR_AIRTEL = 'AIRTEL'

USSD_HINTS = {
    OPERATEUR_MTN: '*133*1# — validez la notification MoMo sur votre téléphone',
    OPERATEUR_AIRTEL: '*128*1# — confirmez le paiement Airtel Money',
}

DEMO_PIN = '1234'


def normalize_phone(raw: str) -> str:
    """Normalise un numéro Congo (+242) vers 9 chiffres locaux (06… / 04… / 05…)."""
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('00242'):
        digits = digits[5:]
    elif digits.startswith('242'):
        digits = digits[3:]
    if len(digits) == 10 and digits.startswith('00'):
        digits = digits[1:]
    if len(digits) == 8 and digits[0] in '645':
        digits = f'0{digits}'
    if len(digits) == 9 and digits.startswith('0'):
        return digits
    if len(digits) == 9 and digits[0] in '645':
        return f'0{digits}'
    raise HttpError(
        400,
        'Numéro invalide. Exemples valides : 06 123 45 67, +242 06 123 45 67, 05 987 65 43',
    )


def phones_equal(a: str, b: str) -> bool:
    try:
        return normalize_phone(a) == normalize_phone(b)
    except HttpError:
        return False


def generate_push_code() -> str:
    import random
    return f'{random.randint(100000, 999999)}'


def detect_operateur(phone: str) -> str:
    normalized = normalize_phone(phone)
    if normalized.startswith('06'):
        return OPERATEUR_MTN
    if normalized.startswith('04') or normalized.startswith('05'):
        return OPERATEUR_AIRTEL
    raise HttpError(
        400,
        'Opérateur non reconnu. MTN MoMo : numéro commençant par 06. '
        'Airtel Money : numéro commençant par 04 ou 05.',
    )


def format_phone_display(phone: str) -> str:
    n = normalize_phone(phone)
    return f'+242 {n[1:3]} {n[3:5]} {n[5:7]} {n[7:9]}'


def new_transaction_reference() -> str:
    return f'MM-{dj_tz.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:10].upper()}'


def validate_confirmation_pin(pin: str, phone: str, push_code: str = '', phone_approved: bool = False) -> None:
    pin = (pin or '').strip()
    if push_code and pin == push_code:
        return
    if phone_approved and pin.isdigit() and 4 <= len(pin) <= 6:
        return
    if not pin or len(pin) < 4:
        raise HttpError(400, 'Saisissez votre code PIN Mobile Money (4 chiffres minimum).')
    normalized = normalize_phone(phone)
    last4 = normalized[-4:]
    if pin in (DEMO_PIN, last4):
        return
    raise HttpError(
        400,
        'Code refusé. Approuvez d\'abord sur votre téléphone, ou saisissez le code reçu par SMS.',
    )


def montant_restant(invoice) -> Decimal:
    return max(invoice.montant_patient - invoice.montant_paye, Decimal('0'))
