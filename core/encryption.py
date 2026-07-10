"""Chiffrement AES-256 pour données sensibles au repos."""

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet_key() -> bytes:
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return ''
    return Fernet(_fernet_key()).encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    return Fernet(_fernet_key()).decrypt(ciphertext.encode()).decode()
