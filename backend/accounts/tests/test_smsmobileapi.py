"""SMSMobileAPI adapter tests. Network calls are mocked. No live SMS is sent."""

import json
import re
import urllib.error
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import PhoneOtpChallenge, PhoneVerification, User
from accounts.otp import (
    MAX_ATTEMPTS,
    MAX_SENDS,
    SMS_ACCEPTED_DETAIL,
    development_otp_enabled,
    sms_otp_enabled,
)
from accounts.smsmobileapi import (
    NOT_CONFIGURED,
    REFUSED,
    SEND_URL,
    TIMEOUT,
    UNREACHABLE,
    UNUSABLE,
    SmsDeliveryError,
    india_msisdn,
    parse_sendsms_body,
    post_sendsms,
    send_message,
)

FAKE_KEY = 'test-smsmobileapi-key-not-real'
ACCEPTED = json.dumps({
    'result': {
        'error': 0,
        'sent': '1',
        'id': 'provider-message-id',
        'note': 'sent by mobile',
    }
}).encode('utf-8')


class FakeHttpResponse:
    def __init__(self, body, status=200, headers=None):
        self._body = body
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def accepted_post(fields, timeout):
    if fields.get('apikey') != FAKE_KEY:
        raise AssertionError('unexpected key handling')
    if not str(fields.get('recipients', '')).startswith('+91'):
        raise AssertionError('recipients must use international format')
    if 'KaamDo code:' not in str(fields.get('message', '')):
        raise AssertionError('message must carry the server-generated code')
    return 200, ACCEPTED


