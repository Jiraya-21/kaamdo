"""
Load sample listings for first-phase testing (Bidar base data).

Safe to re-run: fixed phone numbers are updated in place.
Does not lock the product to Bidar — other districts stay selectable.
Strips old "[Demo] " title prefixes on re-seed.
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from accounts.models import AccountCapability, Capability
from equipment.models import EquipmentListing, FeeStatus, ListingStatus, PricingBasis
from jobs.models import (
    AgriculturalJob,
    EmployerProfile,
    Job,
    PostingStatus,
    ReviewStatus,
    WagePeriod,
    WorkType,
)
from workers.identity import ensure_kaamdo_worker_id
from workers.models import (
    ServiceCategory,
    ServiceProviderVerification,
    WorkerProfile,
)

User = get_user_model()

FIRST_AREA_DISTRICT = 'Bidar'
FIRST_AREA_LOCALITY = 'Town centre'
LEGACY_DEMO_PREFIX = '[Demo] '
SAMPLE_LAT = Decimal('17.913300')
SAMPLE_LNG = Decimal('77.530200')
DEMO_SEED_DIR = Path(settings.BASE_DIR) / 'media' / 'demo_seed'

# Fixed phones so re-seed is idempotent. Password for local/exhibition login only.
SEED_PASSWORD = 'DemoPass!234'
SEED_ACCOUNTS = {
    'plumber': {
        'phone': '9000005001',
        'first': 'Ravi',
        'last': 'Plumber',
        'caps': [Capability.SERVICE_PROVIDER],
        'bio': 'Plumber for Bidar and nearby areas.',
        'category_slugs': ['plumber'],
        'skills': ['Plumbing', 'Tap repair'],
        'rate': Decimal('300.00'),
        'photo': 'plumber',
    },
    'electrician': {
        'phone': '9000005002',
        'first': 'Suresh',
        'last': 'Electric',
        'caps': [Capability.SERVICE_PROVIDER],
        'bio': 'Electrician for Bidar and nearby areas.',
        'category_slugs': ['electrician'],
        'skills': ['Wiring', 'Fan repair'],
        'rate': Decimal('350.00'),
        'photo': 'electrician',
    },
    'cleaner': {
        'phone': '9000005003',
        'first': 'Lakshmi',
        'last': 'Clean',
        'caps': [Capability.SERVICE_PROVIDER],
        'bio': 'House cleaning for Bidar and nearby areas.',
        'category_slugs': ['house-clean'],
        'skills': ['House cleaning'],
        'rate': Decimal('250.00'),
        'photo': 'cleaner',
    },
    'employer': {
        'phone': '9000005004',
        'first': 'Anand',
        'last': 'Hire',
        'caps': [Capability.EMPLOYER, Capability.AGRICULTURAL_EMPLOYER],
    },
    'equip_owner': {
        'phone': '9000005005',
        'first': 'Manju',
        'last': 'Tractor',
        'caps': [Capability.EQUIPMENT_OWNER],
    },
}


class Command(BaseCommand):
    help = (
        'Seed Bidar sample workers, jobs, farm posts, and equipment '
        'so exhibition and testing pages are not empty.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=SEED_PASSWORD,
            help='Password set on sample accounts (local / exhibition use).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.core.management import call_command

        call_command('seed_service_categories')
        password = options['password']
        users = {}
        for key, spec in SEED_ACCOUNTS.items():
            users[key] = self._user(spec, password)

        for key in ('plumber', 'electrician', 'cleaner'):
            self._worker(users[key], SEED_ACCOUNTS[key])

        self._employer_profiles(users['employer'])
        self._jobs(users['employer'])
        self._farm_jobs(users['employer'])
        self._equipment(users['equip_owner'])

        self.stdout.write(self.style.SUCCESS(
            f'Sample data ready for {FIRST_AREA_DISTRICT} '
            f'(other districts stay open). '
            f'Logins: 9000005001–9000005005 / password from --password.'
        ))

    def _user(self, spec, password):
        phone = spec['phone']
        user, _created = User.objects.get_or_create(
            username=phone,
            defaults={
                'phone_number': phone,
                'first_name': spec['first'],
                'last_name': spec['last'],
                'active_mode': spec['caps'][0],
            },
        )
        user.phone_number = phone
        user.first_name = spec['first']
        user.last_name = spec['last']
        user.set_password(password)
        user.is_active = True
        user.save()
        for code in spec['caps']:
            AccountCapability.objects.get_or_create(user=user, code=code)
        Token.objects.get_or_create(user=user)
        return user

    def _worker(self, user, spec):
        profile, _ = WorkerProfile.objects.update_or_create(
            user=user,
            defaults={
                'bio': spec['bio'],
                'service_rate': spec['rate'],
                'pricing_basis': WorkerProfile.PricingBasis.DAILY,
                'district': FIRST_AREA_DISTRICT,
                'locality': FIRST_AREA_LOCALITY,
                'latitude': SAMPLE_LAT,
                'longitude': SAMPLE_LNG,
                'service_radius_km': 20,
                'availability': WorkerProfile.Availability.AVAILABLE,
                'publication_status': WorkerProfile.PublicationStatus.PUBLISHED,
                'experience_years': 5,
            },
        )
        from workers.models import Skill

        skills = []
        for name in spec['skills']:
            skill, _ = Skill.objects.get_or_create(name=name)
            skills.append(skill)
        profile.skills.set(skills)
        categories = []
        for slug in spec['category_slugs']:
            category = ServiceCategory.objects.filter(slug=slug, is_active=True).first()
            if category is None:
                category, _ = ServiceCategory.objects.get_or_create(
                    slug=slug,
                    defaults={'name': slug.replace('-', ' ').title(), 'is_active': True},
                )
            categories.append(category)
        if categories:
            profile.service_categories.set(categories)
        ServiceProviderVerification.objects.update_or_create(
            user=user,
            defaults={
                'status': ServiceProviderVerification.Status.APPROVED,
                'reviewed_at': timezone.now(),
                'applicant_note': 'Seed approval',
            },
        )
        ensure_kaamdo_worker_id(profile)
        self._attach_image(profile, 'photo', DEMO_SEED_DIR / 'workers' / f"{spec.get('photo', '')}.jpg")

    def _attach_image(self, instance, field_name, source_path):
        if not source_path or not Path(source_path).exists():
            return
        field = getattr(instance, field_name)
        with Path(source_path).open('rb') as handle:
            field.save(Path(source_path).name, File(handle), save=True)

    def _employer_profiles(self, user):
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        for domain in (
            EmployerProfile.Domain.ORDINARY,
            EmployerProfile.Domain.AGRICULTURAL,
        ):
            EmployerProfile.objects.update_or_create(
                user=user,
                domain=domain,
                defaults={
                    'full_name': full_name,
                    'party_type': EmployerProfile.PartyType.INDIVIDUAL,
                    'status': EmployerProfile.Status.APPROVED,
                    'submitted_at': timezone.now(),
                    'reviewed_at': timezone.now(),
                },
            )

    def _find_or_init(self, model, poster_field, poster, title):
        obj = model.objects.filter(**{poster_field: poster, 'title': title}).first()
        if obj is None:
            obj = model.objects.filter(
                **{poster_field: poster, 'title': f'{LEGACY_DEMO_PREFIX}{title}'},
            ).first()
        if obj is None:
            return model(**{poster_field: poster, 'title': title})
        obj.title = title
        return obj

    def _jobs(self, poster):
        samples = [
            ('Shop helper needed', 'Help in a small shop.', WorkType.PART_TIME, Decimal('400.00')),
            ('Driver for local trips', 'Local Bidar trips.', WorkType.TEMPORARY, Decimal('600.00')),
            ('Cook for canteen', 'Simple meals for a small canteen.', WorkType.FULL_TIME, Decimal('500.00')),
        ]
        for title, description, work_type, wage in samples:
            job = self._find_or_init(Job, 'poster', poster, title)
            job.description = description
            job.district = FIRST_AREA_DISTRICT
            job.locality = FIRST_AREA_LOCALITY
            job.wage_amount = wage
            job.wage_period = WagePeriod.DAILY
            job.wage_negotiable = True
            job.headcount = 2
            job.work_type = work_type
            job.review_status = ReviewStatus.APPROVED
            job.reviewed_at = timezone.now()
            job.status = PostingStatus.PUBLISHED
            job.save()

    def _farm_jobs(self, poster):
        samples = [
            ('Paddy field helpers', 'Short farm work for the season.', Decimal('450.00')),
            ('Sugarcane cutting help', 'Seasonal farm help needed.', Decimal('550.00')),
        ]
        for title, description, wage in samples:
            job = self._find_or_init(AgriculturalJob, 'poster', poster, title)
            job.description = description
            job.district = FIRST_AREA_DISTRICT
            job.locality = FIRST_AREA_LOCALITY
            job.wage_amount = wage
            job.wage_period = WagePeriod.DAILY
            job.wage_negotiable = False
            job.headcount = 5
            job.working_hours = '8am to 4pm'
            job.review_status = ReviewStatus.APPROVED
            job.reviewed_at = timezone.now()
            job.status = PostingStatus.PUBLISHED
            job.save()

    def _equipment(self, owner):
        samples = [
            ('Tractor with cultivator', 'Half-day or full-day hire.', Decimal('2500.00'), True, 'tractor'),
            ('Water pump set', 'For field irrigation.', Decimal('800.00'), False, 'pump'),
            ('Mini tiller', 'Small plot work.', Decimal('1200.00'), False, 'tiller'),
        ]
        for title, description, rate, operator, photo_key in samples:
            listing = self._find_or_init(EquipmentListing, 'owner', owner, title)
            listing.description = description
            listing.district = FIRST_AREA_DISTRICT
            listing.locality = FIRST_AREA_LOCALITY
            listing.pricing_basis = PricingBasis.DAILY
            listing.rate = rate
            listing.operator_included = operator
            listing.availability_note = 'Available this week'
            listing.fee_status = FeeStatus.WAIVED
            listing.fee_note = 'Waived for exhibition seed'
            listing.status = ListingStatus.PUBLISHED
            listing.save()
            self._attach_image(listing, 'photo', DEMO_SEED_DIR / 'equipment' / f'{photo_key}.jpg')
