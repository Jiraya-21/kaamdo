"""Production secret, hosts, CORS, and cookie flags. These tests do not send SMS or payments."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.security import (
    apply_production_protections,
    csrf_trusted_origins,
    production_security_settings,
    require_explicit_hosts,
    require_explicit_origins,
    require_payments_unconfigured,
    require_production_database,
    require_real_secret_key,
)

PRODUCTION_SECRET = 'kaamdo-test-only-unique-secret-key-50-chars-ok!!!!'


class ProductionSecurityTests(SimpleTestCase):
    def test_placeholder_secret_is_refused_when_debug_is_off(self):
        require_real_secret_key(True, 'django-insecure-kaamdo-placeholder-key-for-local-dev-only')
        with self.assertRaises(ImproperlyConfigured):
            require_real_secret_key(False, 'django-insecure-kaamdo-placeholder-key-for-local-dev-only')
        with self.assertRaises(ImproperlyConfigured):
            require_real_secret_key(False, 'change-me-to-a-secure-random-secret-key-in-production')
        with self.assertRaises(ImproperlyConfigured):
            require_real_secret_key(False, '')
        with self.assertRaises(ImproperlyConfigured):
            require_real_secret_key(False, 'short-unique-secret')
        require_real_secret_key(False, PRODUCTION_SECRET)

    def test_explicit_hosts_are_required_when_debug_is_off(self):
        require_explicit_hosts(True, ['localhost'], None)
        with self.assertRaises(ImproperlyConfigured):
            require_explicit_hosts(False, ['localhost'], None)
        with self.assertRaises(ImproperlyConfigured):
            require_explicit_hosts(False, ['*'], '*')
        require_explicit_hosts(False, ['example.test'], 'example.test')

    def test_explicit_cors_origins_are_required_when_debug_is_off(self):
        require_explicit_origins(True, ['http://127.0.0.1:5500'], None)
        with self.assertRaises(ImproperlyConfigured):
            require_explicit_origins(False, ['http://127.0.0.1:5500'], None)
        with self.assertRaises(ImproperlyConfigured):
            require_explicit_origins(False, ['example.test'], 'example.test')
        require_explicit_origins(
            False,
            ['https://example.test'],
            'https://example.test',
        )
        with self.assertRaises(ImproperlyConfigured):
            require_explicit_origins(
                False,
                ['http://localhost:5500'],
                'http://localhost:5500',
            )

    def test_postgresql_name_is_required_when_debug_is_off(self):
        require_production_database(True, 'postgresql', None)
        with self.assertRaises(ImproperlyConfigured):
            require_production_database(False, 'sqlite', None)
        require_production_database(False, 'sqlite', None, allow_sqlite=True)
        with self.assertRaises(ImproperlyConfigured):
            require_production_database(False, 'postgresql', None)
        require_production_database(False, 'postgresql', 'kaamdo_db')

    def test_payments_stay_unconfigured_when_debug_is_off(self):
        require_payments_unconfigured(True, 'mock_demo')
        require_payments_unconfigured(False, 'unconfigured')
        require_payments_unconfigured(False, 'mock_demo', staging_demo=True)
        with self.assertRaises(ImproperlyConfigured):
            require_payments_unconfigured(False, 'mock_demo')
        with self.assertRaises(ImproperlyConfigured):
            require_payments_unconfigured(False, 'test_bypass')

    def test_csrf_origins_reuse_cors_when_debug_is_off(self):
        self.assertEqual(csrf_trusted_origins(True, None, ['http://127.0.0.1:5500']), [])
        self.assertEqual(
            csrf_trusted_origins(False, None, ['https://example.test']),
            ['https://example.test'],
        )
        self.assertEqual(
            csrf_trusted_origins(False, 'https://app.example.test', ['https://example.test']),
            ['https://app.example.test'],
        )

    def test_secure_cookies_are_only_set_when_debug_is_off(self):
        self.assertEqual(production_security_settings(True), {})
        flags = production_security_settings(False)
        self.assertTrue(flags['SESSION_COOKIE_SECURE'])
        self.assertTrue(flags['CSRF_COOKIE_SECURE'])
        self.assertTrue(flags['SESSION_COOKIE_HTTPONLY'])
        self.assertTrue(flags['CSRF_COOKIE_HTTPONLY'])
        self.assertTrue(flags['SECURE_CONTENT_TYPE_NOSNIFF'])
        self.assertEqual(flags['X_FRAME_OPTIONS'], 'DENY')
        self.assertNotIn('SECURE_SSL_REDIRECT', flags)
        self.assertNotIn('SECURE_HSTS_SECONDS', flags)
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', flags)

    def test_forwarded_proto_is_trusted_only_when_asked(self):
        flags = production_security_settings(False, trust_forwarded_proto=True)
        self.assertEqual(flags['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertNotIn('SECURE_SSL_REDIRECT', flags)

    def test_apply_updates_a_debug_off_mapping(self):
        settings_dict = {
            'DEBUG': False,
            'SECRET_KEY': PRODUCTION_SECRET,
            'ALLOWED_HOSTS': ['example.test'],
            'CORS_ALLOWED_ORIGINS': ['https://example.test'],
            'DB_ENGINE': 'postgresql',
            'KAAMDO_VISIT_PAYMENT': 'unconfigured',
        }
        apply_production_protections(settings_dict, {
            'ALLOWED_HOSTS': 'example.test',
            'CORS_ALLOWED_ORIGINS': 'https://example.test',
            'DB_NAME': 'kaamdo_db',
        })
        self.assertTrue(settings_dict['SESSION_COOKIE_SECURE'])
        self.assertEqual(settings_dict['CSRF_TRUSTED_ORIGINS'], ['https://example.test'])
        self.assertNotIn('SECURE_SSL_REDIRECT', settings_dict)
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', settings_dict)

    def test_apply_trusts_forwarded_proto_from_env(self):
        settings_dict = {
            'DEBUG': False,
            'SECRET_KEY': PRODUCTION_SECRET,
            'ALLOWED_HOSTS': ['example.test'],
            'CORS_ALLOWED_ORIGINS': ['https://example.test'],
            'DB_ENGINE': 'postgresql',
            'KAAMDO_VISIT_PAYMENT': 'unconfigured',
        }
        apply_production_protections(settings_dict, {
            'ALLOWED_HOSTS': 'example.test',
            'CORS_ALLOWED_ORIGINS': 'https://example.test',
            'DB_NAME': 'kaamdo_db',
            'KAAMDO_TRUST_X_FORWARDED_PROTO': 'true',
        })
        self.assertEqual(
            settings_dict['SECURE_PROXY_SSL_HEADER'],
            ('HTTP_X_FORWARDED_PROTO', 'https'),
        )
