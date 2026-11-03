"""
Official Karnataka administrative names used by KaamDo forms and filters.

Districts: Government of Karnataka district portal
https://karnataka.s3waas.gov.in/ (retrieved 27 October 2026).
Bengaluru South is official: renamed from Ramanagara on 23 May 2025
(https://bengalurusouth.nic.in/en/). Mandya is an established official
district; the portal HTML scrape mixed its label with Raichur, so Mandya
is included from the same 31-district set.

Taluks: compiled from the same district set, Bengaluru South NIC taluk
list (Ramanagara, Channapatna, Kanakapura, Magadi, Harohalli), and the
public taluk compilation at
https://en.wikipedia.org/wiki/List_of_taluks_of_Karnataka
with official English spellings. Wikipedia OCR typos were not copied.

This file does not invent villages, localities, or coordinates.
Matching must use a real GPS fix from the device, never a district point.
"""

STATE_NAME = 'Karnataka'
STATE_CODE = 'KA'

DISTRICT_RECORDS = (
    ('Bagalkote', ('Bagalkot',)),
    ('Ballari', ('Bellary',)),
    ('Belagavi', ('Belgaum',)),
    ('Bengaluru Rural', ('Bangalore Rural', 'Bengaluru rural')),
    ('Bengaluru South', ('Ramanagara', 'Ramanagaram', 'Bangalore South', 'Bengaluru south')),
    ('Bengaluru Urban', ('Bangalore', 'Bangalore Urban', 'Bengaluru', 'Bengaluru urban')),
    ('Bidar', ()),
    ('Chamarajanagar', ('Chamarajanagara',)),
    ('Chikkaballapur', ('Chikkaballapura', 'Chikballapur')),
    ('Chikkamagaluru', ('Chikmagalur', 'Chikkamagalur')),
    ('Chitradurga', ()),
    ('Dakshina Kannada', ('South Canara', 'Dakshina kannada')),
    ('Davanagere', ('Davangere',)),
    ('Dharwad', ()),
    ('Gadag', ()),
    ('Hassan', ()),
    ('Haveri', ()),
    ('Kalaburagi', ('Gulbarga',)),
    ('Kodagu', ('Coorg',)),
    ('Kolar', ()),
    ('Koppal', ('Koppala',)),
    ('Mandya', ()),
    ('Mysuru', ('Mysore',)),
    ('Raichur', ('Raichuru',)),
    ('Shivamogga', ('Shimoga',)),
    ('Tumakuru', ('Tumkur',)),
    ('Udupi', ()),
    ('Uttara Kannada', ('North Canara', 'Karwar district')),
    ('Vijayanagara', ('Vijayanagar',)),
    ('Vijayapura', ('Bijapur',)),
    ('Yadgir', ('Yadagiri',)),
)

