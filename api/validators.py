"""Validateurs et filtres de saisie — chiffres, lettres ou texte selon le champ."""

import re

from ninja.errors import HttpError

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$')
_LETTERS_ONLY_RE = re.compile(r"[^a-zA-ZÀ-ÿ\s'\-]")
_DIGITS_ONLY_RE = re.compile(r'\D')
_PHONE_CHARS_RE = re.compile(r'[^\d+\s\-]')
_ALNUM_RE = re.compile(r'[^a-zA-Z0-9_\-.]')
_DECIMAL_RE = re.compile(r'[^\d.,]')


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    email = value.strip()
    if not email:
        return None
    if not _EMAIL_RE.match(email):
        raise HttpError(400, 'Adresse email invalide')
    return email


def only_digits(value: str | None) -> str:
    """Chiffres uniquement."""
    return _DIGITS_ONLY_RE.sub('', str(value or ''))


def only_letters(value: str | None) -> str:
    """Lettres, espaces, tirets et apostrophes (noms / prénoms)."""
    return _LETTERS_ONLY_RE.sub('', str(value or ''))


def only_phone(value: str | None) -> str:
    """Téléphone : chiffres, +, espaces et tirets."""
    raw = str(value or '').strip()
    if not raw:
        return ''
    cleaned = _PHONE_CHARS_RE.sub('', raw)
    plus = '+' if cleaned.startswith('+') else ''
    body = cleaned.lstrip('+')
    return f'{plus}{body}' if plus else body


def only_text(value: str | None) -> str:
    """Texte libre : caractères imprimables courants (adresse, description…)."""
    raw = str(value or '')
    allowed = set(" .,;:'\"()-/\\#@&°\n\r\t")
    return ''.join(
        c for c in raw
        if c.isalnum() or c in allowed
    )


def only_alnum(value: str | None) -> str:
    """Lettres, chiffres, tirets, points et underscores (identifiants, dossiers)."""
    return _ALNUM_RE.sub('', str(value or ''))


def only_decimal(value: str | None) -> str:
    """Nombre décimal : chiffres et un séparateur , ou ."""
    raw = _DECIMAL_RE.sub('', str(value or ''))
    sep = ',' if ',' in raw and '.' not in raw else '.'
    parts = raw.replace(',', '.').split('.')
    if len(parts) <= 1:
        return parts[0]
    return parts[0] + sep + ''.join(parts[1:])


def require_letters(value: str | None, label: str = 'Ce champ') -> str:
    cleaned = only_letters(value).strip()
    if not cleaned:
        raise ValueError(f'{label} : lettres uniquement')
    if cleaned != str(value or '').strip():
        raise ValueError(f'{label} : lettres uniquement (pas de chiffres)')
    return cleaned


def require_phone(value: str | None, label: str = 'Téléphone', required: bool = True) -> str:
    raw = str(value or '').strip()
    if not raw:
        if required:
            raise ValueError(f'{label} obligatoire')
        return ''
    cleaned = only_phone(raw)
    digits = only_digits(cleaned)
    if len(digits) < 8:
        raise ValueError(f'{label} invalide — minimum 8 chiffres')
    return cleaned


def require_text(value: str | None) -> str:
    return only_text(value).strip()


def require_alnum(value: str | None, label: str = 'Ce champ') -> str:
    cleaned = only_alnum(value).strip()
    if not cleaned:
        raise ValueError(f'{label} : caractères alphanumériques uniquement')
    return cleaned