class SmsMobileApiAdapterTests(SimpleTestCase):
    def test_india_msisdn_uses_plus_ninety_one(self):
        self.assertEqual(india_msisdn('9876543210'), '+919876543210')
        self.assertEqual(india_msisdn('+91 98765 43210'), '+919876543210')

    def test_missing_key_does_not_open_the_network(self):
        with patch('accounts.smsmobileapi.post_sendsms') as poster:
            with self.assertRaises(SmsDeliveryError) as caught:
                send_message('9876543210', 'KaamDo code: 123456.', api_key='')
        poster.assert_not_called()
        self.assertEqual(caught.exception.user_message, NOT_CONFIGURED)

    def test_provider_acceptance_is_not_verification(self):
        result = send_message(
            '9876543210',
            'KaamDo code: 123456.',
            api_key=FAKE_KEY,
            post=accepted_post,
        )
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], 'provider-message-id')
        self.assertNotIn('123456', json.dumps(result))

    def test_malformed_json_is_refused(self):
        with self.assertRaises(SmsDeliveryError) as caught:
            parse_sendsms_body(b'<html>nope</html>')
        self.assertEqual(caught.exception.user_message, UNUSABLE)

    def test_provider_error_flag_is_refused(self):
        with self.assertRaises(SmsDeliveryError) as caught:
            parse_sendsms_body(json.dumps({'result': {'error': 1, 'message': 'fail'}}).encode())
        self.assertEqual(caught.exception.user_message, REFUSED)

    def test_plain_text_ok_is_accepted(self):
        result = parse_sendsms_body(b'OK', http_status=200)
        self.assertTrue(result['accepted'])

    def test_empty_2xx_body_is_accepted(self):
        result = parse_sendsms_body(b'', http_status=200)
        self.assertTrue(result['accepted'])

    def test_sanitize_hides_key_phone_and_otp(self):
        from accounts.smsmobileapi import sanitize_response_text
        sample = sanitize_response_text(
            f'apikey={FAKE_KEY}&recipients=+919876543210 code 123456',
            api_key=FAKE_KEY,
        )
        self.assertNotIn(FAKE_KEY, sample)
        self.assertNotIn('9876543210', sample)
        self.assertNotIn('123456', sample)

    def test_error_zero_is_accepted_even_when_sent_is_zero(self):
        result = parse_sendsms_body(json.dumps({
            'result': {'error': 0, 'sent': '0', 'id': 'queued-id'},
        }).encode())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], 'queued-id')

    def test_missing_provider_id_is_still_acceptance(self):
        result = parse_sendsms_body(json.dumps({'result': {'error': 0}}).encode())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], '')

    def test_flat_success_body_is_accepted(self):
        result = parse_sendsms_body(json.dumps({
            'error': 0,
            'sent': '1',
            'id': 'flat-provider-id',
        }).encode())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], 'flat-provider-id')

    def test_sms_ok_envelope_is_accepted(self):
        """Live SMSMobileAPI success body used by the provider test UI."""
        body = {
            'sms': {
                'ok': True,
                'channel': 'SMS',
                'message': (
                    'SMS sent successfully. Verify that the mobile app is running '
                    'on the connected phone.'
                ),
                'details': {
                    'error': 0,
                    'sent': '1',
                    'id': 'test-provider-message-id',
                    'note': 'sent by mobile',
                    'datetime': '2026-01-01T00:00:00Z',
                    'trial_account': {
                        'status': '1',
                        'max_allowed': 60,
                        'sms_sent': 0,
                    },
                },
            }
        }
        result = parse_sendsms_body(json.dumps(body).encode())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], 'test-provider-message-id')

    def test_sms_ok_envelope_does_not_require_trial_sms_sent(self):
        body = {
            'sms': {
                'ok': True,
                'details': {
                    'error': 0,
                    'sent': '1',
                    'id': 'trial-zero-count-id',
                    'trial_account': {'status': '1', 'sms_sent': 0},
                },
            }
        }
        result = parse_sendsms_body(json.dumps(body).encode())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['provider_id'], 'trial-zero-count-id')

    def test_sms_ok_false_is_refused(self):
        body = {
            'sms': {
                'ok': False,
                'message': 'failed',
                'details': {'error': 1, 'sent': '0', 'id': ''},
            }
        }
        with self.assertRaises(SmsDeliveryError) as caught:
            parse_sendsms_body(json.dumps(body).encode())
        self.assertEqual(caught.exception.user_message, REFUSED)

    def test_sms_details_error_nonzero_is_refused(self):
        body = {
            'sms': {
                'ok': True,
                'details': {'error': 2, 'sent': '0', 'id': 'ignored'},
            }
        }
        with self.assertRaises(SmsDeliveryError) as caught:
            parse_sendsms_body(json.dumps(body).encode())
        self.assertEqual(caught.exception.user_message, REFUSED)

    def test_adapter_has_no_delivery_status_url(self):
        from accounts import smsmobileapi
        self.assertEqual(smsmobileapi.SEND_URL, 'https://api.smsmobileapi.com/sendsms/')
        self.assertFalse(hasattr(smsmobileapi, 'STATUS_URL'))
        self.assertNotIn('log/sent/sms', Path(smsmobileapi.__file__).read_text(encoding='utf-8'))

    def test_post_uses_https_form_body_not_query_string(self):
        captured = {}

        def fake_urlopen(request, timeout=None, context=None):
            captured['url'] = request.full_url
            captured['method'] = request.get_method()
            captured['body'] = request.data.decode('utf-8')
            captured['timeout'] = timeout
            self.assertIsNotNone(context)
            return FakeHttpResponse(ACCEPTED)

        with patch('accounts.smsmobileapi._urlopen', side_effect=fake_urlopen):
            status, raw, content_type = post_sendsms(
                {
                    'apikey': FAKE_KEY,
                    'recipients': '+919876543210',
                    'message': 'KaamDo code: 123456.',
                    'sendsms': '1',
                },
                8,
            )
        self.assertEqual(status, 200)
        self.assertEqual(raw, ACCEPTED)
        self.assertEqual(content_type, '')

        self.assertEqual(SEND_URL, 'https://api.smsmobileapi.com/sendsms/')
        self.assertEqual(captured['url'], SEND_URL)
        self.assertEqual(captured['method'], 'POST')
        self.assertEqual(captured['timeout'], 8.0)
        self.assertNotIn('apikey', captured['url'])
        self.assertIn('apikey=', captured['body'])
        self.assertIn(FAKE_KEY, captured['body'])
        self.assertIn('recipients=%2B919876543210', captured['body'])

    def test_invalid_credentials_are_safe(self):
        error = urllib.error.HTTPError(
            SEND_URL,
            401,
            'Unauthorized',
            hdrs={},
            fp=BytesIO(b'{"result":{"error":1}}'),
        )

        def fake_urlopen(request, timeout=None, context=None):
            raise error

        with patch('accounts.smsmobileapi._urlopen', side_effect=fake_urlopen):
            with self.assertRaises(SmsDeliveryError) as caught:
                post_sendsms({'apikey': FAKE_KEY, 'recipients': '+919876543210', 'message': 'x'}, 10)
        self.assertEqual(caught.exception.user_message, REFUSED)
        self.assertNotIn(FAKE_KEY, str(caught.exception.user_message))

    def test_timeout_is_safe(self):
        with patch('accounts.smsmobileapi._urlopen', side_effect=TimeoutError('slow')):
            with self.assertRaises(SmsDeliveryError) as caught:
                post_sendsms({'apikey': FAKE_KEY, 'recipients': '+919876543210', 'message': 'x'}, 10)
        self.assertEqual(caught.exception.user_message, TIMEOUT)

    def test_urlerror_is_unreachable(self):
        with patch(
            'accounts.smsmobileapi._urlopen',
            side_effect=urllib.error.URLError('no route'),
        ):
            with self.assertRaises(SmsDeliveryError) as caught:
                post_sendsms(
                    {'apikey': FAKE_KEY, 'recipients': '+919876543210', 'message': 'x'},
                    10,
                )
        self.assertEqual(caught.exception.user_message, UNREACHABLE)
        self.assertNotIn(FAKE_KEY, str(caught.exception.user_message))

    def test_http_500_is_unusable(self):
        error = urllib.error.HTTPError(
            SEND_URL,
            500,
            'Server Error',
            hdrs={},
            fp=BytesIO(b'oops'),
        )

        def fake_urlopen(request, timeout=None, context=None):
            raise error

        with patch('accounts.smsmobileapi._urlopen', side_effect=fake_urlopen):
            status, raw, content_type = post_sendsms(
                {'apikey': FAKE_KEY, 'recipients': '+919876543210', 'message': 'x'},
                10,
            )
            with self.assertRaises(SmsDeliveryError) as caught:
                send_message(
                    '9876543210',
                    'KaamDo code: 123456.',
                    api_key=FAKE_KEY,
                    post=lambda fields, timeout: (status, raw, content_type),
                )
        self.assertEqual(caught.exception.user_message, UNUSABLE)
        self.assertNotIn(FAKE_KEY, str(caught.exception.user_message))

    def test_http_403_is_refused(self):
        error = urllib.error.HTTPError(
            SEND_URL,
            403,
            'Forbidden',
            hdrs={},
            fp=BytesIO(b'{"result":{"error":1}}'),
        )

        def fake_urlopen(request, timeout=None, context=None):
            raise error

        with patch('accounts.smsmobileapi._urlopen', side_effect=fake_urlopen):
            with self.assertRaises(SmsDeliveryError) as caught:
                post_sendsms(
                    {'apikey': FAKE_KEY, 'recipients': '+919876543210', 'message': 'x'},
                    10,
                )
        self.assertEqual(caught.exception.user_message, REFUSED)
        self.assertNotIn(FAKE_KEY, str(caught.exception.user_message))

    def test_whitespace_key_does_not_open_the_network(self):
        with patch('accounts.smsmobileapi.post_sendsms') as poster:
            with self.assertRaises(SmsDeliveryError) as caught:
                send_message('9876543210', 'KaamDo code: 123456.', api_key='   ')
        poster.assert_not_called()
        self.assertEqual(caught.exception.user_message, NOT_CONFIGURED)

    def test_env_example_keeps_delivery_unconfigured(self):
        text = Path(__file__).resolve().parents[3].joinpath('.env.example').read_text(encoding='utf-8')
        self.assertIn('KAAMDO_OTP_DELIVERY=unconfigured', text)
        self.assertIsNone(re.search(r'^KAAMDO_OTP_DELIVERY=smsmobileapi\s*$', text, re.M))
        self.assertIsNone(re.search(r'^SMSMOBILEAPI_API_KEY=\S+', text, re.M))

    def test_gitignore_excludes_local_env(self):
        text = Path(__file__).resolve().parents[3].joinpath('.gitignore').read_text(encoding='utf-8')
        self.assertRegex(text, r'(?m)^\.env$')

    @override_settings(DEBUG=False, OTP_DELIVERY='unconfigured')
    def test_sms_flag_is_off_when_delivery_is_unconfigured(self):
        self.assertFalse(sms_otp_enabled())
        self.assertFalse(development_otp_enabled())


