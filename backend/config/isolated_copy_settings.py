"""
Settings for an isolated SQLite copy. Never used by the default runserver.

Set KAAMDO_ISOLATED_SQLITE to an absolute path that is not backend/db.sqlite3.
OTP and payment stay unconfigured so this process cannot send SMS or skip fees.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403

_copy = Path(os.environ.get('KAAMDO_ISOLATED_SQLITE', '')).expanduser()
_live = Path(BASE_DIR) / 'db.sqlite3'  # noqa: F405

if not str(_copy):
    raise ImproperlyConfigured('KAAMDO_ISOLATED_SQLITE must point at an isolated copy.')
if not _copy.is_absolute():
    raise ImproperlyConfigured('KAAMDO_ISOLATED_SQLITE must be an absolute path.')
if _copy.resolve() == _live.resolve():
    raise ImproperlyConfigured('KAAMDO_ISOLATED_SQLITE cannot be backend/db.sqlite3.')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(_copy),
        'OPTIONS': {'timeout': 30},
    }
}

OTP_DELIVERY = 'unconfigured'
SMSMOBILEAPI_API_KEY = ''
KAAMDO_VISIT_PAYMENT = 'unconfigured'
MEDIA_ROOT = Path(os.environ.get('KAAMDO_ISOLATED_MEDIA', str(Path(_copy).parent / 'media')))
