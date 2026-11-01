"""Employer and job-seeker account lists. Ownership comes from the signed-in user."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, OtpPurpose, PhoneVerification, User
from jobs.models import AgriculturalJob, Job, JobApplication, PostingStatus, ReviewStatus
from notifications.models import InAppNotification


class JobAccountTests(APITestCase):
    def make_user(self, phone, capabilities, first_name='Asha', last_name='Rao'):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
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

    def test_employer_sees_only_their_jobs_including_drafts(self):
        employer, employer_token = self.make_user('9000000811', [Capability.EMPLOYER], 'Ravi', 'Kumar')
        other, other_token = self.make_user('9000000812', [Capability.EMPLOYER])
        seeker, seeker_token = self.make_user('9000000813', [Capability.JOB_SEEKER])
        self.verify_phone(employer)
        self.verify_phone(other)
        self.auth(employer_token)
        own = self.client.post('/api/v1/jobs/', self.job_payload(title='Own role'), format='json')
        self.auth(other_token)
        theirs = self.client.post('/api/v1/jobs/', self.job_payload(title='Other role'), format='json')

        self.auth(employer_token)
        listed = self.client.get(f'/api/v1/jobs/mine/?poster={other.id}')
        self.client.credentials()
        public = self.client.get('/api/v1/jobs/')
        anonymous = self.client.get('/api/v1/jobs/mine/')
        self.auth(seeker_token)
        denied = self.client.get('/api/v1/jobs/mine/')

        self.assertEqual(own.status_code, 201)
        self.assertEqual(own.data['status'], 'draft')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['count'], 1)
        self.assertEqual(listed.data['results'][0]['id'], own.data['id'])
        self.assertEqual(listed.data['results'][0]['title'], 'Own role')
        self.assertNotIn(theirs.data['id'], [row['id'] for row in listed.data['results']])
        self.assertEqual(public.data['count'], 0)
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(denied.status_code, 403)

    def test_application_lists_stay_with_their_owner_and_hide_phone_numbers(self):
        employer, employer_token = self.make_user('9000000821', [Capability.EMPLOYER], 'Ravi', 'Kumar')
        seeker, seeker_token = self.make_user('9000000822', [Capability.JOB_SEEKER], 'Meera', 'Naik')
        other, other_token = self.make_user('9000000823', [Capability.JOB_SEEKER], 'Other', 'Seeker')
        self.verify_phone(employer)
        self.verify_phone(seeker, OtpPurpose.JOB_APPLICATION)
        self.auth(employer_token)
        created = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        job = Job.objects.get(pk=created.data['id'])
        job.status = PostingStatus.PUBLISHED
        job.review_status = ReviewStatus.APPROVED
        job.save(update_fields=['status', 'review_status'])

        self.auth(seeker_token)
        applied = self.client.post(
            f"/api/v1/jobs/{job.pk}/applications/",
            {'message': 'I can start Monday.'},
            format='json',
        )
        mine = self.client.get('/api/v1/jobs/applications/')
        withdrawn = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )

        self.auth(other_token)
        stolen = self.client.get('/api/v1/jobs/applications/')
        stolen_patch = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'submitted'},
            format='json',
        )
        self.auth(employer_token)
        poster = self.client.get(f'/api/v1/jobs/{job.pk}/applications/')
        employer_patch = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )
        self.client.credentials()
        anonymous = self.client.get('/api/v1/jobs/applications/')

        self.assertEqual(applied.status_code, 201)
        self.assertEqual(applied.data['applicant_name'], 'Meera Naik')
        self.assertEqual(applied.data['job_title'], 'Shop assistant')
        self.assertNotIn('phone_number', applied.data)
        self.assertNotIn('9000000822', str(applied.data))
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(mine.data['results'][0]['job_district'], 'Mandya')
        self.assertEqual(mine.data['results'][0]['job_locality'], 'Town centre')
        self.assertEqual(withdrawn.status_code, 200)
        self.assertEqual(withdrawn.data['status'], 'withdrawn')
        self.assertEqual(JobApplication.objects.get(pk=applied.data['id']).status, 'withdrawn')
        self.assertEqual(stolen.data['count'], 0)
        self.assertEqual(stolen_patch.status_code, 404)
        self.assertEqual(poster.status_code, 200)
        self.assertEqual(poster.data['results'][0]['applicant_name'], 'Meera Naik')
        self.assertEqual(poster.data['results'][0]['message'], 'I can start Monday.')
        self.assertNotIn('9000000822', str(poster.data))
        self.assertEqual(employer_patch.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(Decimal('500.00'), job.wage_amount)

    def test_farm_poster_lists_only_their_posts(self):
        poster, poster_token = self.make_user('9000000831', [Capability.AGRICULTURAL_EMPLOYER])
        employer, employer_token = self.make_user('9000000832', [Capability.EMPLOYER])
        self.verify_phone(poster)
        self.verify_phone(employer)
        self.auth(poster_token)
        created = self.client.post(
            '/api/v1/jobs/agricultural/',
            self.job_payload(title='Paddy harvest'),
            format='json',
        )
        mine = self.client.get('/api/v1/jobs/agricultural/mine/')
        self.auth(employer_token)
        denied = self.client.get('/api/v1/jobs/agricultural/mine/')
        self.client.credentials()
        public = self.client.get('/api/v1/jobs/agricultural/')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(mine.data['results'][0]['title'], 'Paddy harvest')
        self.assertEqual(AgriculturalJob.objects.get(pk=created.data['id']).poster_id, poster.id)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(public.data['count'], 0)

    def test_farm_applications_stay_with_their_owner(self):
        poster, poster_token = self.make_user('9000000841', [Capability.AGRICULTURAL_EMPLOYER], 'Ravi', 'Kumar')
        other_poster, other_poster_token = self.make_user('9000000842', [Capability.AGRICULTURAL_EMPLOYER])
        employer, employer_token = self.make_user('9000000843', [Capability.EMPLOYER])
        worker, worker_token = self.make_user('9000000844', [Capability.AGRICULTURAL_WORKER], 'Meera', 'Naik')
        other_worker, other_worker_token = self.make_user('9000000845', [Capability.AGRICULTURAL_WORKER])
        self.verify_phone(poster)
        self.verify_phone(worker, OtpPurpose.AGRICULTURAL_APPLICATION)
        self.auth(poster_token)
        created = self.client.post(
            '/api/v1/jobs/agricultural/',
            self.job_payload(title='Paddy harvest'),
            format='json',
        )
        job = AgriculturalJob.objects.get(pk=created.data['id'])
        job.status = PostingStatus.PUBLISHED
        job.review_status = ReviewStatus.APPROVED
        job.save(update_fields=['status', 'review_status'])

        self.auth(worker_token)
        applied = self.client.post(
            f'/api/v1/jobs/agricultural/{job.pk}/applications/',
            {'message': 'I have harvest experience.'},
            format='json',
        )
        mine = self.client.get('/api/v1/jobs/agricultural/applications/')
        self.auth(other_worker_token)
        stolen = self.client.get('/api/v1/jobs/agricultural/applications/')
        stolen_patch = self.client.patch(
            f"/api/v1/jobs/agricultural/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )
        self.auth(employer_token)
        ordinary = self.client.get(f'/api/v1/jobs/agricultural/{job.pk}/applications/')
        ordinary_mine = self.client.get('/api/v1/jobs/agricultural/applications/')
        self.auth(other_poster_token)
        other_list = self.client.get(f'/api/v1/jobs/agricultural/{job.pk}/applications/')
        self.auth(poster_token)
        poster_list = self.client.get(f'/api/v1/jobs/agricultural/{job.pk}/applications/')

        self.assertEqual(applied.status_code, 201)
        self.assertEqual(applied.data['applicant_name'], 'Meera Naik')
        self.assertNotIn('phone_number', applied.data)
        self.assertNotIn('9000000844', str(applied.data))
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(stolen.status_code, 200)
        self.assertEqual(stolen.data['count'], 0)
        self.assertEqual(stolen_patch.status_code, 404)
        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(ordinary_mine.status_code, 403)
        self.assertEqual(other_list.status_code, 403)
        self.assertEqual(poster_list.status_code, 200)
        self.assertEqual(poster_list.data['count'], 1)
        self.assertEqual(poster_list.data['results'][0]['message'], 'I have harvest experience.')
        self.assertNotIn('9000000844', str(poster_list.data))

    def test_employer_can_accept_or_reject_a_submitted_application(self):
        employer, employer_token = self.make_user('9000000851', [Capability.EMPLOYER], 'Ravi', 'Kumar')
        other, other_token = self.make_user('9000000852', [Capability.EMPLOYER])
        seeker, seeker_token = self.make_user('9000000853', [Capability.JOB_SEEKER], 'Meera', 'Naik')
        farm_poster, farm_token = self.make_user('9000000854', [Capability.AGRICULTURAL_EMPLOYER])
        farm_worker, farm_worker_token = self.make_user(
            '9000000855',
            [Capability.AGRICULTURAL_WORKER],
            'Latha',
            'Gowda',
        )
        self.verify_phone(employer)
        self.verify_phone(seeker, OtpPurpose.JOB_APPLICATION)
        self.verify_phone(farm_poster)
        self.verify_phone(farm_worker, OtpPurpose.AGRICULTURAL_APPLICATION)

        self.auth(employer_token)
        created = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        job = Job.objects.get(pk=created.data['id'])
        job.status = PostingStatus.PUBLISHED
        job.review_status = ReviewStatus.APPROVED
        job.save(update_fields=['status', 'review_status'])

        self.auth(seeker_token)
        applied = self.client.post(
            f'/api/v1/jobs/{job.pk}/applications/',
            {'message': 'I can start Monday.', 'status': 'accepted'},
            format='json',
        )
        self.assertEqual(applied.status_code, 201)
        self.assertEqual(applied.data['status'], 'submitted')
        self_accept = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        decision_as_seeker = self.client.patch(
            f"/api/v1/jobs/{job.pk}/applications/{applied.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )

        self.auth(other_token)
        stolen = self.client.patch(
            f"/api/v1/jobs/{job.pk}/applications/{applied.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )

        self.auth(employer_token)
        accepted = self.client.patch(
            f"/api/v1/jobs/{job.pk}/applications/{applied.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        again = self.client.patch(
            f"/api/v1/jobs/{job.pk}/applications/{applied.data['id']}/",
            {'status': 'rejected'},
            format='json',
        )
        self.auth(seeker_token)
        late_withdraw = self.client.patch(
            f"/api/v1/jobs/applications/{applied.data['id']}/",
            {'status': 'withdrawn'},
            format='json',
        )
        notes = self.client.get('/api/v1/notifications/')

        self.auth(farm_token)
        farm_created = self.client.post(
            '/api/v1/jobs/agricultural/',
            self.job_payload(title='Paddy harvest'),
            format='json',
        )
        farm_job = AgriculturalJob.objects.get(pk=farm_created.data['id'])
        farm_job.status = PostingStatus.PUBLISHED
        farm_job.review_status = ReviewStatus.APPROVED
        farm_job.save(update_fields=['status', 'review_status'])
        self.auth(farm_worker_token)
        farm_applied = self.client.post(
            f'/api/v1/jobs/agricultural/{farm_job.pk}/applications/',
            {'message': 'I have harvest experience.'},
            format='json',
        )
        self.auth(farm_token)
        rejected = self.client.patch(
            f'/api/v1/jobs/agricultural/{farm_job.pk}/applications/{farm_applied.data["id"]}/',
            {'status': 'rejected'},
            format='json',
        )

        self.assertEqual(self_accept.status_code, 400)
        self.assertEqual(decision_as_seeker.status_code, 403)
        self.assertEqual(stolen.status_code, 404)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['status'], 'accepted')
        self.assertNotIn('9000000853', str(accepted.data))
        self.assertEqual(again.status_code, 400)
        self.assertEqual(late_withdraw.status_code, 400)
        self.assertEqual(JobApplication.objects.get(pk=applied.data['id']).status, 'accepted')
        self.assertEqual(notes.status_code, 200)
        self.assertEqual(len(notes.data), 1)
        self.assertEqual(notes.data[0]['kind'], 'job_application_accepted')
        self.assertNotIn('9000000853', str(notes.data))
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data['status'], 'rejected')
        self.assertEqual(
            InAppNotification.objects.filter(kind='farm_application_rejected').count(),
            1,
        )

    def test_applicant_cannot_delete_an_accepted_application(self):
        employer, employer_token = self.make_user('9000000861', [Capability.EMPLOYER])
        seeker, seeker_token = self.make_user('9000000862', [Capability.JOB_SEEKER])
        self.verify_phone(employer)
        self.verify_phone(seeker, OtpPurpose.JOB_APPLICATION)
        self.auth(employer_token)
        created = self.client.post('/api/v1/jobs/', self.job_payload(), format='json')
        job = Job.objects.get(pk=created.data['id'])
        job.status = PostingStatus.PUBLISHED
        job.review_status = ReviewStatus.APPROVED
        job.save(update_fields=['status', 'review_status'])
        self.auth(seeker_token)
        applied = self.client.post(
            f'/api/v1/jobs/{job.pk}/applications/',
            {'message': 'I can start Monday.'},
            format='json',
        )
        self.auth(employer_token)
        accepted = self.client.patch(
            f"/api/v1/jobs/{job.pk}/applications/{applied.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        self.auth(seeker_token)
        deleted = self.client.delete(f"/api/v1/jobs/applications/{applied.data['id']}/")
        again = self.client.post(
            f'/api/v1/jobs/{job.pk}/applications/',
            {'message': 'Applying again after delete.'},
            format='json',
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(deleted.status_code, 405)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(JobApplication.objects.filter(pk=applied.data['id']).count(), 1)

    def test_employer_can_close_own_published_job(self):
        employer, employer_token = self.make_user('9000000881', [Capability.EMPLOYER], 'Ravi', 'Kumar')
        other, other_token = self.make_user('9000000882', [Capability.EMPLOYER])
        self.verify_phone(employer)
        self.verify_phone(other)
        self.auth(employer_token)
        created = self.client.post('/api/v1/jobs/', self.job_payload(title='Own close'), format='json')
        job = Job.objects.get(pk=created.data['id'])
        job.status = PostingStatus.PUBLISHED
        job.review_status = ReviewStatus.APPROVED
        job.save(update_fields=['status', 'review_status'])
        self.auth(other_token)
        denied = self.client.patch(
            f'/api/v1/jobs/{job.pk}/',
            {'status': 'closed'},
            format='json',
        )
        self.auth(employer_token)
        closed = self.client.patch(
            f'/api/v1/jobs/{job.pk}/',
            {'status': 'closed'},
            format='json',
        )
        job.refresh_from_db()
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.data['status'], 'closed')
        self.assertEqual(job.status, PostingStatus.CLOSED)
