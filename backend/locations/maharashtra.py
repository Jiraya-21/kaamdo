"""
Official Maharashtra administrative names used by KaamDo forms.

Districts: 36 districts listed by the Government of Maharashtra and compiled at
https://en.wikipedia.org/wiki/List_of_districts_of_Maharashtra
(retrieved 2 November 2026). Ahmednagar, Aurangabad, and Osmanabad are stored
under those Wikipedia/Census names; newer government spellings are aliases.

Talukas: https://en.wikipedia.org/wiki/List_of_talukas_of_Maharashtra
(retrieved 2 November 2026), citing the Maharashtra government website.
Mumbai City has no taluka in that table; the taluk list is empty rather than
invented. Villages, streets, and PIN codes are not catalogued here.
"""

STATE_NAME = 'Maharashtra'
STATE_CODE = 'MH'

SOURCES = (
    'https://en.wikipedia.org/wiki/List_of_districts_of_Maharashtra',
    'https://en.wikipedia.org/wiki/List_of_talukas_of_Maharashtra',
)

DISTRICT_RECORDS = (
    ('Ahmednagar', ('Ahilyanagar', 'Ahmadnagar')),
    ('Akola', ()),
    ('Amravati', ('Amrawati',)),
    ('Aurangabad', ('Chhatrapati Sambhajinagar', 'Sambhajinagar')),
    ('Beed', ('Bid',)),
    ('Bhandara', ()),
    ('Buldhana', ('Buldana',)),
    ('Chandrapur', ()),
    ('Dhule', ()),
    ('Gadchiroli', ()),
    ('Gondia', ('Gondiya',)),
    ('Hingoli', ()),
    ('Jalgaon', ()),
    ('Jalna', ()),
    ('Kolhapur', ()),
    ('Latur', ()),
    ('Mumbai City', ('Mumbai', 'Bombay')),
    ('Mumbai Suburban', ('Bombay Suburban',)),
    ('Nagpur', ()),
    ('Nanded', ()),
    ('Nandurbar', ()),
    ('Nashik', ('Nasik',)),
    ('Osmanabad', ('Dharashiv',)),
    ('Palghar', ()),
    ('Parbhani', ()),
    ('Pune', ('Poona',)),
    ('Raigad', ('Raigarh', 'Kolaba')),
    ('Ratnagiri', ()),
    ('Sangli', ()),
    ('Satara', ()),
    ('Sindhudurg', ()),
    ('Solapur', ('Sholapur',)),
    ('Thane', ()),
    ('Wardha', ()),
    ('Washim', ()),
    ('Yavatmal', ('Yeotmal',)),
)


def _t(*names):
    return tuple((name, ()) for name in names)


