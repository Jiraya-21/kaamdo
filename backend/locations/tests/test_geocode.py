from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from locations.geocode import match_karnataka_address, reverse_lookup


class KarnatakaAddressMatchTests(SimpleTestCase):
    def test_matches_official_district_and_taluk(self):
        matched = match_karnataka_address({
            'state': 'Karnataka',
            'county': 'Mandya',
            'municipality': 'Maddur',
            'village': 'Town centre',
        })
        self.assertEqual(matched['district'], 'Mandya')
        self.assertEqual(matched['taluk'], 'Maddur')
        self.assertEqual(matched['locality'], 'Town centre')
        self.assertEqual(matched['display'], 'Town centre, Maddur, Mandya')

    def test_strips_osm_taluk_suffix(self):
        matched = match_karnataka_address({
            'state': 'Karnataka',
            'state_district': 'Mandya',
            'county': 'Mandya taluk',
            'city': 'Mandya',
            'quarter': 'Town centre',
        })
        self.assertEqual(matched['district'], 'Mandya')
        self.assertEqual(matched['taluk'], 'Mandya')
        self.assertEqual(matched['locality'], 'Town centre')

    def test_matches_maharashtra_district_and_street(self):
        matched = match_karnataka_address({
            'state': 'Maharashtra',
            'state_district': 'Pune',
            'county': 'Haveli',
            'suburb': 'Kothrud',
            'road': 'Karve Road',
            'postcode': '411038',
        })
        self.assertEqual(matched['state'], 'Maharashtra')
        self.assertEqual(matched['district'], 'Pune')
        self.assertEqual(matched['taluk'], 'Haveli')
        self.assertEqual(matched['locality'], 'Kothrud')
        self.assertEqual(matched['street'], 'Karve Road')
        self.assertEqual(matched['postcode'], '411038')
        self.assertTrue(matched['in_maharashtra'])

    def test_does_not_invent_unknown_names(self):
        matched = match_karnataka_address({
            'state': 'Tamil Nadu',
            'county': 'Invented',
            'village': 'Somewhere',
        })
        self.assertEqual(matched['district'], '')
        self.assertEqual(matched['taluk'], '')
        self.assertEqual(matched['locality'], 'Somewhere')
        self.assertFalse(matched['in_karnataka'])


class ReverseLookupTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(KAAMDO_GEOCODE_PROVIDER='none')
    def test_disabled_provider_does_not_fetch(self):
        calls = []

        def fetch(lat, lon):
            calls.append((lat, lon))
            return {'address': {'county': 'Mandya'}}

        result = reverse_lookup(12.52, 76.89, fetch=fetch)
        self.assertFalse(result['available'])
        self.assertEqual(result['reason'], 'disabled')
        self.assertEqual(calls, [])

    @override_settings(KAAMDO_GEOCODE_PROVIDER='nominatim_reverse')
    def test_uses_injected_fetch_and_caches(self):
        calls = []

        def fetch(lat, lon):
            calls.append((lat, lon))
            return {
                'address': {
                    'state': 'Karnataka',
                    'county': 'Mandya',
                    'municipality': 'Maddur',
                    'village': 'Town centre',
                }
            }

        first = reverse_lookup(12.52, 76.89, ip='203.0.113.9', fetch=fetch)
        second = reverse_lookup(12.52001, 76.89002, ip='203.0.113.9', fetch=fetch)
        self.assertTrue(first['available'])
        self.assertEqual(first['district'], 'Mandya')
        self.assertEqual(first['taluk'], 'Maddur')
        self.assertEqual(first['locality'], 'Town centre')
        self.assertEqual(len(calls), 1)
        self.assertEqual(second['district'], 'Mandya')


class ReverseGeocodeApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_invalid_coordinates_are_rejected(self):
        response = self.client.post('/api/v1/locations/reverse/', {
            'latitude': 'not-a-number',
            'longitude': '76.89',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data.get('available'))

    @override_settings(KAAMDO_GEOCODE_PROVIDER='none')
    def test_disabled_provider_returns_manual_fallback(self):
        response = self.client.post('/api/v1/locations/reverse/', {
            'latitude': '12.520000',
            'longitude': '76.890000',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['available'])
        self.assertEqual(response.data['reason'], 'disabled')
        self.assertEqual(response.data['district'], '')
        blob = str(response.data).casefold()
        self.assertNotIn('nominatim.openstreetmap.org', blob)
