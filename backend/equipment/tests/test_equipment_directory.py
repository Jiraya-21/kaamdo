"""Public equipment filters run before pagination. Owners read drafts from /mine/."""

from decimal import Decimal

from django.conf import settings
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from equipment.models import EquipmentListing, FeeStatus, ListingStatus


class PublicEquipmentFilterTests(APITestCase):
    def make_user(self, phone, capabilities):
        user = User.objects.create_user(
            username=f'equip-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name='Owner',
            last_name='One',
        )
        for code in capabilities:
            AccountCapability.objects.create(user=user, code=code)
        return user, Token.objects.create(user=user)

    def make_listing(self, owner, **overrides):
        values = {
            'owner': owner,
            'title': 'Small tractor',
            'description': 'Field work near town.',
            'district': 'Mandya',
            'locality': 'Town centre',
            'pricing_basis': 'hourly',
            'rate': Decimal('500.00'),
            'operator_included': True,
            'status': ListingStatus.PUBLISHED,
            'fee_status': FeeStatus.PAID,
        }
        values.update(overrides)
        return EquipmentListing.objects.create(**values)

    def test_filters_cover_advertisements_beyond_the_first_page(self):
        owner, _token = self.make_user('9000000841', [Capability.EQUIPMENT_OWNER])
        older = self.make_listing(owner, title='Older tractor')
        newer = self.make_listing(
            owner,
            title='Harvester',
            description='Cuts paddy.',
            district='Mysuru',
            locality='Hebbal',
            pricing_basis='daily',
            operator_included=False,
        )
        hidden = self.make_listing(
            owner,
            title='Hidden tiller',
            status=ListingStatus.DRAFT,
            fee_status=FeeStatus.UNPAID,
        )

        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'PAGE_SIZE': 1}):
            unfiltered = self.client.get('/api/v1/equipment/')
            by_price = self.client.get('/api/v1/equipment/?pricing_basis=hourly')
            by_district = self.client.get('/api/v1/equipment/?district=mysuru')
            by_text = self.client.get('/api/v1/equipment/?q=paddy')
            by_operator = self.client.get('/api/v1/equipment/?operator_included=false')
            rejected = self.client.get('/api/v1/equipment/?pricing_basis=weekly')

        self.assertEqual(unfiltered.status_code, 200)
        self.assertEqual(unfiltered.data['count'], 2)
        self.assertEqual(by_price.data['count'], 1)
        self.assertEqual(by_price.data['results'][0]['id'], older.id)
        self.assertEqual(by_district.data['results'][0]['id'], newer.id)
        self.assertEqual(by_text.data['results'][0]['id'], newer.id)
        self.assertEqual(by_operator.data['results'][0]['id'], newer.id)
        self.assertEqual(rejected.status_code, 400)
        self.assertNotIn(hidden.id, [row['id'] for row in by_price.data['results']])
        self.assertNotIn('phone_number', by_price.data['results'][0])
        self.assertNotIn(owner.phone_number, str(by_price.data))

    def test_owner_drafts_stay_off_the_public_list_and_on_mine(self):
        owner, owner_token = self.make_user('9000000842', [Capability.EQUIPMENT_OWNER])
        other, other_token = self.make_user('9000000843', [Capability.EQUIPMENT_OWNER])
        renter, renter_token = self.make_user('9000000844', [Capability.EQUIPMENT_RENTER])
        draft = self.make_listing(
            owner,
            title='Own draft',
            status=ListingStatus.DRAFT,
            fee_status=FeeStatus.UNPAID,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {owner_token.key}')
        public = self.client.get(f'/api/v1/equipment/?owner={other.id}')
        mine = self.client.get(f'/api/v1/equipment/mine/?owner={other.id}')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        other_mine = self.client.get('/api/v1/equipment/mine/')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {renter_token.key}')
        denied = self.client.get('/api/v1/equipment/mine/')
        self.client.credentials()
        anonymous = self.client.get('/api/v1/equipment/mine/')

        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data['count'], 0)
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(mine.data['results'][0]['id'], draft.id)
        self.assertEqual(mine.data['results'][0]['title'], 'Own draft')
        self.assertEqual(other_mine.data['count'], 0)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)
        self.assertNotIn(owner.phone_number, str(mine.data))