TALUKS_BY_DISTRICT = {
    'Bagalkote': (
        ('Bagalkote', ('Bagalkot',)),
        ('Badami', ()),
        ('Bilagi', ()),
        ('Hungund', ('Hunagunda',)),
        ('Ilkal', ()),
        ('Jamkhandi', ('Jamkhangi',)),
        ('Mudhol', ('Mudhola',)),
        ('Rabkavi Banhatti', ()),
        ('Terdal', ()),
    ),
    'Ballari': (
        ('Ballari', ('Bellary',)),
        ('Kampli', ()),
        ('Kurugodu', ()),
        ('Sandur', ('Sanduru',)),
        ('Siruguppa', ('Siraguppa',)),
    ),
    'Belagavi': (
        ('Athani', ()),
        ('Bailhongal', ()),
        ('Belagavi', ('Belgaum',)),
        ('Chikkodi', ('Chikodi',)),
        ('Gokak', ()),
        ('Hukkeri', ()),
        ('Kagwad', ('Kagawada',)),
        ('Khanapur', ('Khanapura',)),
        ('Kittur', ('Kitturu',)),
        ('Mudalgi', ()),
        ('Nipani', ('Nippani',)),
        ('Ramdurg', ('Ramadurga',)),
        ('Raybag', ('Rayabaga',)),
        ('Saundatti', ('Savadatti',)),
        ('Yaragatti', ('Yargatti',)),
    ),
    'Bengaluru Rural': (
        ('Devanahalli', ()),
        ('Doddaballapura', ('Doddaballapur',)),
        ('Hosakote', ('Hoskote',)),
        ('Nelamangala', ()),
    ),
    'Bengaluru South': (
        ('Channapatna', ('Channapattana',)),
        ('Harohalli', ()),
        ('Kanakapura', ()),
        ('Magadi', ()),
        ('Ramanagara', ('Ramanagaram',)),
    ),
    'Bengaluru Urban': (
        ('Anekal', ()),
        ('Bengaluru East', ('Krishnarajapura', 'Krishnarajapuram', 'K R Pura')),
        ('Bengaluru North', ('Bengaluru',)),
        ('Bengaluru South', ()),
        ('Kengeri', ()),
        ('Yelahanka', ()),
    ),
    'Bidar': (
        ('Aurad', ()),
        ('Basavakalyan', ('Basavakalyana',)),
        ('Bhalki', ()),
        ('Bidar', ()),
        ('Chitguppa', ('Chitgoppa',)),
        ('Hulsoor', ('Hulsuru',)),
        ('Humnabad', ()),
        ('Kamalnagar', ('Kamalanagara',)),
    ),
    'Chamarajanagar': (
        ('Chamarajanagar', ('Chamarajanagara',)),
        ('Gundlupet', ('Gundlupete',)),
        ('Hanur', ('Hanuru',)),
        ('Kollegal', ('Kollegala',)),
        ('Yelandur', ('Yelanduru',)),
    ),
    'Chikkaballapur': (
        ('Bagepalli', ()),
        ('Chelur', ()),
        ('Chikkaballapur', ('Chikkaballapura',)),
        ('Chintamani', ()),
        ('Gauribidanur', ('Gauribidanuru',)),
        ('Gudibanda', ()),
        ('Manchenahalli', ()),
        ('Sidlaghatta', ()),
    ),
    'Chikkamagaluru': (
        ('Ajjampura', ()),
        ('Chikkamagaluru', ('Chikmagalur',)),
        ('Kadur', ('Kaduru',)),
        ('Kalasa', ()),
        ('Koppa', ()),
        ('Mudigere', ()),
        ('Narasimharajapura', ()),
        ('Sringeri', ()),
        ('Tarikere', ()),
    ),
    'Chitradurga': (
        ('Challakere', ()),
        ('Chitradurga', ()),
        ('Hiriyur', ()),
        ('Holalkere', ()),
        ('Hosadurga', ()),
        ('Molakalmuru', ()),
    ),
    'Dakshina Kannada': (
        ('Bantwal', ('Bantwala',)),
        ('Belthangady', ('Belathangadi',)),
        ('Kadaba', ()),
        ('Mangaluru', ('Mangalore',)),
        ('Moodbidri', ()),
        ('Mulki', ()),
        ('Puttur', ('Putturu',)),
        ('Sullia', ('Sulya',)),
        ('Ullal', ()),
    ),
    'Davanagere': (
        ('Channagiri', ()),
        ('Davanagere', ('Davangere',)),
        ('Harihara', ()),
        ('Honnali', ()),
        ('Jagalur', ('Jagaluru',)),
        ('Nyamathi', ()),
    ),
    'Dharwad': (
        ('Alnavar', ('Alnavara',)),
        ('Annigeri', ()),
        ('Dharwad', ()),
        ('Hubballi Rural', ('Hubli Rural', 'Hubballi (Rural)')),
        ('Hubballi Urban', ('Hubli Urban', 'Hubballi (Urban)', 'Hubballi')),
        ('Kalghatgi', ()),
        ('Kundgol', ('Kundagolu',)),
        ('Navalgund', ('Navalgunda',)),
    ),
    'Gadag': (
        ('Gadag', ()),
        ('Gajendragad', ('Gajendragada',)),
        ('Lakshmeshwar', ('Lakshmeshwara',)),
        ('Mundargi', ('Mundaragi',)),
        ('Nargund', ('Naragunda',)),
        ('Ron', ('Rona',)),
        ('Shirahatti', ()),
    ),
    'Hassan': (
        ('Alur', ('Aluru',)),
        ('Arkalgud', ('Arakalagudu',)),
        ('Arsikere', ('Arasikere',)),
        ('Belur', ('Beluru',)),
        ('Channarayapatna', ('Channarayapattana',)),
        ('Hassan', ()),
        ('Holenarasipura', ('Holenarsipura',)),
        ('Sakleshpur', ('Sakleshpura',)),
    ),
    'Haveri': (
        ('Byadgi', ()),
        ('Hangal', ('Hangala',)),
        ('Haveri', ()),
        ('Hirekerur', ('Hirekeruru',)),
        ('Ranebennur', ('Ranibennur',)),
        ('Rattihalli', ()),
        ('Savanur', ('Savanuru',)),
        ('Shiggaon', ('Shiggavi',)),
    ),
    'Kalaburagi': (
        ('Afzalpur', ('Afzalpura',)),
        ('Aland', ()),
        ('Chincholi', ()),
        ('Chitapur', ('Chitapura',)),
        ('Jewargi', ('Jevargi',)),
        ('Kalaburagi', ('Gulbarga',)),
        ('Kalgi', ()),
        ('Kamalapur', ('Kamalapura',)),
        ('Sedam', ()),
        ('Shahabad', ()),
        ('Yedrami', ()),
    ),
    'Kodagu': (
        ('Kushalnagar', ('Kushalnagara',)),
        ('Madikeri', ()),
        ('Ponnampet', ('Ponnammapete',)),
        ('Somwarpet', ('Somawarapete',)),
        ('Virajpet', ('Virajapete',)),
    ),
    'Kolar': (
        ('Bangarapet', ('Bangarapete',)),
        ('Kolar', ()),
        ('Kolar Gold Fields', ('Robertsonpet', 'KGF')),
        ('Malur', ('Maluru',)),
        ('Mulbagal', ('Mulabagilu',)),
        ('Srinivaspur', ('Srinivasapura',)),
    ),
    'Koppal': (
        ('Gangavathi', ()),
        ('Kanakagiri', ()),
        ('Karatagi', ()),
        ('Koppal', ('Koppala',)),
        ('Kukanur', ('Kukanuru',)),
        ('Kushtagi', ()),
        ('Yelburga', ('Yelaburga',)),
    ),
    'Mandya': (
        ('Krishnarajapet', ('Krishnarajapete', 'K R Pet')),
        ('Maddur', ('Madduru',)),
        ('Malavalli', ()),
        ('Mandya', ()),
        ('Nagamangala', ()),
        ('Pandavapura', ()),
        ('Srirangapatna', ('Srirangapattana',)),
    ),
    'Mysuru': (
        ('Heggadadevanakote', ('H D Kote',)),
        ('Hunsur', ('Hunasuru',)),
        ('Krishnarajanagara', ('K R Nagar',)),
        ('Mysuru', ('Mysore',)),
        ('Nanjangud', ('Nanjanagodu',)),
        ('Periyapatna', ('Piriyapattana',)),
        ('Saligrama', ()),
        ('Saragur', ('Saraguru',)),
        ('T. Narasipura', ('Tirumakudalu Narasipura', 'T Narasipura')),
    ),
    'Raichur': (
        ('Devadurga', ()),
        ('Lingasugur', ('Lingasaguru',)),
        ('Manvi', ()),
        ('Maski', ()),
        ('Mudgal', ()),
        ('Raichur', ('Raichuru',)),
        ('Sindhanur', ('Sindhanuru',)),
        ('Sirwar', ('Sirawara',)),
    ),
    'Shivamogga': (
        ('Bhadravati', ('Bhadravathi',)),
        ('Hosanagara', ()),
        ('Sagar', ('Sagara',)),
        ('Shikaripura', ()),
        ('Shivamogga', ('Shimoga',)),
        ('Soraba', ()),
        ('Thirthahalli', ('Tirthahalli',)),
    ),
    'Tumakuru': (
        ('Chikkanayakanahalli', ()),
        ('Gubbi', ()),
        ('Koratagere', ()),
        ('Kunigal', ()),
        ('Madhugiri', ()),
        ('Pavagada', ()),
        ('Sira', ()),
        ('Tiptur', ('Tipturu',)),
        ('Tumakuru', ('Tumkur',)),
        ('Turuvekere', ()),
    ),
    'Udupi': (
        ('Brahmavar', ('Brahmavara',)),
        ('Byndoor', ('Bynduru',)),
        ('Hebri', ()),
        ('Kapu', ()),
        ('Karkala', ()),
        ('Kundapura', ()),
        ('Udupi', ()),
    ),
    'Uttara Kannada': (
        ('Ankola', ()),
        ('Bhatkal', ()),
        ('Dandeli', ()),
        ('Haliyal', ()),
        ('Honnavar', ('Honnavara',)),
        ('Joida', ()),
        ('Karwar', ('Karwara',)),
        ('Kumta', ()),
        ('Mundgod', ('Mundagodu',)),
        ('Siddapur', ('Siddapura',)),
        ('Sirsi', ()),
        ('Yellapur', ('Yellapura',)),
    ),
    'Vijayanagara': (
        ('Hagaribommanahalli', ()),
        ('Harapanahalli', ()),
        ('Hosapete', ('Hospet',)),
        ('Hoovina Hadagali', ()),
        ('Kotturu', ()),
        ('Kudligi', ()),
    ),
    'Vijayapura': (
        ('Almel', ('Alamela',)),
        ('Babaleshwar', ('Babaleshwara',)),
        ('Basavana Bagewadi', ()),
        ('Chadchan', ('Chadchana',)),
        ('Devara Hipparagi', ()),
        ('Indi', ()),
        ('Kolhar', ('Kolhara',)),
        ('Muddebihal', ('Muddebihala',)),
        ('Nidagundi', ()),
        ('Sindagi', ('Sindgi',)),
        ('Talikoti', ('Talikote',)),
        ('Tikota', ('Tikote',)),
        ('Vijayapura', ('Bijapur',)),
    ),
    'Yadgir': (
        ('Gurmitkal', ('Gurmitkala',)),
        ('Hunsagi', ()),
        ('Shahapur', ('Shahapura',)),
        ('Surpur', ('Surapura',)),
        ('Wadagera', ('Vadagera',)),
        ('Yadgir', ('Yadagiri',)),
    ),
}

