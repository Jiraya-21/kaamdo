"""Apply migrations on a temporary SQLite file. Never opens backend/db.sqlite3."""

import os
import sys
import tempfile
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[2]
LIVE = BACKEND / 'db.sqlite3'


def main():
    work = Path(tempfile.mkdtemp(prefix='kaamdo-isolated-migrate-'))
    isolated = work / 'db.sqlite3'
    isolated.touch()
    if isolated.resolve() == LIVE.resolve():
        raise SystemExit('Refusing to migrate the live SQLite file.')
    os.environ['KAAMDO_ISOLATED_SQLITE'] = str(isolated.resolve())
    os.environ['KAAMDO_ISOLATED_MEDIA'] = str(work / 'media')
    os.environ['KAAMDO_OTP_DELIVERY'] = 'unconfigured'
    os.environ['KAAMDO_VISIT_PAYMENT'] = 'unconfigured'
    os.environ['SMSMOBILEAPI_API_KEY'] = ''
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.isolated_copy_settings'
    sys.path.insert(0, str(BACKEND))

    import django
    from django.conf import settings

    django.setup()
    configured = Path(settings.DATABASES['default']['NAME']).resolve()
    if configured == LIVE.resolve():
        raise SystemExit('Isolated migrate settings pointed at the live database.')
    from django.core.management import call_command

    call_command('migrate', verbosity=1, interactive=False)
    print('ISOLATED_MIGRATE_OK', isolated.stat().st_size)
    print('ISOLATED_PATH', isolated)
    return 0


if __name__ == '__main__':
    sys.exit(main())
