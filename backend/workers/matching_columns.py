"""
Matching-column detection.

The local SQLite file may not have workers.0008 yet. Reads and writes must
skip the new columns until that migration is applied to the connected database.
"""

_REQUEST_READY = None
_OFFER_READY = None
DAILY_REQUEST_TABLE = 'workers_dailyservicerequest'
SERVICE_OFFER_TABLE = 'workers_serviceoffer'
REQUEST_FIELD = 'search_radius_km'
OFFER_FIELD = 'expires_at'


def reset_matching_column_cache():
    global _REQUEST_READY, _OFFER_READY
    _REQUEST_READY = None
    _OFFER_READY = None


def matching_request_columns_ready():
    """True when DailyServiceRequest matching fields exist on this database."""
    global _REQUEST_READY
    if _REQUEST_READY is not None:
        return _REQUEST_READY
    _REQUEST_READY = _table_has_column(DAILY_REQUEST_TABLE, REQUEST_FIELD)
    return _REQUEST_READY


def matching_offer_columns_ready():
    """True when ServiceOffer.expires_at exists on this database."""
    global _OFFER_READY
    if _OFFER_READY is not None:
        return _OFFER_READY
    _OFFER_READY = _table_has_column(SERVICE_OFFER_TABLE, OFFER_FIELD)
    return _OFFER_READY


def _table_has_column(table, column):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table)
        return any(getattr(col, 'name', None) == column for col in description)
    except Exception:
        return False
