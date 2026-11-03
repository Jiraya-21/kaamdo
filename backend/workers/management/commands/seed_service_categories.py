"""Ensure the public Daily Services category list exists."""

from django.core.management.base import BaseCommand

from workers.models import ServiceCategory

# Keep in sync with frontend/assets/js/utils/images.js CATEGORY_SLUGS.
DEFAULT_CATEGORIES = (
    ('plumber', 'Plumber'),
    ('electrician', 'Electrician'),
    ('house-clean', 'House cleaning'),
    ('painter', 'Painter'),
    ('ac-repair', 'AC repair'),
    ('washroom-cleaning', 'Washroom cleaning'),
    ('agriculture-equipment-renting', 'Agriculture equipment renting'),
)


class Command(BaseCommand):
    help = 'Create or reactivate the standard Daily Services categories.'

    def handle(self, *args, **options):
        created = 0
        for slug, name in DEFAULT_CATEGORIES:
            category, was_created = ServiceCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                changed = False
                if not category.is_active:
                    category.is_active = True
                    changed = True
                if category.name != name:
                    category.name = name
                    changed = True
                if changed:
                    category.save()
        self.stdout.write(self.style.SUCCESS(
            f'Service categories ready ({len(DEFAULT_CATEGORIES)}). New: {created}.'
        ))
