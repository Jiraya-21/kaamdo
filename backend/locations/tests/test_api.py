from django.test import TestCase
from rest_framework.test import APIClient

from locations.catalog import district_names
from locations.models import LocationDistrict


class LocationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_catalog_is_public_and_has_no_coordinates(self):
        response = self.client.get('/api/v1/locations/catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state']['name'], 'Karnataka')
        self.assertEqual(len(response.data['districts']), 31)
        names = [row['name'] for row in response.data['districts']]
        self.assertEqual(names, district_names())
        self.assertIn('Bengaluru South', names)
        states = {row['name']: row for row in response.data['states']}
        self.assertEqual(len(states['Karnataka']['districts']), 31)
        self.assertEqual(len(states['Maharashtra']['districts']), 36)
        mh = self.client.get('/api/v1/locations/districts/', {'state': 'Maharashtra'})
        self.assertEqual(mh.status_code, 200)
        self.assertEqual(mh.data['state']['name'], 'Maharashtra')
        self.assertEqual(len(mh.data['results']), 36)
        self.assertIn('Pune', [row['name'] for row in mh.data['results']])
        blob = str(response.data).casefold()
        self.assertNotIn('latitude', blob)
        self.assertNotIn('longitude', blob)

    def test_taluks_require_an_official_district(self):
        missing = self.client.get('/api/v1/locations/taluks/')
        unknown = self.client.get('/api/v1/locations/taluks/', {'district': 'Invented'})
        south = self.client.get('/api/v1/locations/taluks/', {'district': 'Ramanagara'})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(south.status_code, 200)
        self.assertEqual(south.data['district'], 'Bengaluru South')
        names = [row['name'] for row in south.data['results']]
        self.assertIn('Harohalli', names)
        self.assertIn('Ramanagara', names)
        pune = self.client.get('/api/v1/locations/taluks/', {'district': 'Pune'})
        self.assertEqual(pune.status_code, 200)
        self.assertIn('Haveli', [row['name'] for row in pune.data['results']])

    def test_seed_command_writes_official_rows_only(self):
        from django.core.management import call_command

        call_command('seed_karnataka_locations', verbosity=0)
        self.assertEqual(LocationDistrict.objects.count(), 31)
        self.assertTrue(LocationDistrict.objects.filter(name='Bengaluru South').exists())
        self.assertFalse(LocationDistrict.objects.filter(name='Ramanagara').exists())

    def test_maharashtra_seed_writes_thirty_six_districts(self):
        from django.core.management import call_command

        call_command('seed_karnataka_locations', verbosity=0)
        call_command('seed_maharashtra_locations', verbosity=0)
        self.assertEqual(LocationDistrict.objects.count(), 67)
        self.assertTrue(LocationDistrict.objects.filter(name='Pune').exists())
        self.assertTrue(LocationDistrict.objects.filter(name='Mumbai City').exists())
        self.assertFalse(
            LocationDistrict.objects.get(name='Mumbai City').taluks.exists()
        )

    def test_map_config_is_off_and_has_no_nominatim_autocomplete(self):
        response = self.client.get('/api/v1/locations/map-config/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['provider'], 'none')
        self.assertFalse(response.data['enabled'])
        self.assertFalse(response.data['autocomplete'])
        self.assertFalse(response.data['nominatim_autocomplete'])
        self.assertFalse(response.data['invented_centroids'])
        self.assertEqual(response.data['pin_policy'], 'device_gps_only')
        self.assertEqual(response.data.get('reverse_geocode'), 'none')
        blob = str(response.data).casefold()
        self.assertNotIn('latitude', blob)
        self.assertNotIn('longitude', blob)
