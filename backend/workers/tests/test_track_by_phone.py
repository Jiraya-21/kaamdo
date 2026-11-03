"""Guest tracking by verified mobile number — no request id or secret code needed."""

from decimal import Decimal

from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import GuestPhoneVerification, OtpPurpose
from django.utils import timezone
from datetime import timedelta

from workers.models import DailyServiceRequest, ServiceCategory


@override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='mock_demo', OTP_DELIVERY='development')
class TrackByPhoneTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.phone = '9876543210'
        self.other = '9123456789'
        self.first = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_phone=self.phone,
            description='Fan repair',
            latitude=Decimal('17.910000'),
            longitude=Decimal('77.520000'),
            radius_km=15,
            status=DailyServiceRequest.Status.AWAITING_PAYMENT,
        )
        self.second = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_phone=self.phone,
            description='Switch board',
            latitude=Decimal('17.910000'),
            longitude=Decimal('77.520000'),
            radius_km=20,
            status=DailyServiceRequest.Status.OFFERING,
        )
        DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Other',
            contact_phone=self.other,
            description='Other work',
            latitude=Decimal('17.910000'),
            longitude=Decimal('77.520000'),
            radius_km=15,
            status=DailyServiceRequest.Status.DRAFT,
        )

    def mark_verified(self, phone):
        GuestPhoneVerification.objects.create(
            phone_number=phone,
            purpose=OtpPurpose.SERVICE_REQUEST,
            expires_at=timezone.now() + timedelta(hours=12),
        )

    def test_by_phone_requires_verification(self):
        blocked = self.client.post(
            '/api/v1/workers/daily-requests/by-phone/',
            {'phone_number': self.phone},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('phone_number', blocked.data)

    def test_by_phone_lists_all_requests_for_verified_number(self):
        self.mark_verified(self.phone)
        response = self.client.post(
            '/api/v1/workers/daily-requests/by-phone/',
            {'phone_number': self.phone},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        refs = [row['reference'] for row in response.data['requests']]
        self.assertEqual(refs, [self.second.pk, self.first.pk])
        self.assertNotIn(self.other, str(response.data))
        for row in response.data['requests']:
            self.assertIn('status', row)
            self.assertIn('payment', row)
            self.assertNotIn('access_key', row)
            self.assertNotIn('contact_phone', row)

    def test_status_and_cancel_work_with_verified_phone(self):
        self.mark_verified(self.phone)
        status = self.client.post(
            '/api/v1/workers/daily-requests/status/',
            {'reference': self.first.pk, 'phone_number': self.phone},
            format='json',
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.data['reference'], self.first.pk)
        self.assertEqual(status.data['status'], 'awaiting_payment')

        cancelled = self.client.post(
            '/api/v1/workers/daily-requests/cancel/',
            {'reference': self.first.pk, 'phone_number': self.phone},
            format='json',
        )
        self.assertEqual(cancelled.status_code, 200)
        self.first.refresh_from_db()
        self.assertEqual(self.first.status, DailyServiceRequest.Status.CANCELLED)
