"""A guest checks one daily-service request with the access key from creation."""

from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, GuestEmailVerification, OtpPurpose, User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    Skill,
    WorkerProfile,
)


class GuestDailyRequestStatusTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.email = 'asha-status@example.com'
        self.verify(self.email)
        self.created = self.create_request(self.email)

    def verify(self, email):
        GuestEmailVerification.objects.create(
            email=email,
            purpose=OtpPurpose.SERVICE_REQUEST,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def create_request(self, email):
        response = self.client.post(
            '/api/v1/workers/daily-requests/',
            {
                'guest_name': 'Asha Rao',
                'contact_email': email,
                'category': self.category.id,
                'description': 'The ceiling fan does not start.',
                'latitude': '12.521800',
                'longitude': '76.895100',
                'radius_km': 15,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        return response

    def status(self, reference, access_key):
        body = {}
        if reference is not None:
            body['reference'] = reference
        if access_key is not None:
            body['access_key'] = access_key
        return self.client.post('/api/v1/workers/daily-requests/status/', body, format='json')

    def test_guest_can_read_status_with_the_creation_key(self):
        response = self.status(self.created.data['reference'], self.created.data['access_key'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['reference'], self.created.data['reference'])
        self.assertEqual(response.data['status'], 'draft')
        self.assertEqual(response.data['radius_km'], 15)
        self.assertEqual(response.data['can_expand'], False)
        self.assertNotIn('assigned_profile', response.data)
        self.assertNotIn(self.email, str(response.data))
        self.assertNotIn('assigned_profile', response.data)
        self.assertNotIn('access_key', response.data)

    def test_missing_wrong_and_unknown_credentials_look_the_same(self):
        reference = self.created.data['reference']
        missing = self.status(reference, None)
        wrong = self.status(reference, 'not-the-real-access-key-value')
        unknown = self.status(999999, self.created.data['access_key'])
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.data, {'detail': 'Daily service request not found.'})
        self.assertEqual(missing.data, wrong.data)
        self.assertEqual(wrong.data, unknown.data)
        self.assertNotIn(self.email, str(missing.data))
        self.assertNotIn('draft', str(missing.data))

    def test_another_requests_key_cannot_read_this_request(self):
        self.verify('other-status@example.com')
        other = self.create_request('other-status@example.com')
        crossed = self.status(self.created.data['reference'], other.data['access_key'])
        self.assertEqual(crossed.status_code, 404)
        self.assertEqual(crossed.data, {'detail': 'Daily service request not found.'})
        self.assertNotIn(self.email, str(crossed.data))

    @override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='mock_demo')
    def test_assigned_worker_card_appears_only_after_acceptance(self):
        before = self.status(self.created.data['reference'], self.created.data['access_key'])
        worker = User.objects.create_user(
            username='worker-status-card',
            password='SafePass!234',
            phone_number='9000001101',
            first_name='Ravi',
            last_name='Kumar',
        )
        AccountCapability.objects.create(user=worker, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=worker,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            latitude=Decimal('12.521800'),
            longitude=Decimal('76.895100'),
            service_radius_km=20,
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )
        profile.service_categories.add(self.category)
        profile.skills.add(Skill.objects.create(name='Wiring'))
        ServiceProviderVerification.objects.create(
            user=worker,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        staff = User.objects.create_user(
            username='staff-status-card',
            password='SafePass!234',
            phone_number='9000001102',
            is_staff=True,
        )
        staff_token = Token.objects.create(user=staff)
        worker_token = Token.objects.create(user=worker)
        reference = self.created.data['reference']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')
        paid = self.client.post(f'/api/v1/workers/daily-requests/{reference}/mock-payment/')
        matched = self.client.post(f'/api/v1/workers/daily-requests/{reference}/match/')
        offer = ServiceOffer.objects.get(request_id=reference, profile=profile)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {worker_token.key}')
        accepted = self.client.post(
            f'/api/v1/workers/daily-offers/{offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.client.credentials()
        after = self.status(reference, self.created.data['access_key'])

        self.assertEqual(before.status_code, 200)
        self.assertNotIn('assigned_profile', before.data)
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(matched.status_code, 200)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(after.status_code, 200)
        self.assertEqual(after.data['status'], 'assigned')
        self.assertEqual(
            after.data['assigned_profile'],
            {
                'id': profile.pk,
                'display_name': 'Ravi Kumar',
                'skills': ['Wiring'],
                'district': 'Mandya',
                'locality': 'Town centre',
            },
        )
        self.assertNotIn('9000001101', str(after.data))
        self.assertNotIn(self.email, str(after.data))
        self.assertNotIn('latitude', after.data['assigned_profile'])

    def test_inconsistent_assignment_does_not_reveal_a_worker(self):
        worker = User.objects.create_user(
            username='worker-inconsistent',
            password='SafePass!234',
            phone_number='9000001103',
            first_name='Hidden',
            last_name='Worker',
        )
        profile = WorkerProfile.objects.create(
            user=worker,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
        )
        record = DailyServiceRequest.objects.get(pk=self.created.data['reference'])
        record.assigned_profile = profile
        record.save(update_fields=['assigned_profile'])
        early = self.status(record.pk, self.created.data['access_key'])
        self.assertEqual(early.status_code, 200)
        self.assertEqual(early.data['status'], 'draft')
        self.assertNotIn('assigned_profile', early.data)
        self.assertNotIn('Hidden', str(early.data))

        orphan = DailyServiceRequest(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='orphan-status@example.com',
            description='The switch is loose.',
            latitude=Decimal('12.521800'),
            longitude=Decimal('76.895100'),
            radius_km=15,
            status=DailyServiceRequest.Status.ASSIGNED,
        )
        orphan.set_access_key('orphan-access-key-value-long')
        orphan.save()
        hidden = self.status(orphan.pk, 'orphan-access-key-value-long')
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.data['status'], 'assigned')
        self.assertNotIn('assigned_profile', hidden.data)
        self.assertNotIn('orphan-status@example.com', str(hidden.data))
