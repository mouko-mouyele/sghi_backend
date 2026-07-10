"""TOTP (RFC 6238) — authentification à deux facteurs sans dépendance externe."""
import base64
import hashlib
import hmac
import secrets
import struct
import time


def generate_mfa_secret(length: int = 16) -> str:
    """Secret base32 pour application authenticator."""
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode('ascii').rstrip('=')


def _decode_secret(secret: str) -> bytes:
    s = (secret or '').strip().upper().replace(' ', '')
    pad = '=' * ((8 - len(s) % 8) % 8)
    try:
        return base64.b32decode(s + pad)
    except Exception:
        return s.encode()


def totp_at(secret: str, for_time: int | None = None, period: int = 30, digits: int = 6) -> str:
    t = (for_time if for_time is not None else int(time.time())) // period
    msg = struct.pack('>Q', t)
    key = _decode_secret(secret)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    if not secret or not code:
        return False
    cleaned = code.strip().replace(' ', '')
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False
    now = int(time.time())
    for delta in range(-window, window + 1):
        if totp_at(secret, now + delta * 30) == cleaned:
            return True
    return False
