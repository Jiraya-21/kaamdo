"""
Worker profile tests.
Model validation, profile management, permissions, and public visibility.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import (
    ServiceCategory,
    ServiceProviderVerification,
    Skill,
    WorkerProfile,
    service_provider_can_publish,
)


class WorkerProfileModelTests(APITestCase):
    def make_profile(self, **overrides):
        worker = User.objects.create_user(
            username='9000000001',
            password='SafePass!234',
            phone_number='9000000001',
            first_name='Ravi',
            last_name='Kumar',
        )
        values = {
            'user': worker,
            'bio': 'Household plumbing and pipe repair.',
            'service_rate': Decimal('350.00'),
            'pricing_basis': WorkerProfile.PricingBasis.HOURLY,
            'district': 'Mandya',
            'locality': 'Town centre',
        }
        values.update(overrides)
        return WorkerProfile(**values)

    def test_rejects_negative_experience_and_zero_rate(self):
        profile = self.make_profile(experience_years=-1, service_rate=Decimal('0.00'))

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_rejects_radius_outside_the_allowed_range(self):
        profile = self.make_profile(service_radius_km=0)

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_requires_latitude_and_longitude_together(self):
        profile = self.make_profile(latitude=Decimal('12.520000'))

        with self.assertRaises(ValidationError):
            profile.full_clean()


class WorkerProfileApiTests(APITestCase):
    def setUp(self):
        self.worker = self.make_user('9876543210', Capability.SERVICE_PROVIDER, 'Basavaraj', 'Patil')
        self.customer = self.make_user('9123456780', Capability.CUSTOMER, 'Asha', 'Rao')
        self.worker_token = Token.objects.create(user=self.worker)
        self.customer_token = Token.objects.create(user=self.customer)

    def make_user(self, phone, capability, first_name, last_name):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            active_mode=capability,
            first_name=first_name,
            last_name=last_name,
        )
        AccountCapability.objects.create(user=user, code=capability)
        return user

    def approve(self, user):
        ServiceProviderVerification.objects.update_or_create(
            user=user,
            defaults={'status': ServiceProviderVerification.Status.APPROVED},
        )

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def payload(self, **overrides):
        data = {
            'skills': ['Plumbing', 'Pipe fitting'],
            'experience_years': 5,
            'bio': 'Household plumbing and pipe repair.',
            'service_rate': '350.00',
            'pricing_basis': 'hourly',
            'district': 'Mandya',
            'locality': 'Town centre',
            'latitude': '12.521800',
            'longitude': '76.895100',
            'service_radius_km': 20,
            'availability': 'available',
            'publication_status': 'draft',
        }
        data.update(overrides)
        return data

    def test_worker_creates_updates_and_reads_one_profile(self):
        self.authenticate(self.worker_token)
        missing = self.client.get('/api/v1/workers/profile/')
        created = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        duplicate = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        updated = self.client.patch(
            '/api/v1/workers/profile/',
            {'service_rate': '400.00', 'skills': ['Plumbing', 'plumbing']},
            format='json',
        )
        replaced = self.client.put(
            '/api/v1/workers/profile/',
            self.payload(locality='Ashok Nagar', service_rate='450.00'),
            format='json',
        )
        own = self.client.get('/api/v1/workers/profile/')

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['display_name'], 'Basavaraj Patil')
        self.assertEqual(created.data['service_radius_km'], 20)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['service_rate'], '400.00')
        self.assertEqual(updated.data['skills'], ['Plumbing'])
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.data['locality'], 'Ashok Nagar')
        self.assertEqual(replaced.data['service_rate'], '450.00')
        self.assertEqual(Skill.objects.count(), 2)
        self.assertEqual(own.status_code, 200)
        self.assertIsNone(own.data['photo_url'])
        self.assertNotIn('photo', own.data)
        self.assertEqual(WorkerProfile.objects.filter(user=self.worker).count(), 1)

    def test_provider_can_patch_availability_without_other_fields(self):
        self.authenticate(self.worker_token)
        created = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['availability'], 'available')

        updated = self.client.patch(
            '/api/v1/workers/profile/',
            {'availability': 'unavailable'},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['availability'], 'unavailable')
        self.assertEqual(updated.data['bio'], created.data['bio'])

        other = self.make_user('9988001122', Capability.SERVICE_PROVIDER, 'Other', 'Worker')
        other_token = Token.objects.create(user=other)
        self.authenticate(other_token)
        other_patch = self.client.patch(
            '/api/v1/workers/profile/',
            {'availability': 'unavailable'},
            format='json',
        )
        self.assertEqual(other_patch.status_code, 404)
        self.worker.refresh_from_db()
        self.assertEqual(
            WorkerProfile.objects.get(user=self.worker).availability,
            WorkerProfile.Availability.UNAVAILABLE,
        )

        self.authenticate(self.customer_token)
        customer = self.client.patch(
            '/api/v1/workers/profile/',
            {'availability': 'available'},
            format='json',
        )
        self.assertEqual(customer.status_code, 403)

    def test_customer_and_anonymous_users_cannot_manage_a_profile(self):
        anonymous = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        self.authenticate(self.customer_token)
        customer = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(customer.status_code, 403)
        self.assertEqual(WorkerProfile.objects.count(), 0)

    def test_invalid_profile_input_is_rejected(self):
        self.authenticate(self.worker_token)
        response = self.client.post(
            '/api/v1/workers/profile/',
            self.payload(skills=[], service_rate='0.00', latitude='12.500000', longitude=None),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('skills', response.data)
        self.assertEqual(WorkerProfile.objects.count(), 0)

    def test_public_api_shows_only_published_profiles_without_account_secrets(self):
        self.authenticate(self.worker_token)
        blocked = self.client.post(
            '/api/v1/workers/profile/',
            self.payload(publication_status='published'),
            format='json',
        )
        created = self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        self.approve(self.worker)
        published = self.client.patch(
            '/api/v1/workers/profile/',
            {'publication_status': 'published'},
            format='json',
        )
        profile_id = created.data['id']
        other = self.make_user('9988776655', Capability.SERVICE_PROVIDER, 'Hidden', 'Draft')
        draft = WorkerProfile.objects.create(
            user=other,
            bio='Draft electrician profile.',
            service_rate=Decimal('200.00'),
            pricing_basis=WorkerProfile.PricingBasis.DAILY,
            district='Mysuru',
            locality='Hebbal',
            publication_status=WorkerProfile.PublicationStatus.DRAFT,
        )

        self.client.credentials()
        listing = self.client.get('/api/v1/workers/')
        visible = self.client.get(f'/api/v1/workers/{profile_id}/')
        hidden = self.client.get(f'/api/v1/workers/{draft.id}/')

        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(published.status_code, 200)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data['count'], 1)
        public_profile = listing.data['results'][0]
        self.assertEqual(public_profile['display_name'], 'Basavaraj Patil')
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(hidden.status_code, 404)
        for payload in (public_profile, visible.data):
            self.assertIsNone(payload['photo_url'])
            self.assertNotIn('photo', payload)
            self.assertNotIn('latitude', payload)
            self.assertNotIn('longitude', payload)
            self.assertNotIn('phone_number', payload)
            self.assertNotIn('email', payload)
            self.assertNotIn('username', payload)
            self.assertNotIn('password', payload)
            self.assertNotIn('9876543210', str(payload))

    def test_verification_gates_publishing_without_blocking_other_capabilities(self):
        AccountCapability.objects.create(user=self.worker, code=Capability.CUSTOMER)
        self.authenticate(self.worker_token)
        missing_profile = self.client.post('/api/v1/workers/verification/', {}, format='json')
        self.client.post('/api/v1/workers/profile/', self.payload(), format='json')

        submitted = self.client.post(
            '/api/v1/workers/verification/',
            {'applicant_note': 'Please review', 'status': 'approved'},
            format='json',
        )
        duplicate = self.client.post('/api/v1/workers/verification/', {}, format='json')
        still_draft = self.client.patch(
            '/api/v1/workers/profile/',
            {'publication_status': 'published'},
            format='json',
        )
        switched = self.client.patch(
            '/api/v1/auth/mode/',
            {'active_mode': 'customer'},
            format='json',
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        customer = self.client.post('/api/v1/workers/verification/', {}, format='json')

        record = ServiceProviderVerification.objects.get(user=self.worker)
        record.status = ServiceProviderVerification.Status.REJECTED
        record.review_note = 'Add a clearer description.'
        record.save(update_fields=['status', 'review_note'])
        self.authenticate(self.worker_token)
        resubmitted = self.client.post(
            '/api/v1/workers/verification/',
            {'applicant_note': 'Description updated'},
            format='json',
        )

        self.worker.is_active = False
        self.worker.save(update_fields=['is_active'])
        self.approve(self.worker)
        self.worker.refresh_from_db()
        inactive = self.client.patch(
            '/api/v1/workers/profile/',
            {'publication_status': 'published'},
            format='json',
        )

        self.assertEqual(missing_profile.status_code, 400)
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data['status'], 'pending')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(still_draft.status_code, 400)
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.data['active_mode'], 'customer')
        self.assertIn('service_provider', switched.data['capabilities'])
        self.assertEqual(switched.data['service_provider']['verification_status'], 'pending')
        self.assertEqual(customer.status_code, 403)
        self.assertEqual(resubmitted.status_code, 200)
        self.assertEqual(resubmitted.data['status'], 'pending')
        self.assertEqual(resubmitted.data['review_note'], 'Add a clearer description.')
        self.assertFalse(service_provider_can_publish(self.worker))
        self.assertEqual(inactive.status_code, 401)
        self.assertEqual(
            WorkerProfile.objects.get(user=self.worker).publication_status,
            WorkerProfile.PublicationStatus.DRAFT,
        )

    def test_profile_service_categories_are_chosen_slugs_and_are_not_copied_from_skills(self):
        active = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        ServiceCategory.objects.create(name='Retired', slug='retired', is_active=False)
        self.authenticate(self.worker_token)
        created = self.client.post(
            '/api/v1/workers/profile/',
            self.payload(skills=['Wiring'], service_categories=['electrician']),
            format='json',
        )
        unknown = self.client.patch(
            '/api/v1/workers/profile/',
            {'service_categories': ['not-a-category']},
            format='json',
        )
        inactive = self.client.patch(
            '/api/v1/workers/profile/',
            {'service_categories': ['retired']},
            format='json',
        )
        cleared = self.client.patch(
            '/api/v1/workers/profile/',
            {'service_categories': []},
            format='json',
        )
        restored = self.client.patch(
            '/api/v1/workers/profile/',
            {'service_categories': ['Electrician']},
            format='json',
        )
        kept = self.client.patch(
            '/api/v1/workers/profile/',
            {'bio': 'Updated household work.'},
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['service_categories'], ['electrician'])
        self.assertEqual(created.data['skills'], ['Wiring'])
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(inactive.status_code, 400)
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.data['service_categories'], [])
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.data['service_categories'], ['electrician'])
        self.assertEqual(kept.status_code, 200)
        self.assertEqual(kept.data['bio'], 'Updated household work.')
        self.assertEqual(kept.data['service_categories'], ['electrician'])
        self.assertEqual(active.worker_profiles.count(), 1)

    def test_a_provider_cannot_read_or_approve_another_verification(self):
        other = self.make_user('9000000991', Capability.SERVICE_PROVIDER, 'Other', 'Provider')
        other_token = Token.objects.create(user=other)
        self.authenticate(self.worker_token)
        self.client.post('/api/v1/workers/profile/', self.payload(), format='json')
        submitted = self.client.post(
            '/api/v1/workers/verification/',
            {'applicant_note': 'Please review my tools.', 'status': 'approved'},
            format='json',
        )
        own = self.client.get('/api/v1/workers/verification/')
        self.authenticate(other_token)
        other_view = self.client.get('/api/v1/workers/verification/')
        other_submit = self.client.post(
            '/api/v1/workers/verification/',
            {'applicant_note': 'Approve the other person.', 'status': 'approved'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        customer = self.client.get('/api/v1/workers/verification/')

        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data['status'], 'pending')
        self.assertEqual(own.data['applicant_note'], 'Please review my tools.')
        self.assertEqual(other_view.status_code, 200)
        self.assertEqual(other_view.data['status'], 'not_submitted')
        self.assertNotIn('Please review my tools.', str(other_view.data))
        self.assertEqual(other_submit.status_code, 400)
        self.assertEqual(customer.status_code, 403)
        record = ServiceProviderVerification.objects.get(user=self.worker)
        self.assertEqual(record.status, ServiceProviderVerification.Status.PENDING)
