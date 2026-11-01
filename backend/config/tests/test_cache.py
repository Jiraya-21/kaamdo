"""Cache configuration for OTP IP limits. These tests do not contact Redis."""

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import Throttled

from accounts.otp_ip import OTP_IP_WAIT, enforce_otp_ip_limit
from config.cache import (
    DUMMY_BACKEND,
    LOCMEM_BACKEND,
    REDIS_BACKEND,
    cache_settings,
    check_shared_cache_when_sms_is_on,
)


class FakeRequest:
    def __init__(self, **meta):
        self.META = meta


class CacheSettingsTests(SimpleTestCase):
    def test_default_is_locmem_and_does_not_use_redis(self):
        configured = cache_settings()
        self.assertEqual(configured['default']['BACKEND'], LOCMEM_BACKEND)
        self.assertEqual(configured['default']['LOCATION'], 'kaamdo-default')
        self.assertNotEqual(configured['default']['BACKEND'], REDIS_BACKEND)

    def test_redis_requires_a_redis_url(self):
        with self.assertRaises(ImproperlyConfigured) as missing:
            cache_settings('redis', '', debug=False)
        with self.assertRaises(ImproperlyConfigured) as scheme:
            cache_settings('redis', 'http://127.0.0.1:6379/1', debug=False)
        self.assertIn('KAAMDO_CACHE_URL', str(missing.exception))
        self.assertIn('redis://', str(scheme.exception))

    def test_redis_is_configured_or_refused_without_opening_a_connection(self):
        try:
            import redis  # noqa: F401
        except ImportError:
            with self.assertRaises(ImproperlyConfigured) as caught:
                cache_settings('redis', 'redis://127.0.0.1:6379/1', debug=False)
            self.assertIn('Install the redis package', str(caught.exception))
            return
        configured = cache_settings('redis', 'redis://127.0.0.1:6379/1', debug=False)
        self.assertEqual(configured['default']['BACKEND'], REDIS_BACKEND)
        self.assertEqual(configured['default']['LOCATION'], 'redis://127.0.0.1:6379/1')

    def test_dummy_is_refused_when_debug_is_off(self):
        allowed = cache_settings('dummy', debug=True)
        self.assertEqual(allowed['default']['BACKEND'], DUMMY_BACKEND)
        with self.assertRaises(ImproperlyConfigured):
            cache_settings('dummy', debug=False)

    def test_unknown_backend_is_refused(self):
        with self.assertRaises(ImproperlyConfigured):
            cache_settings('memcached')

    @override_settings(DEBUG=True, OTP_DELIVERY='smsmobileapi')
    def test_locmem_sms_is_allowed_in_debug(self):
        self.assertEqual(check_shared_cache_when_sms_is_on(None), [])

    @override_settings(DEBUG=False, OTP_DELIVERY='unconfigured')
    def test_locmem_without_sms_is_not_a_production_error(self):
        self.assertEqual(check_shared_cache_when_sms_is_on(None), [])

    @override_settings(DEBUG=False, OTP_DELIVERY='smsmobileapi')
    def test_locmem_sms_is_an_error_when_debug_is_off(self):
        errors = check_shared_cache_when_sms_is_on(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'kaamdo.E001')


class ConfiguredLocMemThrottleTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(
        CACHES={
            'default': {
                'BACKEND': LOCMEM_BACKEND,
                'LOCATION': 'kaamdo-throttle-tests',
                'KEY_PREFIX': 'kaamdo',
            }
        },
        OTP_IP_SEND_LIMIT=1,
        OTP_IP_WINDOW_MINUTES=15,
    )
    def test_explicit_locmem_still_throttles_the_same_ip(self):
        first = FakeRequest(REMOTE_ADDR='203.0.113.50')
        second = FakeRequest(REMOTE_ADDR='203.0.113.50')
        other = FakeRequest(REMOTE_ADDR='203.0.113.51')
        enforce_otp_ip_limit(first, 'send')
        with self.assertRaises(Throttled) as caught:
            enforce_otp_ip_limit(second, 'send')
        enforce_otp_ip_limit(other, 'send')
        self.assertEqual(caught.exception.detail, OTP_IP_WAIT)
        self.assertEqual(caught.exception.status_code, 429)
