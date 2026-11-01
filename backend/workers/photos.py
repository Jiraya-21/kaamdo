"""
Worker profile photo storage and validation.

Photos are public once a profile is published. Do not store identity documents here.
"""

from pathlib import Path
import secrets

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

WORKER_PHOTO_MAX_BYTES = 2 * 1024 * 1024
WORKER_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
WORKER_PHOTO_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
WORKER_PHOTO_FORMATS = {'JPEG', 'PNG', 'WEBP'}
WORKER_PHOTO_TABLE = 'workers_workerprofile'
PHOTO_MIGRATION_REQUIRED = (
    'Profile photo storage is not available until the photo migration is applied.'
)

_PHOTO_COLUMN_READY = None


def reset_worker_photo_column_cache():
    """Tests and process restarts must not reuse a stale column check."""
    global _PHOTO_COLUMN_READY
    _PHOTO_COLUMN_READY = None


def worker_photo_column_ready():
    """True only when workers.0006 has been applied to the connected database."""
    global _PHOTO_COLUMN_READY
    if _PHOTO_COLUMN_READY is not None:
        return _PHOTO_COLUMN_READY
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                WORKER_PHOTO_TABLE,
            )
        _PHOTO_COLUMN_READY = any(getattr(col, 'name', None) == 'photo' for col in description)
    except Exception:
        _PHOTO_COLUMN_READY = False
    return _PHOTO_COLUMN_READY


def worker_photo_upload_to(instance, filename):
    """Store the file under a per-user folder with a random name, not the original filename."""
    suffix = Path(filename or '').suffix.lower()
    if suffix not in WORKER_PHOTO_EXTENSIONS:
        suffix = '.jpg'
    if suffix == '.jpeg':
        suffix = '.jpg'
    user_id = getattr(instance, 'user_id', None) or 'unknown'
    return f'worker_photos/{user_id}/{secrets.token_hex(16)}{suffix}'


def validate_worker_photo(uploaded):
    """Reject missing, oversized, or non-image uploads before they are stored."""
    if uploaded is None:
        raise ValidationError('A photo file is required.')
    size = getattr(uploaded, 'size', None)
    if size is None:
        raise ValidationError('A photo file is required.')
    if size < 24:
        raise ValidationError('The photo file is too small.')
    if size > WORKER_PHOTO_MAX_BYTES:
        raise ValidationError('Choose a photo of 2 MB or smaller.')

    name = getattr(uploaded, 'name', '') or ''
    suffix = Path(name).suffix.lower()
    if suffix and suffix not in WORKER_PHOTO_EXTENSIONS:
        raise ValidationError('Use a JPEG, PNG, or WebP photo.')

    content_type = (getattr(uploaded, 'content_type', None) or '').lower()
    if content_type and content_type not in WORKER_PHOTO_CONTENT_TYPES and content_type != 'application/octet-stream':
        raise ValidationError('Use a JPEG, PNG, or WebP photo.')

    position = uploaded.tell() if hasattr(uploaded, 'tell') else 0
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image.verify()
            fmt = (image.format or '').upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError('The file is not a usable JPEG, PNG, or WebP photo.') from exc
    finally:
        if hasattr(uploaded, 'seek'):
            uploaded.seek(position)

    if fmt not in WORKER_PHOTO_FORMATS:
        raise ValidationError('Use a JPEG, PNG, or WebP photo.')

    if hasattr(uploaded, 'seek'):
        uploaded.seek(0)


def public_photo_url(profile, request=None):
    """Return an HTTP URL for the stored photo, or None. Never return a filesystem path."""
    if not worker_photo_column_ready():
        return None
    photo = getattr(profile, 'photo', None)
    if not photo:
        return None
    try:
        url = photo.url
    except ValueError:
        return None
    if not url:
        return None
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def replace_worker_photo(profile, uploaded):
    if not worker_photo_column_ready():
        raise ValidationError(PHOTO_MIGRATION_REQUIRED)
    old_name = profile.photo.name if profile.photo else ''
    profile.photo = uploaded
    profile.full_clean()
    profile.save(update_fields=['photo', 'updated_at'])
    if hasattr(profile.photo, 'close'):
        profile.photo.close()
    if old_name and old_name != profile.photo.name:
        try:
            profile.photo.storage.delete(old_name)
        except OSError:
            pass
    return profile


def clear_worker_photo(profile):
    if not worker_photo_column_ready():
        raise ValidationError(PHOTO_MIGRATION_REQUIRED)
    if not profile.photo:
        return profile
    profile.photo.delete(save=False)
    profile.photo = None
    profile.save(update_fields=['photo', 'updated_at'])
    return profile


def delete_stored_photo(profile):
    if not worker_photo_column_ready():
        return
    photo = getattr(profile, 'photo', None)
    if photo:
        photo.delete(save=False)
