from django.test import SimpleTestCase

from config.maps import normalize_map_provider, public_map_config


class MapConfigTests(SimpleTestCase):
    def test_unknown_provider_fails_closed(self):
        self.assertEqual(normalize_map_provider('nominatim'), 'none')
        self.assertEqual(normalize_map_provider(''), 'none')
        off = public_map_config('nominatim')
        self.assertEqual(off['provider'], 'none')
        self.assertFalse(off['enabled'])
        self.assertFalse(off['nominatim_autocomplete'])
        self.assertFalse(off['invented_centroids'])

    def test_osm_is_attribution_only(self):
        on = public_map_config('osm', 'Map data © OpenStreetMap contributors')
        self.assertTrue(on['enabled'])
        self.assertEqual(on['geocode'], 'none')
        self.assertFalse(on['autocomplete'])
        self.assertEqual(on['pin_policy'], 'device_gps_only')
        self.assertIn('OpenStreetMap', on['attribution'])
