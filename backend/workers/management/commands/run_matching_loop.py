"""
Local or staging loop that calls process_daily_matching on an interval.

This is not Celery. Stop the process to stop matching. Do not use as a
substitute for a real scheduler on a public host without supervision.
"""

import time

from django.core.management.base import BaseCommand

from workers.matching import process_due_matching


class Command(BaseCommand):
    help = 'Repeat daily-service matching until interrupted. Loopback or supervised staging only.'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=15)
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        interval = max(5, min(int(options['interval']), 300))
        self.stdout.write(f'matching loop every {interval}s. Ctrl+C to stop.')
        while True:
            result = process_due_matching(limit=options['limit'])
            self.stdout.write(
                f"expired_offers={result['expired_offers']} requests={result['requests']}"
            )
            time.sleep(interval)
