"""Traitement des photos d'identité du personnel."""

import io
import uuid

from django.core.files.base import ContentFile
from ninja.errors import HttpError
from PIL import Image, UnidentifiedImageError

ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_BYTES = 2 * 1024 * 1024
IDENTITY_SIZE = (400, 533)  # ratio 3:4 — format photo d'identité


def photo_url(user) -> str | None:
    if user.photo:
        return user.photo.url
    return None


def save_staff_photo(user, uploaded_file) -> str:
    content_type = getattr(uploaded_file, 'content_type', '') or ''
    if content_type not in ALLOWED_TYPES:
        raise HttpError(400, 'Format accepté : JPEG, PNG ou WebP (photo d\'identité)')

    raw = uploaded_file.read()
    if len(raw) > MAX_BYTES:
        raise HttpError(400, 'Photo trop volumineuse (maximum 2 Mo)')

    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert('RGB')
    except UnidentifiedImageError as exc:
        raise HttpError(400, 'Fichier image invalide') from exc

    img = _crop_identity(img)
    img = img.resize(IDENTITY_SIZE, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=88, optimize=True)
    buffer.seek(0)

    ext = 'jpg'
    name = f'identite_{user.id}_{uuid.uuid4().hex[:8]}.{ext}'
    if user.photo:
        user.photo.delete(save=False)
    user.photo.save(name, ContentFile(buffer.read()), save=True)
    return user.photo.url


def _crop_identity(img: Image.Image) -> Image.Image:
    """Recadre au centre en ratio 3:4 (format identité)."""
    w, h = img.size
    target_ratio = 3 / 4
    current = w / h
    if current > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif current < target_ratio:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img