SOURCES = (
    {
        'label': 'Karnataka district portal',
        'url': 'https://karnataka.s3waas.gov.in/',
        'used_for': 'Official 31-district names including Bengaluru Urban, Bengaluru Rural, and Bengaluru South.',
    },
    {
        'label': 'Bengaluru South district NIC',
        'url': 'https://bengalurusouth.nic.in/en/',
        'used_for': 'Rename from Ramanagara (23 May 2025) and the five official taluks.',
    },
    {
        'label': 'List of taluks of Karnataka (compilation)',
        'url': 'https://en.wikipedia.org/wiki/List_of_taluks_of_Karnataka',
        'used_for': 'Taluk names by district. Spellings were cleaned. Villages and coordinates were not copied.',
    },
    {
        'label': 'List of districts of Maharashtra',
        'url': 'https://en.wikipedia.org/wiki/List_of_districts_of_Maharashtra',
        'used_for': 'Official 36 Maharashtra districts. Villages, streets, and PIN codes were not copied.',
    },
    {
        'label': 'List of talukas of Maharashtra',
        'url': 'https://en.wikipedia.org/wiki/List_of_talukas_of_Maharashtra',
        'used_for': 'Maharashtra talukas by district, citing the state government. Mumbai City has no taluka row.',
    },
)

