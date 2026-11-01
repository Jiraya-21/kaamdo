"""
Tests for ordinary jobs and agricultural hiring.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, OtpPurpose, PhoneVerification, User
from jobs.models import AgriculturalJob, Job, JobApplication, PostingStatus, ReviewStatus


class JobApiTests(APITestCase):
    def make_user(self, phone, capabilities, active_mode=None, first_name='Asha', last_name='Rao'):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
            active_mode=active_mode or capabilities[0],
        )
        for code in capabilities:
            AccountCapability.objects.create(user=user, code=code)
        return user, Token.objects.create(user=user)

    def verify_phone(self, user, purpose=OtpPurpose.ACCOUNT):
        PhoneVerification.objects.create(
            user=user,
            phone_number=user.phone_number,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(hours=2),
        )

    def approve_post(self, model, post_id):
        post = model.objects.get(pk=post_id)
        post.status = PostingStatus.PUBLISHED
        post.review_status = ReviewStatus.APPROVED
        post.save(update_fields=['status', 'review_status'])
        return post

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def job_payload(self, **overrides):
        data = {
            'title': 'Shop assistant',
            'description': 'Help customers and keep the counter.',
            'district': 'Mandya',
            'locality': 'Town centre',
            'wage_amount': '500.00',
            'wage_period': 'daily',
            'headcount': 1,
            'status': 'published',
        }
        data.update(overrides)
        return data

    def test_capability_controls_job_creation_not_active_mode_or_staff_flag(self):
        employer, employer_token = self.make_user(
            '9876543210',
            [Capability.EMPLOYER],
            active_mode=Capability.CUSTOMER,
            first_name='Basavaraj',
            last_name='Patil',
        )
        customer, customer_token = self.make_user(
            '9123456780',
            [Capability.CUSTOMER],
            active_mode=Capability.EMPLOYER,
        )
        self.verify_phone(employer)
        self.auth(employer_token)
        created = self.client.post(
            '/api/v1/jobs/',
            {**self.job_payload(), 'is_staff': True, 'poster': customer.id},
            format='json',
        )
        self.auth(customer_token)
        denied = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        employer.refresh_from_db()

        self.client.credentials()
        anonymous = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['poster_name'], 'Basavaraj Patil')
        self.assertFalse(employer.is_staff)
        self.assertEqual(Job.objects.get(pk=created.data['id']).poster_id, employer.id)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)

    def test_only_the_poster_can_change_a_job_and_drafts_stay_hidden(self):
        employer, employer_token = self.make_user('9876543210', [Capability.EMPLOYER], first_name='Ravi', last_name='Kumar')
        other, other_token = self.make_user('9123456780', [Capability.EMPLOYER])
        self.verify_phone(employer)
        self.auth(employer_token)
        published = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        self.approve_post(Job, published.data['id'])
        draft = self.client.post('/api/v1/jobs/', self.job_payload(title='Draft role', status='draft'), format='json')
        self.auth(other_token)
        stolen = self.client.patch(f"/api/v1/jobs/{published.data['id']}/", {'title': 'Taken'}, format='json')

        self.client.credentials()
        listing = self.client.get('/api/v1/jobs/')
        hidden = self.client.get(f"/api/v1/jobs/{draft.data['id']}/")
        visible = self.client.get(f"/api/v1/jobs/{published.data['id']}/")

        self.assertEqual(stolen.status_code, 403)
        self.assertEqual(listing.data['count'], 1)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(visible.status_code, 200)
        self.assertNotIn('9876543210', str(visible.data))
        self.assertNotIn('password', visible.data)

    def test_ordinary_and_agricultural_applications_stay_separate(self):
        employer, employer_token = self.make_user('9000000001', [Capability.EMPLOYER])
        farm_poster, farm_token = self.make_user('9000000002', [Capability.AGRICULTURAL_EMPLOYER])
        seeker, seeker_token = self.make_user('9000000003', [Capability.JOB_SEEKER])
        other_seeker, other_seeker_token = self.make_user('9000000005', [Capability.JOB_SEEKER])
        farm_worker, farm_worker_token = self.make_user('9000000004', [Capability.AGRICULTURAL_WORKER])
        self.verify_phone(employer)
        self.verify_phone(farm_poster)
        self.verify_phone(seeker, OtpPurpose.JOB_APPLICATION)
        self.verify_phone(farm_worker, OtpPurpose.AGRICULTURAL_APPLICATION)
        self.auth(employer_token)
        job = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        self.approve_post(Job, job.data['id'])
        blocked_farm = self.client.post('/api/v1/jobs/agricultural/', self.job_payload(), format='json')
        self.auth(farm_token)
        farm_job = self.client.post('/api/v1/jobs/agricultural/', self.job_payload(title='Paddy harvest'), format='json')
        self.approve_post(AgriculturalJob, farm_job.data['id'])
        blocked_ordinary = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')

        self.auth(seeker_token)
        applied = self.client.post(
            f"/api/v1/jobs/{job.data['id']}/applications/",
            {'message': 'I can start Monday.'},
            format='json',
        )
        duplicate = self.client.post(
            f"/api/v1/jobs/{job.data['id']}/applications/",
            {'message': 'Applying again.'},
            format='json',
        )
        cross = self.client.post(
            f"/api/v1/jobs/agricultural/{farm_job.data['id']}/applications/",
            {'message': 'I want farm work.'},
            format='json',
        )
        self.auth(farm_worker_token)
        farm_applied = self.client.post(
            f"/api/v1/jobs/agricultural/{farm_job.data['id']}/applications/",
            {'message': 'I have harvest experience.'},
            format='json',
        )
        ordinary_cross = self.client.post(
            f"/api/v1/jobs/{job.data['id']}/applications/",
            {'message': 'Ordinary job.'},
            format='json',
        )

        self.auth(seeker_token)
        others = self.client.get(f"/api/v1/jobs/{job.data['id']}/applications/")
        mine = self.client.get('/api/v1/jobs/applications/')
        self.auth(other_seeker_token)
        stolen = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )
        self.auth(farm_worker_token)
        cross_update = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )
        self.auth(employer_token)
        poster_list = self.client.get(f"/api/v1/jobs/{job.data['id']}/applications/")

        self.assertEqual(blocked_farm.status_code, 403)
        self.assertEqual(blocked_ordinary.status_code, 403)
        self.assertEqual(job.status_code, 201)
        self.assertEqual(farm_job.status_code, 201)
        self.assertEqual(applied.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(cross.status_code, 403)
        self.assertEqual(farm_applied.status_code, 201)
        self.assertEqual(ordinary_cross.status_code, 403)
        self.assertEqual(others.status_code, 403)
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(stolen.status_code, 404)
        self.assertEqual(cross_update.status_code, 403)
        self.assertEqual(poster_list.status_code, 200)
        self.assertEqual(poster_list.data['count'], 1)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(AgriculturalJob.objects.count(), 1)
        self.assertEqual(JobApplication.objects.count(), 1)

    def test_public_registration_still_cannot_grant_staff(self):
        response = self.client.post(
            '/api/v1/auth/register/',
            {
                'phone_number': '9988776655',
                'password': 'SafePass!234',
                'full_name': 'New Person',
                'capabilities': ['employer'],
                'is_staff': True,
                'is_superuser': True,
            },
            format='json',
        )
        user = User.objects.get(phone_number='9988776655')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotIn('is_staff', response.data['user'])
        self.assertIn('customer', user.capability_codes())

    def test_first_job_stays_hidden_until_a_reviewer_approves_it(self):
        employer, token = self.make_user('9000000091', [Capability.EMPLOYER])
        self.verify_phone(employer)
        self.auth(token)
        created = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        self.client.credentials()
        listing = self.client.get('/api/v1/jobs/')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['status'], 'draft')
        self.assertEqual(created.data['review_status'], 'pending')
        self.assertEqual(listing.data['count'], 0)

    def test_agricultural_end_date_cannot_be_before_start_date(self):
        poster, token = self.make_user('9000000092', [Capability.AGRICULTURAL_EMPLOYER])
        self.verify_phone(poster)
        self.auth(token)
        response = self.client.post(
            '/api/v1/jobs/agricultural/',
            self.job_payload(
                title='Paddy harvest',
                work_start='2026-12-20',
                work_end='2026-12-10',
            ),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AgriculturalJob.objects.count(), 0)
