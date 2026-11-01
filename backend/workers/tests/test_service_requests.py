"""Service request creation uses the published profile and a verified phone."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, OtpPurpose, PhoneVerification, User
from workers.models import ServiceProviderVerification, ServiceRequest, WorkerProfile


class ServiceRequestApiTests(APITestCase):
    def setUp(self):
        self.worker = self.make_user('9000000101', Capability.SERVICE_PROVIDER)
        self.customer = self.make_user('9000000102', Capability.CUSTOMER)
        self.other = self.make_user('9000000103', Capability.CUSTOMER)
        self.worker_token = Token.objects.create(user=self.worker)
        self.customer_token = Token.objects.create(user=self.customer)
        self.other_token = Token.objects.create(user=self.other)
        ServiceProviderVerification.objects.create(
            user=self.worker,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        self.profile = WorkerProfile.objects.create(
            user=self.worker,
            bio='Household plumbing.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )

    def make_user(self, phone, capability):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            active_mode=capability,
        )
        AccountCapability.objects.create(user=user, code=capability)
        return user

    def verify(self, user):
        PhoneVerification.objects.create(
            user=user,
            phone_number=user.phone_number,
            purpose=OtpPurpose.SERVICE_REQUEST,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_customer_request_requires_verification_and_stays_private(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        blocked = self.client.post(
            '/api/v1/workers/requests/',
            {'profile': self.profile.id, 'description': 'Kitchen tap is leaking.'},
            format='json',
        )
        self.verify(self.customer)
        forced_status = self.client.post(
            '/api/v1/workers/requests/',
            {'profile': self.profile.id, 'description': 'Kitchen tap is leaking.', 'status': 'accepted'},
            format='json',
        )
        created = self.client.post(
            '/api/v1/workers/requests/',
            {'profile': self.profile.id, 'description': 'Kitchen tap is leaking.', 'contact_phone': '9999999999'},
            format='json',
        )
        own = self.client.get('/api/v1/workers/requests/')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        hidden = self.client.get('/api/v1/workers/requests/')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        incoming = self.client.get('/api/v1/workers/requests/incoming/')

        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(forced_status.status_code, 400)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['status'], 'requested')
        self.assertEqual(created.data['contact_phone'], self.customer.phone_number)
        self.assertNotIn('proposed_fee', created.data)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data['count'], 1)
        self.assertEqual(hidden.data['count'], 0)
        self.assertEqual(incoming.data['count'], 1)
        self.assertEqual(ServiceRequest.objects.count(), 1)

    def test_anonymous_request_is_rejected(self):
        response = self.client.post(
            '/api/v1/workers/requests/',
            {'profile': self.profile.id, 'description': 'Need help.'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(ServiceRequest.objects.count(), 0)

    def test_only_the_provider_can_accept_decline_or_close(self):
        self.verify(self.customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        created = self.client.post(
            '/api/v1/workers/requests/',
            {'profile': self.profile.id, 'description': 'Kitchen tap is leaking.'},
            format='json',
        )
        customer_decision = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        self.client.credentials()
        anonymous = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        outsider = self.make_user('9000000104', Capability.SERVICE_PROVIDER)
        outsider_token = Token.objects.create(user=outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')
        hidden = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'declined'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        accepted = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        repeated = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'declined'},
            format='json',
        )
        closed = self.client.patch(
            f"/api/v1/workers/requests/{created.data['id']}/",
            {'status': 'closed'},
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(customer_decision.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['status'], 'accepted')
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.data['status'], 'closed')
        self.assertEqual(ServiceRequest.objects.get(pk=created.data['id']).status, ServiceRequest.Status.CLOSED)
        self.assertNotIn('9000000104', str(hidden.data))
