"""One mock payment stays in place when a second worker takes the same request."""

from decimal import Decimal

from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    VisitPayment,
    WorkerProfile,
)


MOCK_ON = override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='mock_demo')


class DailyRequestReassignmentTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician-reassign')
        self.daily_request = DailyServiceRequest(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-reassign@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        self.access_key = 'reassignment-access-key-value'
        self.daily_request.set_access_key(self.access_key)
        self.daily_request.save()
        self.staff = User.objects.create_user(
            username='staff-reassign',
            password='SafePass!234',
            phone_number='9000001301',
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username='customer-reassign',
            password='SafePass!234',
            phone_number='9000001302',
        )
        self.staff_token = Token.objects.create(user=self.staff)
        self.customer_token = Token.objects.create(user=self.customer)
        self.first = self.make_worker('9000001303', 'First', 'Worker')

    def make_worker(self, phone, first_name, last_name):
        user = User.objects.create_user(
            username=f'worker-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=user,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            latitude=Decimal('12.010000'),
            longitude=Decimal('77.000000'),
            service_radius_km=20,
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )
        profile.service_categories.add(self.category)
        ServiceProviderVerification.objects.create(
            user=user,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        return {
            'user': user,
            'profile': profile,
            'token': Token.objects.create(user=user),
        }

    def as_user(self, token):
        if token is None:
            self.client.credentials()
        else:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    @MOCK_ON
    def test_decline_then_rematch_keeps_the_original_payment(self):
        reference = self.daily_request.pk
        self.as_user(None)
        anonymous_match = self.client.post(f'/api/v1/workers/daily-requests/{reference}/match/')
        self.as_user(self.customer_token.key)
        customer_payment = self.client.post(f'/api/v1/workers/daily-requests/{reference}/mock-payment/')
        self.as_user(self.staff_token.key)
        paid = self.client.post(f'/api/v1/workers/daily-requests/{reference}/mock-payment/')
        matched = self.client.post(f'/api/v1/workers/daily-requests/{reference}/match/')
        payment = VisitPayment.objects.get(request=self.daily_request)
        first_offer = ServiceOffer.objects.get(request=self.daily_request, profile=self.first['profile'])

        self.as_user(self.first['token'].key)
        declined = self.client.post(
            f'/api/v1/workers/daily-offers/{first_offer.pk}/respond/',
            {'decision': 'decline'},
            format='json',
        )
        self.daily_request.refresh_from_db()
        payment.refresh_from_db()
        status_after_decline = self.daily_request.status
        payment_state_after_decline = payment.state
        second = self.make_worker('9000001304', 'Second', 'Worker')
        self.as_user(self.staff_token.key)
        repeated_payment = self.client.post(f'/api/v1/workers/daily-requests/{reference}/mock-payment/')
        rematched = self.client.post(f'/api/v1/workers/daily-requests/{reference}/match/')
        second_offer = ServiceOffer.objects.get(request=self.daily_request, profile=second['profile'])
        self.as_user(self.first['token'].key)
        crossed = self.client.post(
            f'/api/v1/workers/daily-offers/{second_offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.as_user(second['token'].key)
        accepted = self.client.post(
            f'/api/v1/workers/daily-offers/{second_offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.as_user(None)
        status = self.client.post(
            '/api/v1/workers/daily-requests/status/',
            {'reference': reference, 'access_key': self.access_key},
            format='json',
        )
        self.daily_request.refresh_from_db()
        payment.refresh_from_db()
        first_offer.refresh_from_db()
        second_offer.refresh_from_db()

        self.assertEqual(anonymous_match.status_code, 401)
        self.assertEqual(customer_payment.status_code, 403)
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data['detail'], 'Inspection fee paid. Workers can be offered now.')
        self.assertEqual(paid.data['money_received'], False)
        self.assertEqual(matched.status_code, 200)
        self.assertEqual(matched.data['offers_created'], 1)
        self.assertEqual(declined.status_code, 200)
        self.assertEqual(declined.data['state'], 'declined')
        self.assertIn(
            status_after_decline,
            {
                DailyServiceRequest.Status.NO_ACCEPTANCE,
                DailyServiceRequest.Status.NO_WORKERS,
            },
        )
        self.assertEqual(payment_state_after_decline, VisitPayment.State.MOCK_RECORDED)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.ASSIGNED)
        self.assertEqual(repeated_payment.status_code, 400)
        self.assertEqual(rematched.status_code, 200)
        self.assertEqual(rematched.data['offers_created'], 1)
        self.assertGreaterEqual(rematched.data['offers_already_present'], 0)
        self.assertEqual(crossed.status_code, 404)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['request_status'], 'assigned')
        self.assertEqual(first_offer.state, ServiceOffer.State.DECLINED)
        self.assertEqual(second_offer.state, ServiceOffer.State.ACCEPTED)
        self.assertEqual(self.daily_request.assigned_profile, second['profile'])
        self.assertEqual(VisitPayment.objects.filter(request=self.daily_request).count(), 1)
        self.assertEqual(payment.pk, VisitPayment.objects.get(request=self.daily_request).pk)
        self.assertEqual(payment.state, VisitPayment.State.MOCK_RECORDED)
        self.assertEqual(payment.verification_source, VisitPayment.Source.MOCK_DEMO)
        self.assertIsNone(payment.verified_at)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.data['status'], 'assigned')
        self.assertEqual(status.data['assigned_profile']['id'], second['profile'].pk)
        self.assertEqual(status.data['assigned_profile']['display_name'], 'Second Worker')
        self.assertNotIn('guest-reassign@example.com', str(status.data))
        self.assertNotIn(self.access_key, str(status.data))
        self.assertIn('payment', status.data)
        self.assertEqual(status.data['payment']['money_received'], False)
        self.assertEqual(status.data['payment']['payment_state'], 'mock_recorded')
