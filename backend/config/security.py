"""
Production safeguards that do not send SMS, email, or payments.
Local DEBUG stays usable with the placeholder secret.
HTTPS redirect is not forced here.
"""

from django.core.exceptions import ImproperlyConfigured

PLACEHOLDER_SECRET_PREFIX = 'django-insecure-'
PLACEHOLDER_SECRETS = {
    'django-insecure-kaamdo-placeholder-key-for-local-dev-only',
    'change-me-to-a-secure-random-secret-key-for-production',
    'change-me-to-a-secure-random-secret-key-in-production',
}
MIN_SECRET_LENGTH = 50


def parse_csv(value):
    return [part.strip() for part in str(value or '').split(',') if part.strip()]


def require_real_secret_key(debug, secret_key):
    """Refuse a public launch that still uses the local placeholder secret."""
    if debug:
        return
    key = str(secret_key or '')
    if not key or key in PLACEHOLDER_SECRETS or key.startswith(PLACEHOLDER_SECRET_PREFIX):
        raise ImproperlyConfigured(
            'Set SECRET_KEY to a unique value before running with DEBUG=False.'
        )
    if len(key) < MIN_SECRET_LENGTH:
        raise ImproperlyConfigured(
            'Set SECRET_KEY to at least 50 characters before running with DEBUG=False.'
        )


def require_explicit_hosts(debug, allowed_hosts, hosts_env):
    """DEBUG=False needs an explicit ALLOWED_HOSTS value. A wildcard is refused."""
    if debug:
        return
    if hosts_env is None or not str(hosts_env).strip():
        raise ImproperlyConfigured(
            'Set ALLOWED_HOSTS to the public hostname before running with DEBUG=False.'
        )
    hosts = [str(host).strip() for host in (allowed_hosts or []) if str(host).strip()]
    if not hosts:
        raise ImproperlyConfigured(
            'Set ALLOWED_HOSTS to the public hostname before running with DEBUG=False.'
        )
    if any(host == '*' for host in hosts):
        raise ImproperlyConfigured('ALLOWED_HOSTS cannot be * when DEBUG=False.')


def require_explicit_origins(debug, cors_origins, origins_env):
    """DEBUG=False needs an explicit CORS origin list. Do not keep the local default silently."""
    if debug:
        return
    if origins_env is None or not str(origins_env).strip():
        raise ImproperlyConfigured(
            'Set CORS_ALLOWED_ORIGINS to the public frontend origin before running with DEBUG=False.'
        )
    origins = list(cors_origins or [])
    if not origins:
        raise ImproperlyConfigured(
            'Set CORS_ALLOWED_ORIGINS to the public frontend origin before running with DEBUG=False.'
        )
    for origin in origins:
        text = str(origin)
        if not text.startswith(('http://', 'https://')):
            raise ImproperlyConfigured(
                'CORS_ALLOWED_ORIGINS values must include http:// or https://.'
            )
        if _is_loopback_origin(text):
            raise ImproperlyConfigured(
                'CORS_ALLOWED_ORIGINS must be the real frontend origin when DEBUG=False. '
                'localhost and 127.0.0.1 are refused.'
            )


def require_production_database(debug, engine, name_env, allow_sqlite=False):
    """Staging and production need PostgreSQL. SQLite is local-only unless explicitly allowed."""
    if debug:
        return
    selected = str(engine or '').strip().lower()
    if selected != 'postgresql':
        if allow_sqlite:
            return
        raise ImproperlyConfigured(
            'DEBUG=False requires DB_ENGINE=postgresql. SQLite is local-only.'
        )
    if name_env is None or not str(name_env).strip():
        raise ImproperlyConfigured(
            'Set DB_NAME before running PostgreSQL with DEBUG=False.'
        )


def require_payments_unconfigured(debug, visit_payment, staging_demo=False):
    """A public process cannot enable the mock visit-fee skip unless staging demo is on."""
    if debug or staging_demo:
        return
    value = str(visit_payment or 'unconfigured').strip().lower()
    if value not in ('', 'unconfigured'):
        raise ImproperlyConfigured(
            'KAAMDO_VISIT_PAYMENT must stay unconfigured when DEBUG=False '
            '(set KAAMDO_STAGING_DEMO=true only for a hosted exhibition).'
        )


def _is_loopback_origin(origin):
    text = str(origin or '').casefold()
    return any(marker in text for marker in ('localhost', '127.0.0.1', '[::1]'))


def env_flag(value):
    return str(value or '').strip().lower() in ('true', '1', 'yes')


def production_security_settings(debug, trust_forwarded_proto=False):
    """Cookie and header flags for DEBUG=False. HTTPS redirect is not forced here."""
    if debug:
        return {}
    flags = {
        'SESSION_COOKIE_SECURE': True,
        'CSRF_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'CSRF_COOKIE_HTTPONLY': True,
        'SECURE_CONTENT_TYPE_NOSNIFF': True,
        'SECURE_REFERRER_POLICY': 'same-origin',
        'X_FRAME_OPTIONS': 'DENY',
    }
    if trust_forwarded_proto:
        # Only after a reverse proxy you control overwrites X-Forwarded-Proto.
        flags['SECURE_PROXY_SSL_HEADER'] = ('HTTP_X_FORWARDED_PROTO', 'https')
    return flags


def csrf_trusted_origins(debug, csrf_env, cors_origins):
    """Use CSRF_TRUSTED_ORIGINS when set. Otherwise reuse CORS origins when DEBUG is off."""
    explicit = parse_csv(csrf_env)
    if explicit:
        return explicit
    if debug:
        return []
    return [str(origin) for origin in (cors_origins or []) if str(origin).strip()]


def apply_production_protections(settings_dict, env_values=None):
    env_values = env_values or {}
    debug = settings_dict['DEBUG']
    require_real_secret_key(debug, settings_dict['SECRET_KEY'])
    require_explicit_hosts(
        debug,
        settings_dict.get('ALLOWED_HOSTS'),
        env_values.get('ALLOWED_HOSTS'),
    )
    require_explicit_origins(
        debug,
        settings_dict.get('CORS_ALLOWED_ORIGINS'),
        env_values.get('CORS_ALLOWED_ORIGINS'),
    )
    require_production_database(
        debug,
        settings_dict.get('DB_ENGINE'),
        env_values.get('DB_NAME'),
        allow_sqlite=env_flag(env_values.get('KAAMDO_ALLOW_SQLITE')),
    )
    require_payments_unconfigured(
        debug,
        settings_dict.get('KAAMDO_VISIT_PAYMENT'),
        staging_demo=env_flag(env_values.get('KAAMDO_STAGING_DEMO')),
    )
    settings_dict.update(production_security_settings(
        debug,
        trust_forwarded_proto=env_flag(env_values.get('KAAMDO_TRUST_X_FORWARDED_PROTO')),
    ))
    trusted = csrf_trusted_origins(
        debug,
        env_values.get('CSRF_TRUSTED_ORIGINS'),
        settings_dict.get('CORS_ALLOWED_ORIGINS'),
    )
    if trusted:
        if not debug and any(_is_loopback_origin(origin) for origin in trusted):
            raise ImproperlyConfigured(
                'CSRF_TRUSTED_ORIGINS must be the real frontend origin when DEBUG=False.'
            )
        settings_dict['CSRF_TRUSTED_ORIGINS'] = trusted
