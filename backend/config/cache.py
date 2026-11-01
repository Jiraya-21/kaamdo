"""
OTP IP limits use Django's cache.

LocMemCache is the local default. It does not contact Redis and does not share
counts across processes. Redis is optional and is configured only through env.
"""

from django.core.checks import Error, Tags, Warning, register
from django.core.exceptions import ImproperlyConfigured

LOCMEM_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'
REDIS_BACKEND = 'django.core.cache.backends.redis.RedisCache'
DUMMY_BACKEND = 'django.core.cache.backends.dummy.DummyCache'


def cache_settings(backend='locmem', location='', debug=True):
    """Return a CACHES mapping. Redis is not contacted here."""
    name = str(backend or 'locmem').strip().lower() or 'locmem'
    if name in ('locmem', 'locmemcache', 'local'):
        return {
            'default': {
                'BACKEND': LOCMEM_BACKEND,
                'LOCATION': 'kaamdo-default',
                'KEY_PREFIX': 'kaamdo',
            }
        }
    if name == 'dummy':
        if not debug:
            raise ImproperlyConfigured(
                'DummyCache disables OTP IP limits. Do not use KAAMDO_CACHE_BACKEND=dummy with DEBUG=False.'
            )
        return {'default': {'BACKEND': DUMMY_BACKEND}}
    if name == 'redis':
        url = str(location or '').strip()
        if not url:
            raise ImproperlyConfigured(
                'Set KAAMDO_CACHE_URL to a redis:// or rediss:// URL when KAAMDO_CACHE_BACKEND=redis.'
            )
        if not url.lower().startswith(('redis://', 'rediss://')):
            raise ImproperlyConfigured('KAAMDO_CACHE_URL must start with redis:// or rediss://.')
        try:
            import redis  # noqa: F401
        except ImportError as exc:
            raise ImproperlyConfigured(
                'Install the redis package before KAAMDO_CACHE_BACKEND=redis: '
                'python -m pip install "redis>=5,<7".'
            ) from exc
        return {
            'default': {
                'BACKEND': REDIS_BACKEND,
                'LOCATION': url,
                'KEY_PREFIX': 'kaamdo',
            }
        }
    raise ImproperlyConfigured('KAAMDO_CACHE_BACKEND must be locmem, redis, or dummy.')


@register(Tags.caches, deploy=True)
def check_locmem_not_shared(app_configs, **kwargs):
    from django.conf import settings

    backend = str(settings.CACHES.get('default', {}).get('BACKEND') or '')
    if 'locmem' in backend.lower():
        return [
            Warning(
                'LocMemCache is per-process. OTP IP limits will not be shared across workers.',
                hint='Set KAAMDO_CACHE_BACKEND=redis and KAAMDO_CACHE_URL when more than one worker serves OTP.',
                id='kaamdo.W001',
            )
        ]
    return []


@register(Tags.caches, deploy=True)
def check_shared_cache_when_sms_is_on(app_configs, **kwargs):
    from django.conf import settings

    if settings.DEBUG:
        return []
    delivery = str(getattr(settings, 'OTP_DELIVERY', 'unconfigured') or '').strip().lower()
    if delivery != 'smsmobileapi':
        return []
    backend = str(settings.CACHES.get('default', {}).get('BACKEND') or '')
    if 'locmem' not in backend.lower():
        return []
    return [
        Error(
            'SMS OTP IP limits cannot use LocMemCache when DEBUG=False.',
            hint='Set KAAMDO_CACHE_BACKEND=redis and KAAMDO_CACHE_URL before enabling SMS in production.',
            id='kaamdo.E001',
        )
    ]