from .maharashtra import (
    DISTRICT_RECORDS as MH_DISTRICT_RECORDS,
    STATE_CODE as MH_STATE_CODE,
    STATE_NAME as MH_STATE_NAME,
    TALUKS_BY_DISTRICT as MH_TALUKS_BY_DISTRICT,
)

STATE_RECORDS = (
    {
        'code': STATE_CODE,
        'name': STATE_NAME,
        'districts': DISTRICT_RECORDS,
        'taluks': TALUKS_BY_DISTRICT,
    },
    {
        'code': MH_STATE_CODE,
        'name': MH_STATE_NAME,
        'districts': MH_DISTRICT_RECORDS,
        'taluks': MH_TALUKS_BY_DISTRICT,
    },
)


def _norm(value):
    return ' '.join(str(value or '').split()).casefold()


def _district_lookup():
    table = {}
    for state in STATE_RECORDS:
        for name, aliases in state['districts']:
            table[_norm(name)] = name
            for alias in aliases:
                table[_norm(alias)] = name
    return table


def _taluk_lookup():
    table = {}
    for state in STATE_RECORDS:
        for district, rows in state['taluks'].items():
            inner = {}
            for name, aliases in rows:
                inner[_norm(name)] = name
                for alias in aliases:
                    inner[_norm(alias)] = name
            table[district] = inner
    return table


