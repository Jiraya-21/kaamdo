"""
Database engine selection.

SQLite is the default and always uses backend/db.sqlite3.
PostgreSQL is used only when DB_ENGINE is postgresql (or postgres).
Unknown engines are refused so a typo cannot silently open SQLite.
"""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

SQLITE_ENGINE = 'django.db.backends.sqlite3'
POSTGRES_ENGINE = 'django.db.backends.postgresql'
SQLITE_FILENAME = 'db.sqlite3'


def normalize_engine(value):
    name = str(value or 'sqlite').strip().lower()
    if name in ('', 'sqlite', 'sqlite3'):
        return 'sqlite'
    if name in ('postgresql', 'postgres'):
        return 'postgresql'
    raise ImproperlyConfigured(
        'DB_ENGINE must be sqlite or postgresql. Unknown values are refused '
        'so the existing SQLite file is not opened by accident.'
    )


def sqlite_file(base_dir):
    return Path(base_dir) / SQLITE_FILENAME


def _looks_like_sqlite_path(name):
    raw = str(name or '').strip()
    text = raw.replace('\\', '/').lower()
    if not text:
        return False
    if '/' in text or text.endswith('.sqlite3') or text.endswith('.sqlite'):
        return True
    if len(raw) >= 2 and raw[1] == ':':
        return True
    return SQLITE_FILENAME in text


def sqlite_settings(base_dir):
    """Ignore DB_NAME/HOST/PORT. SQLite always uses the project db.sqlite3 path."""
    return {
        'default': {
            'ENGINE': SQLITE_ENGINE,
            'NAME': sqlite_file(base_dir),
        }
    }


def postgresql_settings(name, user, password='', host='', port=''):
    db_name = str(name or '').strip()
    db_user = str(user or '').strip()
    if not db_name:
        raise ImproperlyConfigured(
            'Set DB_NAME to a PostgreSQL database name when DB_ENGINE=postgresql.'
        )
    if _looks_like_sqlite_path(db_name):
        raise ImproperlyConfigured(
            'DB_NAME looks like a SQLite file path. PostgreSQL needs a database '
            'name such as kaamdo_staging, not backend/db.sqlite3.'
        )
    if not db_user:
        raise ImproperlyConfigured('Set DB_USER when DB_ENGINE=postgresql.')
    return {
        'default': {
            'ENGINE': POSTGRES_ENGINE,
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': str(password or ''),
            'HOST': str(host or '127.0.0.1').strip() or '127.0.0.1',
            'PORT': str(port or '5432').strip() or '5432',
        }
    }


def database_settings(engine, base_dir, name='', user='', password='', host='', port=''):
    selected = normalize_engine(engine)
    if selected == 'sqlite':
        return selected, sqlite_settings(base_dir)
    return selected, postgresql_settings(name, user, password, host, port)