SMS_ON = override_settings(
    DEBUG=False,
    OTP_DELIVERY='smsmobileapi',
    SMSMOBILEAPI_API_KEY=FAKE_KEY,
    SMSMOBILEAPI_TIMEOUT_SECONDS=10,
)


class SmsMobileApiOtpViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = User.objects.create_user(
            username='sms-otp-user',
            password='SafePass!234',
            phone_number='9876543210',
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def send(self):
        return self.client.post('/api/v1/auth/otp/send/', {'purpose': 'account'}, format='json')

    @override_settings(DEBUG=False, OTP_DELIVERY='unconfigured', SMSMOBILEAPI_API_KEY='')
    def test_default_delivery_does_not_call_the_provider(self):
        with patch('accounts.otp.send_smsmobileapi_message') as sender:
            response = self.send()
        sender.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('dev_code', response.data)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)
        self.assertEqual(PhoneVerification.objects.count(), 0)

    @override_settings(DEBUG=False, OTP_DELIVERY='smsmobileapi', SMSMOBILEAPI_API_KEY='')
    def test_sms_mode_without_key_creates_no_challenge(self):
        with patch('accounts.otp.send_smsmobileapi_message') as sender:
            response = self.send()
        sender.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    def fake_send(self, phone, message, *, api_key, timeout=10, post=None):
        self.assertEqual(phone, '9876543210')
        self.assertEqual(api_key, FAKE_KEY)
        self.assertIn('123456', message)
        self.assertNotIn(FAKE_KEY, message)
        return {'accepted': True, 'provider_id': 'provider-message-id'}

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_accepted_sms_does_not_verify_or_return_the_code(self, sender, _code):
        sender.side_effect = self.fake_send
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['delivery'], 'sms')
        self.assertEqual(response.data['detail'], SMS_ACCEPTED_DETAIL)
        self.assertNotIn('sent to your mobile', response.data['detail'].lower())
        self.assertNotIn('dev_code', response.data)
        self.assertNotIn('123456', json.dumps(response.data))
        self.assertEqual(PhoneVerification.objects.count(), 0)
        self.assertEqual(PhoneOtpChallenge.objects.filter(consumed=False).count(), 1)
        sender.assert_called_once()

        verified = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '123456'},
            format='json',
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(PhoneVerification.objects.count(), 1)

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch(
        'accounts.otp.send_smsmobileapi_message',
        side_effect=SmsDeliveryError(REFUSED),
    )
    def test_provider_refusal_consumes_the_challenge(self, sender, _code):
        response = self.send()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('dev_code', response.data)
        self.assertEqual(response.data['detail'], REFUSED)
        self.assertNotIn(FAKE_KEY, str(response.data))
        self.assertEqual(PhoneOtpChallenge.objects.filter(consumed=False).count(), 0)
        self.assertEqual(PhoneVerification.objects.count(), 0)
        sender.assert_called_once()

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_wrong_code_does_not_verify_after_an_accepted_sms(self, sender, _code):
        sender.side_effect = self.fake_send
        sent = self.send()
        wrong = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '000000'},
            format='json',
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(PhoneVerification.objects.count(), 0)
        sender.assert_called_once()

    def test_anonymous_send_does_not_call_the_provider(self):
        self.client.credentials()
        with patch('accounts.otp.send_smsmobileapi_message') as sender:
            response = self.send()
        sender.assert_not_called()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    @override_settings(DEBUG=False, OTP_DELIVERY='smsmobileapi', SMSMOBILEAPI_API_KEY='   ')
    def test_blank_key_does_not_call_the_provider(self):
        with patch('accounts.otp.send_smsmobileapi_message') as sender:
            response = self.send()
        sender.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_client_phone_cannot_redirect_the_sms(self, sender, _code):
        sender.side_effect = self.fake_send
        response = self.client.post(
            '/api/v1/auth/otp/send/',
            {'purpose': 'account', 'phone_number': '9123456789'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        sender.assert_called_once()
        self.assertEqual(sender.call_args.args[0], '9876543210')
        self.assertEqual(PhoneOtpChallenge.objects.get().phone_number, '9876543210')

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_code_cannot_verify_another_user(self, sender, _code):
        sender.side_effect = self.fake_send
        sent = self.send()
        other = User.objects.create_user(
            username='sms-otp-other',
            password='SafePass!234',
            phone_number='9123456789',
        )
        other_token = Token.objects.create(user=other)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        stolen = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '123456'},
            format='json',
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(stolen.status_code, 400)
        self.assertEqual(PhoneVerification.objects.count(), 0)

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_code_cannot_verify_another_purpose(self, sender, _code):
        sender.side_effect = self.fake_send
        sent = self.send()
        crossed = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'service_request', 'code': '123456'},
            format='json',
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(crossed.status_code, 400)
        self.assertEqual(PhoneVerification.objects.count(), 0)
        self.assertEqual(
            PhoneOtpChallenge.objects.filter(purpose='account', consumed=False).count(),
            1,
        )

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_expired_code_does_not_verify(self, sender, _code):
        sender.side_effect = self.fake_send
        sent = self.send()
        challenge = PhoneOtpChallenge.objects.get()
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=['expires_at'])
        expired = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '123456'},
            format='json',
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(expired.status_code, 400)
        self.assertEqual(PhoneVerification.objects.count(), 0)

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_resend_limit_is_per_phone_and_purpose(self, sender, _code):
        sender.side_effect = self.fake_send
        statuses = [self.send().status_code for _ in range(MAX_SENDS)]
        blocked = self.send()
        self.assertEqual(statuses, [200] * MAX_SENDS)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(sender.call_count, MAX_SENDS)

    @SMS_ON
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_too_many_wrong_attempts_consume_the_code(self, sender, _code):
        sender.side_effect = self.fake_send
        self.send()
        for _ in range(MAX_ATTEMPTS):
            wrong = self.client.post(
                '/api/v1/auth/otp/verify/',
                {'purpose': 'account', 'code': '000000'},
                format='json',
            )
            self.assertEqual(wrong.status_code, 400)
        late = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '123456'},
            format='json',
        )
        self.assertEqual(late.status_code, 400)
        self.assertEqual(PhoneVerification.objects.count(), 0)
        self.assertEqual(PhoneOtpChallenge.objects.filter(consumed=False).count(), 0)

    @override_settings(DEBUG=True, OTP_DELIVERY='smsmobileapi', SMSMOBILEAPI_API_KEY=FAKE_KEY)
    @patch('accounts.otp._new_code', return_value='123456')
    @patch('accounts.otp.send_smsmobileapi_message')
    def test_debug_does_not_return_a_development_code_in_sms_mode(self, sender, _code):
        sender.side_effect = self.fake_send
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['delivery'], 'sms')
        self.assertNotIn('dev_code', response.data)
        self.assertNotIn('123456', json.dumps(response.data))