TALUKS_BY_DISTRICT = {
    'Ahmednagar': _t(
        'Nagar', 'Shevgaon', 'Pathardi', 'Parner', 'Sangamner', 'Kopargaon',
        'Akole', 'Shrirampur', 'Nevasa', 'Rahata', 'Rahuri', 'Shrigonda',
        'Karjat', 'Jamkhed',
    ),
    'Akola': _t('Akola', 'Akot', 'Telhara', 'Balapur', 'Patur', 'Murtajapur', 'Barshitakli'),
    'Amravati': _t(
        'Amravati', 'Bhatkuli', 'Nandgaon Khandeshwar', 'Dharni', 'Chikhaldara',
        'Achalpur', 'Chandurbazar', 'Morshi', 'Warud', 'Daryapur',
        'Anjangaon-Surji', 'Chandur', 'Dhamangaon', 'Tiosa',
    ),
    'Aurangabad': _t(
        'Aurangabad', 'Kannad', 'Soegaon', 'Sillod', 'Phulambri', 'Khuldabad',
        'Vaijapur', 'Gangapur', 'Paithan',
    ),
    'Beed': _t(
        'Beed', 'Georai', 'Patoda', 'Shirur-Kasar', 'Ashti', 'Majalgaon',
        'Wadwani', 'Kaij', 'Dharur', 'Parli', 'Ambajogai',
    ),
    'Bhandara': _t('Bhandara', 'Tumsar', 'Pauni', 'Mohadi', 'Sakoli', 'Lakhani', 'Lakhandur'),
    'Buldhana': _t(
        'Buldhana', 'Chikhli', 'Deulgaon Raja', 'Jalgaon Jamod', 'Sangrampur',
        'Malkapur', 'Motala', 'Nandura', 'Khamgaon', 'Shegaon', 'Mehkar',
        'Sindkhed Raja', 'Lonar',
    ),
    'Chandrapur': _t(
        'Chandrapur', 'Saoli', 'Mul', 'Ballarpur', 'Pombhurna', 'Gondpimpri',
        'Warora', 'Chimur', 'Bhadravati', 'Bramhapuri', 'Nagbhid', 'Sindewahi',
        'Rajura', 'Korpana', 'Jiwati',
    ),
    'Dhule': _t('Dhule', 'Sakri', 'Sindkheda', 'Shirpur'),
    'Gadchiroli': _t(
        'Gadchiroli', 'Dhanora', 'Chamorshi', 'Mulchera', 'Desaiganj', 'Armori',
        'Kurkheda', 'Korchi', 'Aheri', 'Etapalli', 'Bhamragad', 'Sironcha',
    ),
    'Gondia': _t(
        'Gondia', 'Goregaon', 'Salekasa', 'Tiroda', 'Amgaon', 'Deori',
        'Arjuni-Morgaon', 'Sadak-Arjuni',
    ),
    'Hingoli': _t('Hingoli', 'Sengaon', 'Kalamnuri', 'Basmath', 'Aundha Nagnath'),
    'Jalgaon': _t(
        'Jalgaon', 'Jamner', 'Erandol', 'Dharangaon', 'Bhusawal', 'Raver',
        'Muktainagar', 'Bodwad', 'Yawal', 'Amalner', 'Parola', 'Chopda',
        'Pachora', 'Bhadgaon', 'Chalisgaon',
    ),
    'Jalna': _t(
        'Jalna', 'Bhokardan', 'Jafrabad', 'Badnapur', 'Ambad', 'Ghansawangi',
        'Partur', 'Mantha',
    ),
    'Kolhapur': _t(
        'Karvir', 'Panhala', 'Shahuwadi', 'Kagal', 'Hatkanangale', 'Shirol',
        'Radhanagari', 'Gaganbawada', 'Bhudargad', 'Gadhinglaj', 'Chandgad', 'Ajra',
    ),
    'Latur': _t(
        'Latur', 'Renapur', 'Ausa', 'Ahmedpur', 'Jalkot', 'Chakur',
        'Shirur Anantpal', 'Nilanga', 'Deoni', 'Udgir',
    ),
    'Mumbai City': (),
    'Mumbai Suburban': _t('Kurla', 'Andheri', 'Borivali'),
    'Nagpur': _t(
        'Nagpur Urban', 'Nagpur Rural', 'Kamptee', 'Hingna', 'Katol', 'Narkhed',
        'Savner', 'Kalameshwar', 'Ramtek', 'Mouda', 'Parseoni', 'Umred', 'Kuhi',
        'Bhiwapur',
    ),
    'Nanded': _t(
        'Nanded', 'Ardhapur', 'Mudkhed', 'Bhokar', 'Umri', 'Loha', 'Kandhar',
        'Kinwat', 'Himayatnagar', 'Hadgaon', 'Mahur', 'Deglur', 'Mukhed',
        'Dharmabad', 'Biloli', 'Naigaon',
    ),
    'Nandurbar': _t('Nandurbar', 'Navapur', 'Shahada', 'Talode', 'Akkalkuwa', 'Dhadgaon'),
    'Nashik': _t(
        'Nashik', 'Igatpuri', 'Dindori', 'Peth', 'Trimbakeshwar', 'Kalwan',
        'Deola', 'Surgana', 'Baglan', 'Malegaon', 'Nandgaon', 'Chandwad',
        'Niphad', 'Sinnar', 'Yeola',
    ),
    'Osmanabad': _t(
        'Osmanabad', 'Tuljapur', 'Bhum', 'Paranda', 'Washi', 'Kalamb', 'Lohara', 'Umarga',
    ),
    'Palghar': _t(
        'Palghar', 'Vasai', 'Dahanu', 'Talasari', 'Jawhar', 'Mokhada', 'Vada', 'Vikramgad',
    ),
    'Parbhani': _t(
        'Parbhani', 'Sonpeth', 'Gangakhed', 'Palam', 'Purna', 'Sailu', 'Jintur',
        'Manwath', 'Pathri',
    ),
    'Pune': _t(
        'Pune City', 'Haveli', 'Khed', 'Junnar', 'Ambegaon', 'Maval', 'Mulshi',
        'Shirur', 'Purandhar (Saswad)', 'Velhe', 'Bhor', 'Baramati', 'Indapur', 'Daund',
    ),
    'Raigad': _t(
        'Pen', 'Alibag', 'Murud', 'Panvel', 'Uran', 'Karjat', 'Khalapur',
        'Mangaon', 'Tala', 'Roha', 'Sudhagad-Pali', 'Mahad', 'Poladpur',
        'Shrivardhan', 'Mhasala',
    ),
    'Ratnagiri': _t(
        'Ratnagiri', 'Sangameshwar', 'Lanja', 'Rajapur', 'Chiplun', 'Guhagar',
        'Dapoli', 'Mandangad', 'Khed',
    ),
    'Sangli': _t(
        'Miraj', 'Kavathemahankal', 'Tasgaon', 'Jat', 'Walwa', 'Shirala',
        'Khanapur (Vita)', 'Atpadi', 'Palus', 'Kadegaon',
    ),
    'Satara': _t(
        'Satara', 'Jaoli', 'Koregaon', 'Wai', 'Mahabaleshwar', 'Khandala',
        'Phaltan', 'Maan', 'Khatav', 'Patan', 'Karad',
    ),
    'Sindhudurg': _t(
        'Kankavli', 'Vaibhavwadi', 'Devgad', 'Malwan', 'Sawantwadi', 'Kudal',
        'Vengurla', 'Dodamarg',
    ),
    'Solapur': _t(
        'Barshi', 'Solapur North', 'Solapur South', 'Akkalkot', 'Madha', 'Karmala',
        'Pandharpur', 'Mohol', 'Malshiras', 'Sangole', 'Mangalvedhe',
    ),
    'Thane': _t('Thane', 'Kalyan', 'Murbad', 'Shahapur', 'Bhiwandi', 'Ulhasnagar', 'Ambarnath'),
    'Wardha': _t('Wardha', 'Deoli', 'Seloo', 'Arvi', 'Ashti', 'Karanja', 'Hinganghat', 'Samudrapur'),
    'Washim': _t('Washim', 'Malegaon', 'Risod', 'Mangrulpir', 'Karanja', 'Manora'),
    'Yavatmal': _t(
        'Yavatmal', 'Arni', 'Babhulgaon', 'Kalamb', 'Darwha', 'Digras', 'Ner',
        'Pusad', 'Umarkhed', 'Mahagaon', 'Kelapur', 'Ralegaon', 'Ghatanji',
        'Wani', 'Maregaon', 'Zari Jamani',
    ),
}
