"""
Expire due Daily Services offers and start the next batch.

This is the automatic trigger. A page refresh is not required.
Run it from Task Scheduler or cron, or use run_matching_loop for a local process.
"""

from django.core.management.base import BaseCommand

from workers.matching import process_due_matching


class Command(BaseCommand):
    help = 'Expire due daily-service offers and continue matching. Does not send SMS.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        result = process_due_matching(limit=options['limit'])
        self.stdout.write(
            f"expired_offers={result['expired_offers']} requests={result['requests']}"
        )
