"""Public job filters run before pagination."""

from decimal import Decimal

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User
from jobs.models import AgriculturalJob, Job, PostingStatus, ReviewStatus, WorkType


class PublicJobFilterTests(APITestCase):
    def make_user(self, phone):
        return User.objects.create_user(
            username=f'poster-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name='Poster',
            last_name='One',
        )

    def make_job(self, poster, **overrides):
        values = {
            'poster': poster,
            'title': 'Shop assistant',
            'description': 'Help at the counter.',
            'district': 'Mandya',
            'locality': 'Town centre',
            'wage_amount': Decimal('500.00'),
            'wage_period': 'daily',
            'headcount': 1,
            'work_type': WorkType.TEMPORARY,
            'status': PostingStatus.PUBLISHED,
            'review_status': ReviewStatus.APPROVED,
        }
        values.update(overrides)
        return Job.objects.create(**values)

    def test_work_type_district_and_text_cover_jobs_beyond_the_first_page(self):
        poster = self.make_user('9000000831')
        older = self.make_job(poster, title='Older shop role', work_type=WorkType.FULL_TIME)
        newer = self.make_job(
            poster,
            title='Field driver',
            description='Drive between villages.',
            district='Mysuru',
            locality='Hebbal',
            work_type=WorkType.PART_TIME,
        )
        hidden = self.make_job(
            poster,
            title='Hidden draft',
            work_type=WorkType.FULL_TIME,
            status=PostingStatus.DRAFT,
            review_status=ReviewStatus.PENDING,
        )

        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'PAGE_SIZE': 1}):
            unfiltered = self.client.get('/api/v1/jobs/')
            by_type = self.client.get('/api/v1/jobs/?work_type=full_time')
            by_district = self.client.get('/api/v1/jobs/?district=mysuru')
            by_text = self.client.get('/api/v1/jobs/?q=villages')
            rejected = self.client.get('/api/v1/jobs/?work_type=seasonal')

        self.assertEqual(unfiltered.status_code, 200)
        self.assertEqual(unfiltered.data['count'], 2)
        self.assertEqual(by_type.data['count'], 1)
        self.assertEqual(by_type.data['results'][0]['id'], older.id)
        self.assertEqual(by_district.data['results'][0]['id'], newer.id)
        self.assertEqual(by_text.data['results'][0]['id'], newer.id)
        self.assertEqual(rejected.status_code, 400)
        self.assertNotIn(hidden.id, [row['id'] for row in by_type.data['results']])
        self.assertNotIn('phone_number', by_type.data['results'][0])
        self.assertNotIn(poster.phone_number, str(by_type.data))

    def test_farm_list_filters_district_and_ignores_ordinary_work_type(self):
        poster = self.make_user('9000000832')
        harvest = AgriculturalJob.objects.create(
            poster=poster,
            title='Paddy harvest',
            description='Cutting and stacking.',
            district='Mandya',
            locality='Canal side',
            wage_amount=Decimal('600.00'),
            wage_period='daily',
            headcount=4,
            status=PostingStatus.PUBLISHED,
            review_status=ReviewStatus.APPROVED,
        )
        AgriculturalJob.objects.create(
            poster=poster,
            title='Other farm',
            description='Weeding.',
            district='Hassan',
            locality='Hill road',
            wage_negotiable=True,
            wage_period='daily',
            headcount=1,
            status=PostingStatus.PUBLISHED,
            review_status=ReviewStatus.APPROVED,
        )
        listed = self.client.get('/api/v1/jobs/agricultural/?district=Mandya&work_type=seasonal')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['count'], 1)
        self.assertEqual(listed.data['results'][0]['id'], harvest.id)
        self.assertNotIn(poster.phone_number, str(listed.data))
