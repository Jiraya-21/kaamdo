from django.test import SimpleTestCase

from locations.catalog import (
    DISTRICT_RECORDS,
    TALUKS_BY_DISTRICT,
    catalog_payload,
    district_names,
    normalize_district,
    normalize_state,
    normalize_taluk,
    place_label,
    taluk_names,
)
from locations.maharashtra import DISTRICT_RECORDS as MH_DISTRICT_RECORDS
from locations.maharashtra import TALUKS_BY_DISTRICT as MH_TALUKS


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

    def test_maharashtra_has_thirty_six_districts_and_pune_talukas(self):
        names = [name for name, _aliases in MH_DISTRICT_RECORDS]
        self.assertEqual(len(names), 36)
        self.assertEqual(len(set(names)), 36)
        self.assertEqual(normalize_state('MH'), 'Maharashtra')
        self.assertEqual(normalize_district('Poona'), 'Pune')
        self.assertEqual(normalize_district('Sambhajinagar'), 'Aurangabad')
        self.assertEqual(normalize_taluk('Pune', 'Haveli'), 'Haveli')
        self.assertEqual(normalize_taluk('Pune', 'Invented'), '')
        self.assertEqual(taluk_names('Mumbai City'), [])
        payload = catalog_payload()
        self.assertEqual(len(payload['districts']), 31)
        mh = next(row for row in payload['states'] if row['name'] == 'Maharashtra')
        self.assertEqual(len(mh['districts']), 36)
        pune = next(row for row in mh['districts'] if row['name'] == 'Pune')
        self.assertIn('Haveli', pune['taluks'])
        for name, _aliases in MH_DISTRICT_RECORDS:
            if name == 'Mumbai City':
                self.assertEqual(MH_TALUKS[name], ())
            else:
                self.assertTrue(MH_TALUKS[name])
