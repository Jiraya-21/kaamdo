"""Development-only mock visit payment. A mock record is not money received."""

from decimal import Decimal

from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    VisitFeeConfiguration,
    VisitPayment,
    get_active_visit_fee,
)

MOCK_ON = override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='mock_demo')


class MockVisitPaymentTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.daily_request = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-mock-pay@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        self.staff = User.objects.create_user(
            username='staff-mock-pay',
            password='SafePass!234',
            phone_number='9000000901',
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username='customer-mock-pay',
            password='SafePass!234',
            phone_number='9000000902',
        )
        self.staff_token = Token.objects.create(user=self.staff)
        self.customer_token = Token.objects.create(user=self.customer)

    def post(self, token=None, pk=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        else:
            self.client.credentials()
        target = self.daily_request.pk if pk is None else pk
        return self.client.post(f'/api/v1/workers/daily-requests/{target}/mock-payment/')

    def test_safeguards_refuse_without_creating_a_payment(self):
        anonymous = self.post()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        customer = self.client.post(f'/api/v1/workers/daily-requests/{self.daily_request.pk}/mock-payment/')
        with override_settings(DEBUG=False, KAAMDO_VISIT_PAYMENT='mock_demo'):
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token.key}')
            debug_off = self.client.post(f'/api/v1/workers/daily-requests/{self.daily_request.pk}/mock-payment/')
        with override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='unconfigured'):
            setting_off = self.client.post(f'/api/v1/workers/daily-requests/{self.daily_request.pk}/mock-payment/')
        self.daily_request.refresh_from_db()
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(customer.status_code, 403)
        self.assertEqual(debug_off.status_code, 400)
        self.assertEqual(setting_off.status_code, 400)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertEqual(VisitPayment.objects.count(), 0)

        with override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='unconfigured'):
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token.key}')
            flagged = self.client.post(
                f'/api/v1/workers/daily-requests/{self.daily_request.pk}/mock-payment/',
                {'test_mode': True, 'enabled': True, 'money_received': True},
                format='json',
            )
        self.assertEqual(flagged.status_code, 400)
        self.assertEqual(VisitPayment.objects.count(), 0)

    @override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='test_bypass')
    def test_test_bypass_alias_records_a_mock_and_not_a_gateway_payment(self):
        response = self.post(self.staff_token.key)
        payment = VisitPayment.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['money_received'], False)
        self.assertEqual(payment.state, VisitPayment.State.MOCK_RECORDED)
        self.assertEqual(payment.verification_source, VisitPayment.Source.MOCK_DEMO)
        self.assertNotEqual(payment.state, VisitPayment.State.GATEWAY_VERIFIED)
        self.assertIsNone(payment.verified_at)

    @MOCK_ON
    def test_mock_progress_copies_the_active_fee_and_does_not_receive_money(self):
        fee = get_active_visit_fee()
        fee.amount_inr = Decimal('125.00')
        fee.save(update_fields=['amount_inr'])
        response = self.post(self.staff_token.key)
        repeated = self.post(self.staff_token.key)
        self.daily_request.refresh_from_db()
        payment = VisitPayment.objects.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'TEST MODE — Payment skipped; no money collected.')
        self.assertEqual(response.data['test_mode'], True)
        self.assertEqual(response.data['money_received'], False)
        self.assertEqual(response.data['status'], 'dispatch_pending')
        self.assertEqual(response.data['payment_state'], 'mock_recorded')
        self.assertEqual(response.data['verification_source'], 'mock_demo')
        self.assertEqual(response.data['amount_inr'], '125.00')
        self.assertNotIn('guest-mock-pay@example.com', str(response.data))
        self.assertNotIn('gateway_verified', str(response.data))
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DISPATCH_PENDING)
        self.assertIsNone(self.daily_request.assigned_profile_id)
        self.assertEqual(payment.amount_inr, Decimal('125.00'))
        self.assertEqual(payment.state, VisitPayment.State.MOCK_RECORDED)
        self.assertEqual(payment.verification_source, VisitPayment.Source.MOCK_DEMO)
        self.assertIsNone(payment.verified_at)
        self.assertNotEqual(payment.state, VisitPayment.State.GATEWAY_VERIFIED)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data['status'], 'dispatch_pending')
        self.assertEqual(VisitPayment.objects.count(), 1)

    @MOCK_ON
    def test_missing_fee_and_later_or_inconsistent_states_change_nothing(self):
        VisitFeeConfiguration.objects.filter(is_active=True).update(is_active=False)
        missing_fee = self.post(self.staff_token.key)
        self.daily_request.refresh_from_db()
        self.assertEqual(missing_fee.status_code, 400)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertEqual(VisitPayment.objects.count(), 0)

        fee = VisitFeeConfiguration.objects.create(
            amount_inr=Decimal('99.00'),
            currency='INR',
            is_active=True,
        )
        self.daily_request.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.daily_request.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        self.daily_request.transition_to(DailyServiceRequest.Status.OFFERING)
        later = self.post(self.staff_token.key)
        self.daily_request.refresh_from_db()
        self.assertEqual(later.status_code, 400)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.OFFERING)
        self.assertEqual(VisitPayment.objects.count(), 0)
        self.assertEqual(fee.amount_inr, Decimal('99.00'))

        ready = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-mock-ready@example.com',
            description='The switch is loose.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
            status=DailyServiceRequest.Status.DISPATCH_PENDING,
        )
        inconsistent = self.post(self.staff_token.key, pk=ready.pk)
        ready.refresh_from_db()
        self.assertEqual(inconsistent.status_code, 400)
        self.assertEqual(ready.status, DailyServiceRequest.Status.DISPATCH_PENDING)
        self.assertFalse(VisitPayment.objects.filter(request=ready).exists())
