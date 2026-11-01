"""IP OTP limits. These tests do not send SMS or contact SMSMobileAPI."""

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import Throttled
from rest_framework.test import APITestCase

from accounts.models import PhoneOtpChallenge, User
from accounts.otp_ip import OTP_IP_WAIT, client_ip, enforce_otp_ip_limit


class FakeRequest:
    def __init__(self, **meta):
        self.META = meta


class ClientIpTests(SimpleTestCase):
    def test_spoofed_forwarded_for_is_ignored_without_a_trusted_proxy(self):
        ip_address = client_ip({
            'REMOTE_ADDR': '203.0.113.10',
            'HTTP_X_FORWARDED_FOR': '198.51.100.1, 203.0.113.10',
        })
        self.assertEqual(ip_address, '203.0.113.10')

    @override_settings(OTP_TRUSTED_PROXIES=['10.0.0.1'])
    def test_trusted_proxy_uses_the_rightmost_untrusted_forwarded_ip(self):
        ip_address = client_ip({
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_FORWARDED_FOR': '198.51.100.1, 203.0.113.20',
        })
        self.assertEqual(ip_address, '203.0.113.20')

    @override_settings(OTP_TRUSTED_PROXIES=['10.0.0.1'])
    def test_direct_client_cannot_spoof_as_a_trusted_proxy(self):
        ip_address = client_ip({
            'REMOTE_ADDR': '198.51.100.8',
            'HTTP_X_FORWARDED_FOR': '203.0.113.1',
        })
        self.assertEqual(ip_address, '198.51.100.8')


@override_settings(
    DEBUG=False,
    OTP_DELIVERY='unconfigured',
    SMSMOBILEAPI_API_KEY='',
    OTP_IP_SEND_LIMIT=2,
    OTP_IP_VERIFY_LIMIT=2,
    OTP_IP_WINDOW_MINUTES=15,
)
class OtpIpLimitTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = User.objects.create_user(
            username='otp-ip-user',
            password='SafePass!234',
            phone_number='9876500001',
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def send(self, purpose='account', **extra):
        return self.client.post(
            '/api/v1/auth/otp/send/',
            {'purpose': purpose},
            format='json',
            **extra,
        )

    def verify(self, code='000000', purpose='account', **extra):
        return self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': purpose, 'code': code},
            format='json',
            **extra,
        )

    def test_third_send_from_the_same_ip_is_429(self):
        first = self.send()
        second = self.send()
        third = self.send()
        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.data['detail'], OTP_IP_WAIT)
        self.assertNotIn('9876500001', str(third.data))
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    def test_a_new_ip_is_counted_separately(self):
        self.send()
        self.send()
        blocked = self.send()
        other = self.send(REMOTE_ADDR='203.0.113.40')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(other.status_code, 400)

    def test_spoofed_forwarded_for_does_not_reset_the_limit(self):
        self.send()
        self.send()
        spoofed = self.send(HTTP_X_FORWARDED_FOR='198.51.100.9')
        self.assertEqual(spoofed.status_code, 429)

    @override_settings(OTP_TRUSTED_PROXIES=['10.0.0.1'])
    def test_trusted_proxy_counts_the_forwarded_client(self):
        extra = {'REMOTE_ADDR': '10.0.0.1', 'HTTP_X_FORWARDED_FOR': '198.51.100.2'}
        self.send(**extra)
        self.send(**extra)
        blocked = self.send(**extra)
        other = self.send(REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR='198.51.100.3')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(other.status_code, 400)

    def test_changing_account_or_purpose_does_not_bypass_the_ip_limit(self):
        other = User.objects.create_user(
            username='otp-ip-other',
            password='SafePass!234',
            phone_number='9876500002',
        )
        other_token = Token.objects.create(user=other)
        self.send()
        self.send(purpose='service_request')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        blocked = self.send(purpose='job_application')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.data['detail'], OTP_IP_WAIT)

    def test_anonymous_requests_still_count_toward_the_ip_limit(self):
        self.client.credentials()
        first = self.send()
        second = self.send()
        third = self.send()
        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 401)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.data['detail'], OTP_IP_WAIT)

    def test_verify_ip_limit_does_not_name_an_account(self):
        first = self.verify()
        second = self.verify()
        third = self.verify()
        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.data['detail'], OTP_IP_WAIT)
        self.assertNotIn('9876500001', str(third.data))
        self.assertNotIn(self.user.username, str(third.data))


@override_settings(OTP_IP_SEND_LIMIT=2, OTP_IP_VERIFY_LIMIT=2, OTP_IP_WINDOW_MINUTES=15)
class GuestOtpIpLimitTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def send(self, email='guest@example.com', purpose='service_request', **extra):
        return self.client.post(
            '/api/v1/auth/otp/guest/send/',
            {'email': email, 'purpose': purpose},
            format='json',
            **extra,
        )

    def verify(self, email='guest@example.com', purpose='service_request', **extra):
        return self.client.post(
            '/api/v1/auth/otp/guest/verify/',
            {'email': email, 'purpose': purpose, 'code': '000000'},
            format='json',
            **extra,
        )

    def test_changing_email_does_not_bypass_the_send_limit(self):
        first = self.send()
        second = self.send(email='other@example.com', purpose='job_application')
        third = self.send(email='third@example.com')
        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.data['detail'], OTP_IP_WAIT)
        self.assertNotIn('guest@example.com', str(third.data))

    def test_guest_verify_is_limited_per_ip(self):
        first = self.verify()
        second = self.verify(email='other@example.com')
        third = self.verify()
        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.data['detail'], OTP_IP_WAIT)


class OtpIpCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(OTP_IP_SEND_LIMIT=1, OTP_IP_WINDOW_MINUTES=15)
    def test_enforce_counts_the_connecting_ip_only(self):
        first = FakeRequest(REMOTE_ADDR='203.0.113.7')
        second = FakeRequest(REMOTE_ADDR='203.0.113.7')
        other = FakeRequest(REMOTE_ADDR='203.0.113.8')
        enforce_otp_ip_limit(first, 'send')
        with self.assertRaises(Throttled) as caught:
            enforce_otp_ip_limit(second, 'send')
        enforce_otp_ip_limit(other, 'send')
        self.assertEqual(caught.exception.detail, OTP_IP_WAIT)
        self.assertEqual(caught.exception.status_code, 429)