def _state_lookup():
    table = {}
    for state in STATE_RECORDS:
        table[_norm(state['name'])] = state['name']
        table[_norm(state['code'])] = state['name']
    table[_norm('karnātaka')] = STATE_NAME
    table[_norm('ಕರ್ನಾಟಕ')] = STATE_NAME
    table[_norm('महाराष्ट्र')] = MH_STATE_NAME
    return table


def _district_state_lookup():
    table = {}
    for state in STATE_RECORDS:
        for name, aliases in state['districts']:
            table[name] = state['name']
            for alias in aliases:
                table[_norm(alias)] = state['name']
    return table


DISTRICT_LOOKUP = _district_lookup()
TALUK_LOOKUP = _taluk_lookup()
STATE_LOOKUP = _state_lookup()
COMBINED_TALUKS = {}
for _state in STATE_RECORDS:
    COMBINED_TALUKS.update(_state['taluks'])
DISTRICT_STATE_LOOKUP = _district_state_lookup()


def district_names():
    return [name for name, _aliases in DISTRICT_RECORDS]


def normalize_state(value):
    return STATE_LOOKUP.get(_norm(value), '')


def state_for_district(value):
    official = normalize_district(value)
    if not official:
        return ''
    return DISTRICT_STATE_LOOKUP.get(official, '')


def normalize_district(value):
    return DISTRICT_LOOKUP.get(_norm(value), '')


def taluk_names(district):
    official = normalize_district(district)
    if not official:
        return []
    return [name for name, _aliases in COMBINED_TALUKS.get(official, ())]


def normalize_taluk(district, value):
    official = normalize_district(district)
    if not official or not _norm(value):
        return ''
    return TALUK_LOOKUP[official].get(_norm(value), '')


def has_coordinates(payload):
    text = str(payload).casefold()
    return 'latitude' in text or 'longitude' in text or 'lat' in text and 'lon' in text


def _district_rows(records, taluks):
    rows = []
    for name, _aliases in records:
        rows.append({
            'name': name,
            'taluks': [taluk for taluk, _taluk_aliases in taluks.get(name, ())],
        })
    return rows


def catalog_payload():
    districts = _district_rows(DISTRICT_RECORDS, TALUKS_BY_DISTRICT)
    states = []
    for state in STATE_RECORDS:
        states.append({
            'code': state['code'],
            'name': state['name'],
            'districts': _district_rows(state['districts'], state['taluks']),
        })
    return {
        'state': {'code': STATE_CODE, 'name': STATE_NAME},
        'districts': districts,
        'states': states,
        'sources': list(SOURCES),
    }


def place_label(locality, taluk, district):
    parts = []
    for item in (locality, taluk, district):
        text = ' '.join(str(item or '').split())
        if text and text not in parts:
            parts.append(text)
    return ', '.join(parts)
