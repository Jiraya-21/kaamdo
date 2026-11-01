from django.test import SimpleTestCase
from rest_framework import serializers

from locations.validate import official_district, official_taluk


class LocationValidateTests(SimpleTestCase):
    def test_official_district_normalizes_aliases(self):
        self.assertEqual(official_district('Ramanagara'), 'Bengaluru South')
        self.assertEqual(official_district('Bangalore Urban'), 'Bengaluru Urban')

    def test_invented_district_and_taluk_are_refused(self):
        with self.assertRaises(serializers.ValidationError):
            official_district('Not a Karnataka district')
        with self.assertRaises(serializers.ValidationError):
            official_taluk('Mandya', 'Invented village', required=True)
        self.assertEqual(official_taluk('Mandya', 'Maddur'), 'Maddur')
