"""Public worker directory filters run before pagination."""

from decimal import Decimal

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import ServiceCategory, Skill, WorkerProfile


class WorkerDirectoryFilterTests(APITestCase):
    def make_profile(self, phone, first_name, last_name, **overrides):
        user = User.objects.create_user(
            username=f'worker-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        values = {
            'user': user,
            'bio': 'Published household work.',
            'service_rate': Decimal('150.00'),
            'pricing_basis': WorkerProfile.PricingBasis.HOURLY,
            'district': 'Mandya',
            'locality': 'Town centre',
            'latitude': Decimal('12.000000'),
            'longitude': Decimal('77.000000'),
            'publication_status': WorkerProfile.PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return WorkerProfile.objects.create(**values)

    def test_skill_category_and_district_filters_cover_workers_beyond_the_first_page(self):
        electrician = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        plumber = ServiceCategory.objects.create(name='Plumber', slug='plumber')
        wiring = Skill.objects.create(name='Wiring')
        pipes = Skill.objects.create(name='Pipes')
        older = self.make_profile('9000000701', 'Older', 'Electrician')
        older.skills.add(wiring)
        older.service_categories.add(electrician)
        newer = self.make_profile(
            '9000000702',
            'Newer',
            'Plumber',
            district='Mysuru',
            locality='Hebbal',
        )
        newer.skills.add(pipes)
        newer.service_categories.add(plumber)
        hidden = self.make_profile(
            '9000000703',
            'Hidden',
            'Draft',
            publication_status=WorkerProfile.PublicationStatus.DRAFT,
        )
        hidden.skills.add(wiring)

        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'PAGE_SIZE': 1}):
            unfiltered = self.client.get('/api/v1/workers/')
            by_skill = self.client.get('/api/v1/workers/?skill=wiring')
            by_category = self.client.get('/api/v1/workers/?category=electrician')
            by_district = self.client.get('/api/v1/workers/?district=mysuru')
            by_name = self.client.get('/api/v1/workers/?q=Older')

        self.assertEqual(unfiltered.data['count'], 2)
        self.assertEqual(by_skill.data['count'], 1)
        self.assertEqual(by_skill.data['results'][0]['id'], older.id)
        self.assertEqual(by_category.data['results'][0]['id'], older.id)
        self.assertEqual(by_district.data['results'][0]['id'], newer.id)
        self.assertEqual(by_name.data['results'][0]['id'], older.id)
        self.assertNotIn('phone_number', by_skill.data['results'][0])
        self.assertNotIn('9000000701', str(by_skill.data))
        self.assertNotIn(hidden.id, [row['id'] for row in by_skill.data['results']])

    def test_radius_uses_straight_line_distance_and_skips_unusable_coordinates(self):
        near = self.make_profile(
            '9000000711',
            'Near',
            'Worker',
            latitude=Decimal('12.010000'),
            longitude=Decimal('77.000000'),
        )
        far = self.make_profile(
            '9000000712',
            'Far',
            'Worker',
            latitude=Decimal('12.500000'),
            longitude=Decimal('77.000000'),
        )
        missing = self.make_profile(
            '9000000713',
            'Missing',
            'Worker',
            latitude=None,
            longitude=None,
        )
        found = self.client.get('/api/v1/workers/?latitude=12&longitude=77&radius_km=10')
        ids = [row['id'] for row in found.data['results']]
        self.assertEqual(found.status_code, 200)
        self.assertEqual(ids, [near.id])
        self.assertNotIn(far.id, ids)
        self.assertNotIn(missing.id, ids)
        self.assertEqual(found.data['count'], 1)

    def test_invalid_radius_input_is_rejected(self):
        partial = self.client.get('/api/v1/workers/?latitude=12')
        bad_coordinate = self.client.get('/api/v1/workers/?latitude=95&longitude=77&radius_km=10')
        bad_radius = self.client.get('/api/v1/workers/?latitude=12&longitude=77&radius_km=0')
        self.assertEqual(partial.status_code, 400)
        self.assertEqual(bad_coordinate.status_code, 400)
        self.assertEqual(bad_radius.status_code, 400)


class ProviderAndJobSeekerSeparationTests(APITestCase):
    def make_user(self, phone, first_name, *capabilities):
        user = User.objects.create_user(
            username=f'role-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name=first_name,
            last_name='Role',
        )
        for code in capabilities:
            AccountCapability.objects.create(user=user, code=code)
        return user

    def make_profile(self, user, **overrides):
        values = {
            'user': user,
            'bio': 'Profile used only to test which list can see it.',
            'service_rate': Decimal('100.00'),
            'pricing_basis': WorkerProfile.PricingBasis.HOURLY,
            'district': 'Hassan',
            'locality': 'Centre',
            'publication_status': WorkerProfile.PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return WorkerProfile.objects.create(**values)

    def test_public_directory_is_daily_service_providers_only(self):
        provider = self.make_user('9000000801', 'Provider', Capability.SERVICE_PROVIDER)
        seeker = self.make_user('9000000802', 'Seeker', Capability.JOB_SEEKER)
        both = self.make_user(
            '9000000803',
            'Both',
            Capability.SERVICE_PROVIDER,
            Capability.JOB_SEEKER,
        )
        inactive = self.make_user('9000000804', 'Inactive', Capability.SERVICE_PROVIDER)
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])
        provider_profile = self.make_profile(provider)
        seeker_profile = self.make_profile(seeker)
        both_profile = self.make_profile(both)
        inactive_profile = self.make_profile(inactive)

        listing = self.client.get('/api/v1/workers/')
        ids = [row['id'] for row in listing.data['results']]

        self.assertEqual(listing.status_code, 200)
        self.assertCountEqual(ids, [both_profile.id, provider_profile.id])
        self.assertNotIn(seeker_profile.id, ids)
        self.assertNotIn(inactive_profile.id, ids)
        hidden = self.client.get(f'/api/v1/workers/{seeker_profile.id}/')
        visible = self.client.get(f'/api/v1/workers/{provider_profile.id}/')
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(visible.status_code, 200)
        self.assertNotIn('applicant_note', visible.data)
        self.assertNotIn('review_note', visible.data)
        self.assertNotIn('phone_number', visible.data)

    def test_job_seeker_cannot_open_provider_verification(self):
        seeker = self.make_user('9000000811', 'Seeker', Capability.JOB_SEEKER)
        token = self.client.post(
            '/api/v1/auth/login/',
            {'phone_number': '9000000811', 'password': 'SafePass!234'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.data["token"]}')
        response = self.client.get('/api/v1/workers/verification/')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('applicant_note', response.data)
