"""Guest daily-service booking. No worker dispatch and no payment."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import GuestEmailVerification, GuestPhoneVerification, OtpPurpose, User
from workers.models import DailyServiceRequest, ServiceCategory, ServiceRequest, VisitPayment


class GuestDailyRequestApiTests(APITestCase):
    def setUp(self):
        self.active = ServiceCategory.objects.create(
            name='Electrician',
            slug='electrician',
            description='Home electrical repairs.',
            is_active=True,
        )
        self.hidden = ServiceCategory.objects.create(
            name='Old service',
            slug='old-service',
            is_active=False,
        )
        self.email = 'asha@example.com'

    def verify(self, email=None, purpose=OtpPurpose.SERVICE_REQUEST, hours=1):
        GuestEmailVerification.objects.create(
            email=email or self.email,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(hours=hours),
        )

    def payload(self, **overrides):
        values = {
            'guest_name': 'Asha Rao',
            'contact_email': self.email,
            'category': self.active.id,
            'description': 'The ceiling fan does not start.',
            'latitude': '12.521800',
            'longitude': '76.895100',
            'radius_km': 15,
        }
        values.update(overrides)
        return values

    def test_active_categories_are_public_and_inactive_categories_are_hidden(self):
        response = self.client.get('/api/v1/workers/categories/')
        slugs = [row['slug'] for row in response.data['results']]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(slugs, ['electrician'])
        self.assertNotIn('is_active', response.data['results'][0])

    def test_verified_guest_can_create_a_request_without_an_account(self):
        self.verify()
        users_before = User.objects.count()
        response = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        record = DailyServiceRequest.objects.get()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            set(response.data),
            {'detail', 'reference', 'status', 'radius_km', 'access_key', 'payment', 'next_step'},
        )
        self.assertIn('inspection fee', response.data['detail'].lower())
        self.assertEqual(response.data['reference'], record.pk)
        self.assertEqual(response.data['status'], 'awaiting_payment')
        self.assertEqual(response.data['next_step'], 'pay_inspection_fee')
        self.assertEqual(response.data['radius_km'], 15)
        self.assertNotIn(self.email, str(response.data))
        self.assertNotIn('access_key_hash', response.data)
        self.assertNotEqual(response.data['access_key'], record.access_key_hash)
        self.assertIn('$', record.access_key_hash)
        self.assertTrue(record.check_access_key(response.data['access_key']))
        self.assertIsNone(record.customer_id)
        self.assertEqual(record.contact_email, self.email)
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(ServiceRequest.objects.count(), 0)
        self.assertEqual(VisitPayment.objects.count(), 1)
        self.assertEqual(VisitPayment.objects.get().state, VisitPayment.State.PENDING)
        hidden = self.client.get(f'/api/v1/workers/daily-requests/{record.pk}/')
        listed = self.client.get('/api/v1/workers/daily-requests/')
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(listed.status_code, 405)

    def test_missing_expired_and_other_email_verification_are_rejected(self):
        missing = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        self.verify(hours=-1)
        expired = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        self.verify(email='other@example.com')
        other = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(expired.status_code, 400)
        self.assertEqual(other.status_code, 400)
        self.assertEqual(DailyServiceRequest.objects.count(), 0)

    def test_invalid_category_fields_coordinates_and_radius_are_rejected(self):
        self.verify()
        cases = [
            self.payload(category=self.hidden.id),
            self.payload(category=99999),
            self.payload(guest_name=' '),
            self.payload(description=' '),
            self.payload(latitude='95'),
            self.payload(longitude='200'),
            self.payload(latitude='not-a-number'),
            self.payload(radius_km=4),
            self.payload(radius_km=101),
        ]
        for body in cases:
            response = self.client.post('/api/v1/workers/daily-requests/', body, format='json')
            self.assertEqual(response.status_code, 400, body)
        missing_name = self.payload()
        missing_name.pop('guest_name')
        missing = self.client.post('/api/v1/workers/daily-requests/', missing_name, format='json')
        self.assertEqual(missing.status_code, 400)
        omitted = self.client.post(
            '/api/v1/workers/daily-requests/',
            self.payload(radius_km=None),
            format='json',
        )
        self.assertEqual(omitted.status_code, 400)
        defaulted = self.payload()
        defaulted.pop('radius_km')
        created = self.client.post('/api/v1/workers/daily-requests/', defaulted, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['radius_km'], 60)
        self.assertEqual(DailyServiceRequest.objects.get().latitude, Decimal('12.521800'))

    def test_verified_guest_can_create_a_request_with_mobile_instead_of_email(self):
        phone = '9876543210'
        GuestPhoneVerification.objects.create(
            phone_number=phone,
            purpose=OtpPurpose.SERVICE_REQUEST,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        body = self.payload()
        body.pop('contact_email')
        body['contact_phone'] = phone
        users_before = User.objects.count()
        response = self.client.post('/api/v1/workers/daily-requests/', body, format='json')
        record = DailyServiceRequest.objects.get()

        self.assertEqual(response.status_code, 201)
        self.assertNotIn(phone, str(response.data))
        self.assertNotIn('contact_phone', response.data)
        self.assertEqual(record.contact_email, '')
        self.assertEqual(record.contact_phone, phone)
        self.assertIsNone(record.customer_id)
        self.assertEqual(User.objects.count(), users_before)

    def test_guest_verification_cannot_create_a_second_request(self):
        self.verify()
        first = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        second = self.client.post('/api/v1/workers/daily-requests/', self.payload(), format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(DailyServiceRequest.objects.count(), 1)
        self.assertFalse(GuestEmailVerification.objects.filter(email=self.email).exists())

    def test_unverified_mobile_and_email_together_are_rejected(self):
        missing_phone = self.client.post(
            '/api/v1/workers/daily-requests/',
            self.payload(contact_email='', contact_phone='9876543210'),
            format='json',
        )
        both = self.client.post(
            '/api/v1/workers/daily-requests/',
            self.payload(contact_phone='9876543210'),
            format='json',
        )
        self.assertEqual(missing_phone.status_code, 400)
        self.assertEqual(both.status_code, 400)
        self.assertEqual(DailyServiceRequest.objects.count(), 0)

    def test_phone_gps_precision_is_rounded_instead_of_rejected(self):
        self.verify()
        response = self.client.post(
            '/api/v1/workers/daily-requests/',
            self.payload(
                latitude='12.971891887766543',
                longitude='77.59456634567891',
            ),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        record = DailyServiceRequest.objects.get()
        self.assertEqual(record.latitude, Decimal('12.971892'))
        self.assertEqual(record.longitude, Decimal('77.594566'))
        self.assertNotIn('digits in total', str(response.data).lower())
