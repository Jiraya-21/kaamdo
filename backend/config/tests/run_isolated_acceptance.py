"""
Create a consistent SQLite copy, migrate only the copy, run acceptance checks.

Never migrates backend/db.sqlite3. Never prints secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[2]
LIVE = BACKEND / 'db.sqlite3'


def sha256_and_size(path: Path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    stat = path.stat()
    return {
        'sha256': digest.hexdigest(),
        'size': size,
        'mtime_ns': stat.st_mtime_ns,
    }


def consistent_copy(source: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    src = sqlite3.connect(f'file:{source.as_posix()}?mode=ro', uri=True)
    try:
        src.execute('PRAGMA query_only=ON')
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


def assert_not_live(path: Path):
    if path.resolve() == LIVE.resolve():
        raise SystemExit('Refusing to use the live SQLite file.')


def main():
    if not LIVE.exists():
        raise SystemExit(f'Missing {LIVE}')
    before = sha256_and_size(LIVE)
    work = Path(tempfile.mkdtemp(prefix='kaamdo-accept-'))
    copy = work / 'db-copy.sqlite3'
    media = work / 'media'
    media.mkdir()
    consistent_copy(LIVE, copy)
    after_copy = sha256_and_size(LIVE)
    assert_not_live(copy)
    os.environ['KAAMDO_ISOLATED_SQLITE'] = str(copy.resolve())
    os.environ['KAAMDO_ISOLATED_MEDIA'] = str(media.resolve())
    os.environ['KAAMDO_OTP_DELIVERY'] = 'unconfigured'
    os.environ['KAAMDO_VISIT_PAYMENT'] = 'unconfigured'
    os.environ['SMSMOBILEAPI_API_KEY'] = ''
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.isolated_copy_settings'
    sys.path.insert(0, str(BACKEND))

    import django
    from django.core.exceptions import ImproperlyConfigured

    django.setup()
    from django.conf import settings
    from django.core.management import call_command

    configured = Path(settings.DATABASES['default']['NAME']).resolve()
    if configured == LIVE.resolve():
        raise ImproperlyConfigured('Isolated settings pointed at the live database.')
    call_command('migrate', 'workers', '0008', verbosity=1, interactive=False)

    from config.tests.isolated_acceptance import (
        concurrency_sqlite,
        existing_records_readable,
        matching_lifecycle,
        scheduler_loop_two_cycles,
        scheduler_once,
    )

    results = [existing_records_readable()]
    results.extend(matching_lifecycle())
    results.extend(concurrency_sqlite())
    results.extend(scheduler_once())
    results.extend(scheduler_loop_two_cycles())
    after_work = sha256_and_size(LIVE)
    unchanged = before == after_copy == after_work
    report = {
        'live_database': str(LIVE),
        'copy_database': str(copy),
        'original_before': before,
        'original_after_copy': after_copy,
        'original_after_acceptance': after_work,
        'original_unchanged': unchanged,
        'copy_size': copy.stat().st_size,
        'results': results,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if unchanged and all(item['status'] in {'PASS', 'NOT TESTED'} for item in results) else 1


if __name__ == '__main__':
    sys.exit(main())
