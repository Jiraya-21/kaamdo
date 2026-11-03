"""
WSGI config for KaamDo project.
Exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()


def _truthy(name):
    return str(os.getenv(name, '') or '').strip().lower() in ('1', 'true', 'yes')


def _bootstrap_render_database():
    """
    Free-tier Render often starts with an empty Postgres.
    When RENDER=true (set by Render), apply migrations and seed so signup/services work.
    """
    if not (_truthy('RENDER') or _truthy('KAAMDO_AUTO_MIGRATE')):
        return
    try:
        call_command('migrate', interactive=False, verbosity=1)
        call_command('seed_karnataka_locations', verbosity=1)
        call_command('seed_service_categories', verbosity=1)
        if _truthy('KAAMDO_SEED_DEMO') or _truthy('RENDER'):
            call_command('seed_first_area_demo', verbosity=1)
    except Exception as exc:  # noqa: BLE001 - keep the web process up; fix DB via env/logs
        # Do not crash gunicorn on a bad DB host — the site can still serve HTML while
        # Render env is corrected. API routes will fail until migrate succeeds on a later boot.
        print(f'KaamDo Render bootstrap failed: {exc}', file=sys.stderr)


_bootstrap_render_database()
