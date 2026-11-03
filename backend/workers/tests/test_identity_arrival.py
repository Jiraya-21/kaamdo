"""Worker ID card and booking-specific arrival verification."""

from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.arrival import provider_signals_arrival
from workers.identity import ensure_kaamdo_worker_id, worker_identity_card
from workers.models import (
    DailyServiceArrivalChallenge,
    DailyServiceAssignmentEvent,
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    WorkerProfile,
)


class IdentityArrivalTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Plumber', slug='plumber-identity')
        self.customer = User.objects.create_user(
            username='cust-id',
            password='SafePass!234',
            phone_number='9000001401',
            first_name='Asha',
            last_name='Rao',
        )
        # Marketplace access without treating Customer as a required professional role.
        AccountCapability.objects.create(user=self.customer, code=Capability.JOB_SEEKER)
        self.customer_token = Token.objects.create(user=self.customer)
        self.provider = self.make_provider('9000001402', 'Ravi', 'Kumar')
        self.other = self.make_provider('9000001403', 'Other', 'Worker')

    def make_provider(self, phone, first, last):
        user = User.objects.create_user(
            username=f'prov-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name=first,
            last_name=last,
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=user,
            bio='Household plumbing.',
            service_rate=Decimal('150.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Bengaluru Urban',
            locality='Centre',
            latitude=Decimal('12.970000'),
            longitude=Decimal('77.590000'),
            service_radius_km=20,
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )
        profile.service_categories.add(self.category)
        ServiceProviderVerification.objects.create(
            user=user,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        ensure_kaamdo_worker_id(profile)
        return {
            'user': user,
            'profile': profile,
            'token': Token.objects.create(user=user),
        }

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def assign_request(self):
        record = DailyServiceRequest.objects.create(
            category=self.category,
            customer=self.customer,
            description='Kitchen tap leak.',
            latitude=Decimal('12.970000'),
            longitude=Decimal('77.590000'),
            radius_km=15,
            status=DailyServiceRequest.Status.OFFERING,
        )
        offer = ServiceOffer.objects.create(
            request=record,
            profile=self.provider['profile'],
            state=ServiceOffer.State.OFFERED,
        )
        self.auth(self.provider['token'])
        accepted = self.client.post(
            f'/api/v1/workers/daily-offers/{offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.assertEqual(accepted.status_code, 200)
        record.refresh_from_db()
        return record

    def test_provider_without_customer_capability_can_create_daily_request(self):
        self.auth(self.provider['token'])
        response = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': self.category.id,
                'description': 'Need an electrician for a fan.',
                'latitude': '12.970000',
                'longitude': '77.590000',
                'radius_km': 15,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], DailyServiceRequest.Status.DRAFT)
        self.assertTrue(
            DailyServiceRequest.objects.filter(
                customer=self.provider['user'],
                description='Need an electrician for a fan.',
            ).exists()
        )

    def test_job_seeker_without_customer_capability_can_list_and_create(self):
        self.auth(self.customer_token)
        listed = self.client.get('/api/v1/workers/daily-requests/mine/')
        self.assertEqual(listed.status_code, 200)
        created = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': self.category.id,
                'description': 'Fix bathroom pipe.',
                'latitude': '12.970000',
                'longitude': '77.590000',
                'radius_km': 20,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)

    def test_worker_id_card_has_no_invented_ratings(self):
        card = worker_identity_card(self.provider['profile'])
        self.assertTrue(str(card['worker_id']).startswith('KD'))
        self.assertEqual(card['display_name'], 'Ravi Kumar')
        self.assertTrue(card['identity_verified'])
        self.assertFalse(card['skill_verified'])
        self.assertFalse(card['qualification_verified'])
        self.assertIsNone(card['rating_average'])
        self.assertIsNone(card['review_count'])
        self.assertEqual(card['completed_jobs'], 0)

    def test_arrival_requires_customer_code_not_provider_click(self):
        record = self.assign_request()
        self.auth(self.provider['token'])
        signal = self.client.post(f'/api/v1/workers/daily-requests/{record.pk}/arrival/signal/')
        self.assertEqual(signal.status_code, 200, signal.data)
        code = signal.data['code']
        self.assertEqual(len(code), 6)
        record.refresh_from_db()
        self.assertEqual(record.status, DailyServiceRequest.Status.ASSIGNED)
        self.assertIsNone(record.arrival_verified_at)

        self.auth(self.other['token'])
        blocked = self.client.post(
            f'/api/v1/workers/daily-requests/{record.pk}/arrival/verify/',
            {'code': code},
            format='json',
        )
        self.assertEqual(blocked.status_code, 404)

        self.auth(self.customer_token)
        wrong = self.client.post(
            f'/api/v1/workers/daily-requests/{record.pk}/arrival/verify/',
            {'code': '000000'},
            format='json',
        )
        self.assertEqual(wrong.status_code, 400)

        verified = self.client.post(
            f'/api/v1/workers/daily-requests/{record.pk}/arrival/verify/',
            {'code': code},
            format='json',
        )
        self.assertEqual(verified.status_code, 200, verified.data)
        self.assertEqual(verified.data['status'], DailyServiceRequest.Status.IN_PROGRESS)
        self.assertIsNotNone(verified.data['arrival_verified_at'])
        self.assertEqual(verified.data['worker_identity']['worker_id'], self.provider['profile'].kaamdo_worker_id)
        self.assertNotIn('phone_number', verified.data['worker_identity'])

        completed = self.client.post(
            f'/api/v1/workers/daily-requests/{record.pk}/complete/',
            {},
            format='json',
        )
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertEqual(completed.data['status'], DailyServiceRequest.Status.COMPLETED)
        self.assertEqual(
            completed.data['assigned_profile']['id'],
            self.provider['profile'].pk,
        )
        self.assertTrue(
            DailyServiceAssignmentEvent.objects.filter(
                request=record,
                event=DailyServiceAssignmentEvent.Event.ARRIVAL_VERIFIED,
            ).exists()
        )

    def test_enable_customer_capability_is_rejected(self):
        self.auth(self.provider['token'])
        response = self.client.post(
            '/api/v1/auth/capabilities/',
            {'capability': 'customer'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_replacement_clears_arrival_and_records_history(self):
        record = self.assign_request()
        provider_signals_arrival(record, provider_user=self.provider['user'])
        self.assertTrue(
            DailyServiceArrivalChallenge.objects.filter(
                request=record,
                verified_at__isnull=True,
                superseded_at__isnull=True,
            ).exists()
        )

        # Authorized replacement before visit start: cancel assigned worker, then reassign.
        record.transition_to(DailyServiceRequest.Status.WORKER_CANCELLED)
        record.transition_to(DailyServiceRequest.Status.OFFERING)
        record.transition_to(
            DailyServiceRequest.Status.ASSIGNED,
            assigned_profile=self.other['profile'],
        )
        record.refresh_from_db()
        self.assertEqual(record.assigned_profile_id, self.other['profile'].pk)
        self.assertIsNone(record.arrival_verified_at)
        self.assertTrue(
            DailyServiceAssignmentEvent.objects.filter(
                request=record,
                event=DailyServiceAssignmentEvent.Event.WORKER_CANCELLED,
            ).exists()
        )
        self.assertTrue(
            DailyServiceAssignmentEvent.objects.filter(
                request=record,
                profile=self.other['profile'],
                event=DailyServiceAssignmentEvent.Event.ASSIGNED,
            ).exists()
        )
        self.assertFalse(
            DailyServiceArrivalChallenge.objects.filter(
                request=record,
                verified_at__isnull=True,
                superseded_at__isnull=True,
            ).exists()
        )
