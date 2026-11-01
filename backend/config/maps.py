"""
Optional map display. Matching never uses a district centroid.

Default provider is none. osm only turns on attribution for a real GPS
fix from the visitor. Nominatim autocomplete is refused.
"""

ALLOWED_PROVIDERS = frozenset({'none', 'osm'})


def normalize_map_provider(value):
    name = str(value or 'none').strip().lower()
    if name in ALLOWED_PROVIDERS:
        return name
    return 'none'


def public_map_config(provider='none', attribution=''):
    name = normalize_map_provider(provider)
    enabled = name == 'osm'
    credit = str(attribution or '').strip() if enabled else ''
    if enabled and not credit:
        credit = 'Map data © OpenStreetMap contributors'
    return {
        'provider': name,
        'enabled': enabled,
        'geocode': 'none',
        'autocomplete': False,
        'nominatim_autocomplete': False,
        'pin_policy': 'device_gps_only',
        'invented_centroids': False,
        'attribution': credit,
    }
