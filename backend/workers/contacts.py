"""
Guest contact-phone column detection.

The local SQLite file may not have workers.0007 yet. Reads and writes must
skip the column until that migration is applied to the connected database.
"""

_CONTACT_PHONE_READY = None
DAILY_REQUEST_TABLE = 'workers_dailyservicerequest'


def reset_daily_contact_phone_cache():
    global _CONTACT_PHONE_READY
    _CONTACT_PHONE_READY = None


def daily_contact_phone_ready():
    """True only when DailyServiceRequest.contact_phone exists on this database."""
    global _CONTACT_PHONE_READY
    if _CONTACT_PHONE_READY is not None:
        return _CONTACT_PHONE_READY
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                DAILY_REQUEST_TABLE,
            )
        _CONTACT_PHONE_READY = any(getattr(col, 'name', None) == 'contact_phone' for col in description)
    except Exception:
        _CONTACT_PHONE_READY = False
    return _CONTACT_PHONE_READY
