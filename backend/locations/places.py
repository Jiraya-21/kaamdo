"""
Optional persisted taluk labels. Missing tables are skipped so live SQLite
without locations migrations keeps working.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import ProgrammingError, OperationalError


def _table_ready():
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)
        return 'locations_listingplace' in tables
    except Exception:
        return False


def save_place(instance, district, taluk, locality):
    if instance is None or getattr(instance, 'pk', None) is None:
        return None
    if not _table_ready():
        return None
    from .models import ListingPlace

    try:
        content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
        place, _created = ListingPlace.objects.update_or_create(
            content_type=content_type,
            object_pk=str(instance.pk),
            defaults={
                'district': district or '',
                'taluk': taluk or '',
                'locality': locality or '',
            },
        )
        return place
    except (ProgrammingError, OperationalError):
        return None


def load_place(instance):
    if instance is None or getattr(instance, 'pk', None) is None:
        return None
    if not _table_ready():
        return None
    from .models import ListingPlace

    try:
        content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
        return ListingPlace.objects.filter(
            content_type=content_type,
            object_pk=str(instance.pk),
        ).first()
    except (ProgrammingError, OperationalError):
        return None


def place_taluk(instance):
    row = load_place(instance)
    return row.taluk if row and row.taluk else ''
