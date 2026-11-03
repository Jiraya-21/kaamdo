"""
Reverse geocode a GPS fix and match it to official Karnataka and Maharashtra names.

Nominatim reverse is optional, cached, and rate-limited. This module does not
invent villages, centroids, or autocomplete. Public Nominatim search is refused.
"""

from hashlib import sha256
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

from .catalog import (
    STATE_NAME,
    normalize_district,
    normalize_state,
    normalize_taluk,
    state_for_district,
)
from .maharashtra import STATE_NAME as MH_STATE_NAME

NOMINATIM_REVERSE = 'https://nominatim.openstreetmap.org/reverse'
CACHE_SECONDS = 86400
MIN_INTERVAL_SECONDS = 1.1
IP_HOUR_LIMIT = 20
ALLOWED_PROVIDERS = frozenset({'none', 'nominatim_reverse'})
SUBURBAN_HINTS = frozenset({'andheri', 'borivali', 'kurla'})


def normalize_geocode_provider(value):
    name = str(value or 'none').strip().lower()
    if name in ALLOWED_PROVIDERS:
        return name
    return 'none'


def parse_coordinates(latitude, longitude):
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None
    return round(lat, 6), round(lon, 6)


def _clean_admin_name(value):
    text = ' '.join(str(value or '').split())
    lowered = text.casefold()
    for suffix in (' taluk', ' tehsil', ' tahsil', ' district'):
        if lowered.endswith(suffix):
            return text[:len(text) - len(suffix)].strip()
    return text


def _address_values(address):
    if not isinstance(address, dict):
        return []
    order = (
        'state_district',
        'county',
        'city_district',
        'municipality',
        'city',
        'town',
        'village',
        'suburb',
        'hamlet',
        'neighbourhood',
        'quarter',
    )
    values = []
    for key in order:
        text = _clean_admin_name(address.get(key))
        if text and text not in values:
            values.append(text)
    return values


def match_catalog_address(address):
    """Map an OSM address onto official names. Empty fields stay empty."""
    payload = address if isinstance(address, dict) else {}
    state = normalize_state(payload.get('state')) or ' '.join(str(payload.get('state') or '').split())
    district = ''
    for candidate in _address_values(payload):
        district = normalize_district(candidate)
        if district:
            break
    blob = ' '.join(_address_values(payload)).casefold()
    if district == 'Mumbai City' and any(hint in blob for hint in SUBURBAN_HINTS):
        district = 'Mumbai Suburban'
    if district:
        matched_state = state_for_district(district)
        if matched_state:
            state = matched_state
    taluk = ''
    if district:
        fallback = ''
        for candidate in _address_values(payload):
            matched_taluk = normalize_taluk(district, candidate)
            if not matched_taluk:
                continue
            if matched_taluk == district:
                fallback = fallback or matched_taluk
                continue
            taluk = matched_taluk
            break
        if not taluk:
            taluk = fallback
    locality = ''
    for key in ('village', 'hamlet', 'suburb', 'neighbourhood', 'quarter', 'town'):
        text = ' '.join(str(payload.get(key) or '').split())
        if not text:
            continue
        if district and normalize_district(text) == district:
            continue
        if taluk and normalize_taluk(district, text) == taluk:
            continue
        locality = text
        break
    street = ' '.join(str(payload.get('road') or payload.get('pedestrian') or '').split())
    postcode = ' '.join(str(payload.get('postcode') or '').split())
    village = ' '.join(str(payload.get('village') or '').split())
    display = _display(street, locality or village, taluk, district, postcode)
    return {
        'state': state if isinstance(state, str) else '',
        'in_karnataka': state == STATE_NAME,
        'in_maharashtra': state == MH_STATE_NAME,
        'district': district,
        'taluk': taluk,
        'locality': locality or village,
        'village': village,
        'street': street,
        'postcode': postcode,
        'display': display,
    }


def match_karnataka_address(address):
    return match_catalog_address(address)


def _display(street, locality, taluk, district, postcode):
    parts = []
    for item in (street, locality, taluk, district, postcode):
        text = ' '.join(str(item or '').split())
        if text and text not in parts:
            parts.append(text)
    return ', '.join(parts)


def empty_suggestion(reason):
    return {
        'available': False,
        'provider': normalize_geocode_provider(getattr(settings, 'KAAMDO_GEOCODE_PROVIDER', 'none')),
        'reason': reason,
        'state': '',
        'in_karnataka': False,
        'in_maharashtra': False,
        'district': '',
        'taluk': '',
        'locality': '',
        'village': '',
        'street': '',
        'postcode': '',
        'display': '',
        'attribution': '',
    }


def _fetch_nominatim(latitude, longitude):
    query = urllib.parse.urlencode({
        'lat': f'{latitude:.6f}',
        'lon': f'{longitude:.6f}',
        'format': 'jsonv2',
        'addressdetails': '1',
        'zoom': '18',
    })
    request = urllib.request.Request(
        f'{NOMINATIM_REVERSE}?{query}',
        headers={
            'Accept': 'application/json',
            'User-Agent': str(getattr(
                settings,
                'KAAMDO_GEOCODE_USER_AGENT',
                'KaamDo/1.0 (reverse-geocode; contact: local-development)',
            )),
        },
        method='GET',
    )
    timeout = float(getattr(settings, 'KAAMDO_GEOCODE_TIMEOUT_SECONDS', 8))
    with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        raw = response.read()
    payload = json.loads(raw.decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('unusable')
    return payload


def reverse_lookup(latitude, longitude, *, ip='', fetch=None):
    lat, lon = parse_coordinates(latitude, longitude)
    if lat is None:
        return empty_suggestion('invalid_coordinates')
    provider = normalize_geocode_provider(getattr(settings, 'KAAMDO_GEOCODE_PROVIDER', 'none'))
    if provider == 'none':
        return empty_suggestion('disabled')

    cache_key = 'geocode:' + sha256(f'{round(lat, 4)}:{round(lon, 4)}'.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached:
        return cached

    ip_key = 'geocode-ip:' + sha256(str(ip or 'anon').encode()).hexdigest()
    count = cache.get(ip_key) or 0
    if count >= IP_HOUR_LIMIT:
        return empty_suggestion('rate_limited')

    lock_key = 'geocode-lock'
    last = cache.get(lock_key)
    now = time.time()
    if last and now - float(last) < MIN_INTERVAL_SECONDS:
        return empty_suggestion('rate_limited')
    cache.set(lock_key, now, 10)

    fetcher = fetch or _fetch_nominatim
    try:
        payload = fetcher(lat, lon)
    except (TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError, OSError):
        return empty_suggestion('provider_unavailable')

    matched = match_catalog_address(payload.get('address'))
    result = {
        'available': True,
        'provider': provider,
        'reason': 'ok' if matched['district'] else 'unmatched',
        'state': matched['state'],
        'in_karnataka': matched['in_karnataka'],
        'in_maharashtra': matched['in_maharashtra'],
        'district': matched['district'],
        'taluk': matched['taluk'],
        'locality': matched['locality'],
        'village': matched['village'],
        'street': matched['street'],
        'postcode': matched['postcode'],
        'display': matched['display'] or matched['district'],
        'attribution': 'Map data © OpenStreetMap contributors',
    }
    cache.set(cache_key, result, CACHE_SECONDS)
    cache.set(ip_key, count + 1, 3600)
    return result
