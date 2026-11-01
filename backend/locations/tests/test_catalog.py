from django.test import SimpleTestCase

from locations.catalog import (
    DISTRICT_RECORDS,
    TALUKS_BY_DISTRICT,
    catalog_payload,
    district_names,
    normalize_district,
    normalize_taluk,
    place_label,
    taluk_names,
)


class KarnatakaCatalogTests(SimpleTestCase):
    def test_has_thirty_one_official_districts_including_bengaluru_south(self):
        names = district_names()
        self.assertEqual(len(names), 31)
        self.assertEqual(len(set(names)), 31)
        self.assertIn('Bengaluru Urban', names)
        self.assertIn('Bengaluru Rural', names)
        self.assertIn('Bengaluru South', names)
        self.assertIn('Vijayanagara', names)
        self.assertIn('Mandya', names)
        self.assertNotIn('Ramanagara', names)

    def test_aliases_normalize_to_official_names(self):
        self.assertEqual(normalize_district('Ramanagara'), 'Bengaluru South')
        self.assertEqual(normalize_district('Bangalore'), 'Bengaluru Urban')
        self.assertEqual(normalize_district('Mysore'), 'Mysuru')
        self.assertEqual(normalize_district('not-a-district'), '')

    def test_taluks_are_official_and_have_no_coordinates(self):
        self.assertEqual(normalize_taluk('Bengaluru South', 'Harohalli'), 'Harohalli')
        self.assertEqual(normalize_taluk('Mandya', 'Maddur'), 'Maddur')
        self.assertEqual(normalize_taluk('Mandya', 'Invented village'), '')
        self.assertIn('Mandya', taluk_names('Mandya'))
        payload = catalog_payload()
        self.assertEqual(payload['state']['name'], 'Karnataka')
        self.assertEqual(len(payload['districts']), 31)
        blob = str(payload).casefold()
        self.assertNotIn('latitude', blob)
        self.assertNotIn('longitude', blob)
        for name, _aliases in DISTRICT_RECORDS:
            self.assertTrue(TALUKS_BY_DISTRICT[name])
        self.assertEqual(place_label('Town centre', 'Mandya', 'Mandya'), 'Town centre, Mandya')
