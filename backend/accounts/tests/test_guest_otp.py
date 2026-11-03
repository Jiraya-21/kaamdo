"""Development-only guest email OTP. No account or booking is created."""

from datetime import timedelta

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from unittest.mock import patch

from accounts.models import (
    GuestEmailOtpChallenge,
    GuestEmailVerification,
    GuestPhoneVerification,
    PhoneOtpChallenge,
    User,
    guest_email_is_verified,
    guest_phone_is_verified,
    reset_guest_phone_table_cache,
)
from accounts.smsmobileapi import REFUSED, SmsDeliveryError


LOCAL_OTP = override_settings(DEBUG=True, OTP_DELIVERY='development')


class GuestEmailOtpTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def send(self, email='guest@example.com', purpose='service_request'):
        return self.client.post(
            '/api/v1/auth/otp/guest/send/',
            {'email': email, 'purpose': purpose},
            format='json',
        )

    def verify(self, code, email='guest@example.com', purpose='service_request'):
        return self.client.post(
            '/api/v1/auth/otp/guest/verify/',
            {'email': email, 'purpose': purpose, 'code': code},
            format='json',
        )

    @LOCAL_OTP
    def test_development_code_verifies_once_and_creates_no_account(self):
        sent = self.send()
        self.assertFalse(guest_email_is_verified('guest@example.com', 'service_request'))
        wrong = self.verify('000000')
        verified = self.verify(sent.data['dev_code'])
        reused = self.verify(sent.data['dev_code'])

        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['delivery'], 'development')
        self.assertNotIn(sent.data['dev_code'], sent.data['detail'])
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(guest_email_is_verified('guest@example.com', 'service_request'))
        self.assertEqual(reused.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(GuestEmailVerification.objects.count(), 1)
        stored = GuestEmailOtpChallenge.objects.get()
        self.assertNotIn(sent.data['dev_code'], stored.code_hash)
        self.assertTrue(stored.consumed)

    @LOCAL_OTP
    def test_expired_code_and_attempt_limit_fail(self):
        sent = self.send()
        challenge = GuestEmailOtpChallenge.objects.get()
        challenge.expires_at = timezone.now() - timedelta(minutes=1)
        challenge.save(update_fields=['expires_at'])
        expired = self.verify(sent.data['dev_code'])
        self.assertEqual(expired.status_code, 400)
        self.assertEqual(GuestEmailVerification.objects.count(), 0)

        challenge.expires_at = timezone.now() + timedelta(minutes=5)
        challenge.save(update_fields=['expires_at'])
        for _ in range(5):
            self.verify('111111')
        blocked = self.verify(sent.data['dev_code'])
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(GuestEmailVerification.objects.count(), 0)

    @LOCAL_OTP
    def test_resend_limit_and_contact_binding(self):
        first = self.send()
        self.send()
        self.send()
        limited = self.send()
        other = self.send(email='other@example.com')
        crossed = self.verify(first.data['dev_code'], email='other@example.com')

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(other.status_code, 200)
        self.assertEqual(crossed.status_code, 400)
        self.assertFalse(guest_email_is_verified('other@example.com', 'service_request'))

    @LOCAL_OTP
    def test_other_purposes_are_refused(self):
        response = self.send(purpose='account')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(GuestEmailOtpChallenge.objects.count(), 0)

    @override_settings(DEBUG=False, OTP_DELIVERY='development')
    def test_debug_off_hides_the_code_even_when_development_delivery_is_set(self):
        response = self.send()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('dev_code', response.data)
        self.assertIn('not configured', response.data['detail'].lower())
        self.assertEqual(GuestEmailOtpChallenge.objects.count(), 0)

    @override_settings(DEBUG=True, OTP_DELIVERY='unconfigured')
    def test_debug_alone_does_not_disclose_a_code(self):
        response = self.send()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('dev_code', response.data)
        self.assertEqual(GuestEmailOtpChallenge.objects.count(), 0)


class GuestPhoneOtpTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        reset_guest_phone_table_cache()
        self.phone = '9876543210'

    def send(self, phone=None, purpose='service_request'):
        return self.client.post(
            '/api/v1/auth/otp/guest/send/',
            {'phone_number': phone or self.phone, 'purpose': purpose},
            format='json',
        )

    def verify(self, code, phone=None, purpose='service_request'):
        return self.client.post(
            '/api/v1/auth/otp/guest/verify/',
            {'phone_number': phone or self.phone, 'purpose': purpose, 'code': code},
            format='json',
        )

    @LOCAL_OTP
    def test_development_mobile_code_verifies_once_and_creates_no_account(self):
        sent = self.send()
        self.assertFalse(guest_phone_is_verified(self.phone, 'service_request'))
        wrong = self.verify('000000')
        verified = self.verify(sent.data['dev_code'])
        reused = self.verify(sent.data['dev_code'])

        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['delivery'], 'development')
        self.assertNotIn(sent.data['dev_code'], sent.data['detail'])
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(guest_phone_is_verified(self.phone, 'service_request'))
        self.assertEqual(reused.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(GuestPhoneVerification.objects.count(), 1)
        stored = PhoneOtpChallenge.objects.get()
        self.assertIsNone(stored.user_id)
        self.assertNotIn(sent.data['dev_code'], stored.code_hash)
        self.assertTrue(stored.consumed)

    @LOCAL_OTP
    def test_email_and_mobile_together_are_refused(self):
        response = self.client.post(
            '/api/v1/auth/otp/guest/send/',
            {
                'email': 'guest@example.com',
                'phone_number': self.phone,
                'purpose': 'service_request',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)
        self.assertEqual(GuestEmailOtpChallenge.objects.count(), 0)

    @LOCAL_OTP
    def test_other_purposes_are_refused(self):
        response = self.send(purpose='account')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    @override_settings(DEBUG=True, OTP_DELIVERY='unconfigured')
    def test_unconfigured_delivery_does_not_issue_a_mobile_code(self):
        response = self.send()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('dev_code', response.data)
        self.assertIn('not configured', response.data['detail'].lower())
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    @LOCAL_OTP
    def test_verify_uses_cache_when_guest_phone_table_is_missing(self):
        sent = self.send()
        with (
            patch('accounts.otp.guest_phone_table_ready', return_value=False),
            patch('accounts.models.guest_phone_table_ready', return_value=False),
        ):
            verified = self.verify(sent.data['dev_code'])
            self.assertEqual(verified.status_code, 200)
            self.assertTrue(guest_phone_is_verified(self.phone, 'service_request'))
        self.assertEqual(GuestPhoneVerification.objects.count(), 0)

    @override_settings(
        DEBUG=False,
        OTP_DELIVERY='smsmobileapi',
        SMSMOBILEAPI_API_KEY='test-sms-key',
        SMSMOBILEAPI_TIMEOUT_SECONDS=10,
    )
    def test_sms_mode_sends_a_guest_mobile_code_without_dev_code(self):
        with patch('accounts.otp.send_smsmobileapi_message') as sender:
            response = self.send()
        sender.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['delivery'], 'sms')
        self.assertIn('OTP sent to your mobile', response.data['detail'])
        self.assertNotIn('dev_code', response.data)
        self.assertEqual(PhoneOtpChallenge.objects.filter(user__isnull=True).count(), 1)
        self.assertEqual(User.objects.count(), 0)

    @override_settings(
        DEBUG=False,
        OTP_DELIVERY='smsmobileapi',
        SMSMOBILEAPI_API_KEY='test-sms-key',
        SMSMOBILEAPI_TIMEOUT_SECONDS=10,
    )
    def test_provider_refusal_consumes_the_guest_challenge(self):
        with patch(
            'accounts.otp.send_smsmobileapi_message',
            side_effect=SmsDeliveryError(REFUSED),
        ) as sender:
            response = self.send()
        sender.assert_called_once()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], REFUSED)
        self.assertEqual(PhoneOtpChallenge.objects.filter(consumed=False).count(), 0)
        self.assertEqual(User.objects.count(), 0)


