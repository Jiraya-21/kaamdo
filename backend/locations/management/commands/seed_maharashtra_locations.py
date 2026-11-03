"""
Load official Maharashtra districts and taluks into the locations tables.

Does not invent villages, streets, PIN codes, or coordinates.
Mumbai City has no taluka rows in the official table.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from locations.maharashtra import DISTRICT_RECORDS, TALUKS_BY_DISTRICT
from locations.models import LocationDistrict, LocationTaluk


class Command(BaseCommand):
    help = 'Seed official Maharashtra districts and taluks. No coordinates. No villages.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        created_districts = 0
        created_taluks = 0
        for name, _aliases in DISTRICT_RECORDS:
            taluks = TALUKS_BY_DISTRICT[name]
            if dry:
                created_districts += 1
                created_taluks += len(taluks)
                continue
            district, made = LocationDistrict.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name)},
            )
            if made:
                created_districts += 1
            for taluk_name, _taluk_aliases in taluks:
                _taluk, made_taluk = LocationTaluk.objects.get_or_create(
                    district=district,
                    name=taluk_name,
                )
                if made_taluk:
                    created_taluks += 1
        self.stdout.write(
            f'districts={created_districts} taluks={created_taluks} dry_run={dry}'
        )
