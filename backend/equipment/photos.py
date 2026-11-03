"""Equipment listing photo storage and validation."""

from pathlib import Path
import secrets

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

EQUIPMENT_PHOTO_MAX_BYTES = 2 * 1024 * 1024
EQUIPMENT_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
EQUIPMENT_PHOTO_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
EQUIPMENT_PHOTO_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def equipment_photo_upload_to(instance, filename):
    suffix = Path(filename or '').suffix.lower()
    if suffix not in EQUIPMENT_PHOTO_EXTENSIONS:
        suffix = '.jpg'
    if suffix == '.jpeg':
        suffix = '.jpg'
    owner_id = getattr(instance, 'owner_id', None) or 'unknown'
    return f'equipment_photos/{owner_id}/{secrets.token_hex(16)}{suffix}'


def validate_equipment_photo(uploaded):
    if uploaded is None:
        raise ValidationError('A photo file is required.')
    size = getattr(uploaded, 'size', None)
    if size is None or size < 24:
        raise ValidationError('A photo file is required.')
    if size > EQUIPMENT_PHOTO_MAX_BYTES:
        raise ValidationError('Choose a photo of 2 MB or smaller.')
    name = getattr(uploaded, 'name', '') or ''
    suffix = Path(name).suffix.lower()
    if suffix and suffix not in EQUIPMENT_PHOTO_EXTENSIONS:
        raise ValidationError('Use a JPEG, PNG, or WebP photo.')
    content_type = (getattr(uploaded, 'content_type', None) or '').lower()
    if content_type and content_type not in EQUIPMENT_PHOTO_CONTENT_TYPES and content_type != 'application/octet-stream':
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
    if fmt not in EQUIPMENT_PHOTO_FORMATS:
        raise ValidationError('Use a JPEG, PNG, or WebP photo.')
    if hasattr(uploaded, 'seek'):
        uploaded.seek(0)


def public_equipment_photo_url(listing, request=None):
    photo = getattr(listing, 'photo', None)
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


def replace_equipment_photo(listing, uploaded):
    old_name = listing.photo.name if listing.photo else ''
    listing.photo = uploaded
    listing.full_clean()
    listing.save(update_fields=['photo', 'updated_at'])
    if hasattr(listing.photo, 'close'):
        listing.photo.close()
    if old_name and old_name != listing.photo.name:
        try:
            listing.photo.storage.delete(old_name)
        except OSError:
            pass
    return listing


def clear_equipment_photo(listing):
    if not listing.photo:
        return listing
    listing.photo.delete(save=False)
    listing.photo = None
    listing.save(update_fields=['photo', 'updated_at'])
    return listing