class GuestOtpOptionsTests(APITestCase):
    def options(self):
        return self.client.get('/api/v1/auth/otp/guest/options/')

    def assert_no_secrets(self, response):
        text = str(response.data).lower()
        self.assertNotIn('api_key', text)
        self.assertNotIn('smsmobileapi', text)
        self.assertNotIn('dev_code', text)

    def test_unconfigured_offers_no_guest_methods(self):
        with override_settings(DEBUG=True, OTP_DELIVERY='unconfigured', SMSMOBILEAPI_API_KEY=''):
            response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], {'available': False, 'mode': 'unavailable'})
        self.assertEqual(response.data['phone'], {'available': False, 'mode': 'unavailable'})
        self.assert_no_secrets(response)

    def test_development_offers_email_and_phone_practice(self):
        with override_settings(DEBUG=True, OTP_DELIVERY='development', SMSMOBILEAPI_API_KEY=''):
            response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], {'available': True, 'mode': 'development'})
        self.assertEqual(response.data['phone'], {'available': True, 'mode': 'development'})
        self.assert_no_secrets(response)

    @override_settings(DEBUG=False, OTP_DELIVERY='development', KAAMDO_STAGING_DEMO=False)
    def test_development_without_debug_is_unavailable(self):
        response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['email']['available'])
        self.assertFalse(response.data['phone']['available'])

    @override_settings(DEBUG=False, OTP_DELIVERY='development', KAAMDO_STAGING_DEMO=True)
    def test_staging_demo_offers_development_phone(self):
        response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['phone'], {'available': True, 'mode': 'development'})
        self.assertEqual(response.data['email'], {'available': True, 'mode': 'development'})
        self.assert_no_secrets(response)

    @override_settings(
        DEBUG=False,
        OTP_DELIVERY='smsmobileapi',
        SMSMOBILEAPI_API_KEY='test-sms-key',
    )
    def test_sms_with_a_key_offers_mobile_only(self):
        response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['phone'], {'available': True, 'mode': 'sms'})
        self.assertEqual(response.data['email'], {'available': False, 'mode': 'unavailable'})
        self.assert_no_secrets(response)

    @override_settings(DEBUG=False, OTP_DELIVERY='smsmobileapi', SMSMOBILEAPI_API_KEY='')
    def test_sms_without_a_key_offers_no_mobile(self):
        response = self.options()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['phone']['available'])
        self.assertEqual(response.data['phone']['mode'], 'unavailable')
        self.assert_no_secrets(response)
