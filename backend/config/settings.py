"""
Django settings for KaamDo project.
Configured for local SQLite development and production PostgreSQL deployment.
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

from .cache import cache_settings
from .database import database_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from root or backend directory.
# override=True so a stale parent-shell SMS/OTP export cannot keep a refused key
# after .env was updated. Backend .env wins over the repo-root .env.
load_dotenv(BASE_DIR.parent / '.env', override=True)
load_dotenv(BASE_DIR / '.env', override=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-kaamdo-placeholder-key-for-local-dev-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

def _normalize_allowed_host(raw):
    """Accept hostname only; strip scheme/quotes users often paste from the browser URL."""
    host = str(raw or '').strip().strip('"').strip("'")
    if not host:
        return ''
    if '://' in host:
        host = host.split('://', 1)[1]
    host = host.split('/', 1)[0].strip()
    return host


_allowed_hosts_env = os.getenv('ALLOWED_HOSTS')
ALLOWED_HOSTS = [
    host
    for host in (
        _normalize_allowed_host(item)
        for item in (_allowed_hosts_env or 'localhost,127.0.0.1').split(',')
    )
    if host
]
# Render sets this automatically to the live hostname (e.g. kaamdo-kg5r.onrender.com).
_render_host = _normalize_allowed_host(os.getenv('RENDER_EXTERNAL_HOSTNAME', ''))
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

# Application definition
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'config.apps.KaamdoConfig',

    # KaamDo Domain Apps
    'accounts',
    'workers',
    'jobs',
    'equipment',
    'reviews',
    'notifications',
    'reliability',
    'locations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS must be at the top
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration
# Defaults to SQLite (backend/db.sqlite3). PostgreSQL is used only when
# DB_ENGINE=postgresql. Unknown engines are refused. SQLite ignores DB_NAME
# so a Postgres database name cannot retarget the existing file.
# Install the driver first: python -m pip install "psycopg[binary]"
DB_ENGINE, DATABASES = database_settings(
    os.getenv('DB_ENGINE', 'sqlite'),
    BASE_DIR,
    name=os.getenv('DB_NAME', ''),
    user=os.getenv('DB_USER', ''),
    password=os.getenv('DB_PASSWORD', ''),
    host=os.getenv('DB_HOST', ''),
    port=os.getenv('DB_PORT', ''),
)

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS Settings (local defaults). DEBUG=False requires CORS_ALLOWED_ORIGINS in the environment.
_cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS')
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in (
        _cors_origins_env
        or 'http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000,http://[::1]:8989,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8768,http://127.0.0.1:8768'
    ).split(',') if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
_csrf_trusted_env = os.getenv('CSRF_TRUSTED_ORIGINS')

# Hosted exhibition only. Lets development OTP + mock visit payment run with DEBUG=False.
# Never enable this for a real public money launch. Real SMS/payments stay separate.
KAAMDO_STAGING_DEMO = os.getenv('KAAMDO_STAGING_DEMO', '').strip().lower() in ('true', '1', 'yes')

# A code is shown only when delivery is "development" and (DEBUG or KAAMDO_STAGING_DEMO).
# SMSMobileAPI is used only when this is explicitly "smsmobileapi" and a server key is set.
# The default refuses to create or display a code.
OTP_DELIVERY = str(os.getenv('KAAMDO_OTP_DELIVERY', 'unconfigured') or 'unconfigured').strip().lower()
SMSMOBILEAPI_API_KEY = str(os.getenv('SMSMOBILEAPI_API_KEY', '') or '').strip()
try:
    _sms_timeout = int(os.getenv('SMSMOBILEAPI_TIMEOUT_SECONDS', '10') or '10')
except (TypeError, ValueError):
    _sms_timeout = 10
SMSMOBILEAPI_TIMEOUT_SECONDS = min(max(_sms_timeout, 1), 30)


def _bounded_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        value = default
    return min(max(value, minimum), maximum)


# Per-IP OTP caps. These do not replace the per-phone send cap (3 / 15 minutes).
# Django's default LocMemCache is per-process; use Redis or Memcached if more
# than one worker serves OTP. X-Forwarded-For is used only when REMOTE_ADDR is
# listed in OTP_TRUSTED_PROXIES. Leave that list empty unless a reverse proxy
# you control terminates TLS in front of Django.
OTP_IP_SEND_LIMIT = _bounded_int('KAAMDO_OTP_IP_SEND_LIMIT', 8, 1, 1000)
OTP_IP_VERIFY_LIMIT = _bounded_int('KAAMDO_OTP_IP_VERIFY_LIMIT', 25, 1, 1000)
OTP_IP_WINDOW_MINUTES = _bounded_int('KAAMDO_OTP_IP_WINDOW_MINUTES', 15, 1, 1440)
OTP_TRUSTED_PROXIES = [
    item.strip()
    for item in os.getenv('KAAMDO_OTP_TRUSTED_PROXIES', '').split(',')
    if item.strip()
]

# LocMemCache is the local default and does not contact Redis.
# Multi-worker OTP IP limits need KAAMDO_CACHE_BACKEND=redis and a redis:// URL.
CACHES = cache_settings(
    os.getenv('KAAMDO_CACHE_BACKEND', 'locmem'),
    os.getenv('KAAMDO_CACHE_URL', ''),
    debug=DEBUG,
)

# Staff/local mock visit fee. Default refuses.
# Allowed with DEBUG=True, or with KAAMDO_STAGING_DEMO=true on a hosted exhibition.
# Values: mock_demo or test_bypass. Neither is money received.
KAAMDO_VISIT_PAYMENT = os.getenv('KAAMDO_VISIT_PAYMENT', 'unconfigured')

# Daily Services matching. These are starting values, not proven optima.
# Distance is a straight-line estimate. It is not road distance or travel time.
KAAMDO_MATCH_BATCH_SIZE = _bounded_int('KAAMDO_MATCH_BATCH_SIZE', 3, 1, 10)
KAAMDO_MATCH_OFFER_WINDOW_SECONDS = _bounded_int('KAAMDO_MATCH_OFFER_WINDOW_SECONDS', 180, 30, 3600)
KAAMDO_MATCH_MAX_ROUNDS = _bounded_int('KAAMDO_MATCH_MAX_ROUNDS', 6, 1, 20)
# Hard ceiling for staged search. Customer radius_km may be 5-100; stages stay 8,15,20.
KAAMDO_MATCH_MAX_RADIUS_KM = _bounded_int('KAAMDO_MATCH_MAX_RADIUS_KM', 100, 8, 100)
_match_stages = []
for _stage in os.getenv('KAAMDO_MATCH_RADIUS_STAGES', '8,15,20').split(','):
    try:
        _value = int(_stage.strip())
    except (TypeError, ValueError):
        continue
    if 5 <= _value <= 100 and _value not in _match_stages:
        _match_stages.append(_value)
KAAMDO_MATCH_RADIUS_STAGES = tuple(_match_stages or (8, 15, 20))

# Automated tests never inherit live SMS or payment flags from a local .env.
# Individual tests still use override_settings when they need those paths.
if 'test' in sys.argv:
    OTP_DELIVERY = 'unconfigured'
    SMSMOBILEAPI_API_KEY = ''
    KAAMDO_VISIT_PAYMENT = 'unconfigured'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv('STATIC_URL', 'static/')
STATIC_ROOT = Path(os.getenv('STATIC_ROOT', str(BASE_DIR / 'staticfiles')))
# Sibling frontend/ folder (HTML site served by config.frontend.FrontendView).
FRONTEND_ROOT = Path(os.getenv('FRONTEND_ROOT', str(BASE_DIR.parent / 'frontend')))

# Media files (worker profile photos). Django serves these only when DEBUG is True.
# Production must serve MEDIA_ROOT at MEDIA_URL from the reverse proxy or object storage.
# Photos on published profiles are public. Do not store identity documents here.
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BASE_DIR / 'media')))

# Hosts such as Render set PORT. Django runserver ignores it. The process
# manager must bind 0.0.0.0:$PORT. See deploy/render.example.yaml.
KAAMDO_HTTP_PORT = os.getenv('PORT', '8000')

# Maps. Default is none. Do not enable public Nominatim autocomplete.
# osm shows OpenStreetMap attribution only when the page is given real GPS.
KAAMDO_MAP_PROVIDER = os.getenv('KAAMDO_MAP_PROVIDER', 'none').strip().lower() or 'none'
KAAMDO_MAP_ATTRIBUTION = os.getenv(
    'KAAMDO_MAP_ATTRIBUTION',
    'Map data © OpenStreetMap contributors',
)
# Reverse geocode only. Default nominatim_reverse. Tests force none.
# Never use public Nominatim for autocomplete or search-as-you-type.
KAAMDO_GEOCODE_PROVIDER = os.getenv(
    'KAAMDO_GEOCODE_PROVIDER',
    'nominatim_reverse',
).strip().lower() or 'none'
KAAMDO_GEOCODE_USER_AGENT = os.getenv(
    'KAAMDO_GEOCODE_USER_AGENT',
    'KaamDo/1.0 (reverse-geocode; local development)',
)
try:
    KAAMDO_GEOCODE_TIMEOUT_SECONDS = int(os.getenv('KAAMDO_GEOCODE_TIMEOUT_SECONDS', '8') or '8')
except ValueError:
    KAAMDO_GEOCODE_TIMEOUT_SECONDS = 8
if 'test' in sys.argv:
    KAAMDO_GEOCODE_PROVIDER = 'none'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from .security import apply_production_protections
apply_production_protections(globals(), {
    'ALLOWED_HOSTS': _allowed_hosts_env,
    'CORS_ALLOWED_ORIGINS': _cors_origins_env,
    'CSRF_TRUSTED_ORIGINS': _csrf_trusted_env,
    'DB_NAME': os.getenv('DB_NAME'),
    'KAAMDO_TRUST_X_FORWARDED_PROTO': os.getenv('KAAMDO_TRUST_X_FORWARDED_PROTO'),
    'KAAMDO_ALLOW_SQLITE': os.getenv('KAAMDO_ALLOW_SQLITE'),
    'KAAMDO_STAGING_DEMO': os.getenv('KAAMDO_STAGING_DEMO'),
})
