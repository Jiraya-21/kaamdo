"""
Load official Karnataka districts and taluks into the locations tables.

This command does not invent villages or coordinates. It does not open
backend/db.sqlite3 unless Django is already pointed at that file.
Use an isolated database for the first apply.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from locations.catalog import DISTRICT_RECORDS, TALUKS_BY_DISTRICT
from locations.models import LocationDistrict, LocationTaluk


class Command(BaseCommand):
    help = 'Seed official Karnataka districts and taluks. No coordinates. No villages.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        created_districts = 0
        created_taluks = 0
        for name, _aliases in DISTRICT_RECORDS:
            if dry:
                created_districts += 1
                created_taluks += len(TALUKS_BY_DISTRICT[name])
                continue
            district, made = LocationDistrict.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name)},
            )
            if made:
                created_districts += 1
            for taluk_name, _taluk_aliases in TALUKS_BY_DISTRICT[name]:
                _taluk, made_taluk = LocationTaluk.objects.get_or_create(
                    district=district,
                    name=taluk_name,
                )
                if made_taluk:
                    created_taluks += 1
        self.stdout.write(
            f'districts={created_districts} taluks={created_taluks} dry_run={dry}'
        )
