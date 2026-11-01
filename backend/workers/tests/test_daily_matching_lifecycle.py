"""Offer batches, expiry, radius consent, and reassignment."""

from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.matching import advance_matching, process_due_matching
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    WorkerProfile,
)
from workers.tests.test_daily_service_matching import north_of


class MatchingLifecycleTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician-life')
        self.request = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-life@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        self.access_key = 'matching-lifecycle-access-key'
        self.request.set_access_key(self.access_key)
        self.request.save(update_fields=['access_key_hash'])
        self._phones = 9000002000
        self.staff = User.objects.create_user(
            username='staff-life',
            password='SafePass!234',
            phone_number='9000002099',
            is_staff=True,
        )
        self.staff_token = Token.objects.create(user=self.staff)

    def make_worker(self, kilometres=1, *, available=True, radius=40):
        self._phones += 1
        lat, lon = north_of(12, 77, kilometres)
        user = User.objects.create_user(
            username=f'worker-{self._phones}',
            password='SafePass!234',
            phone_number=str(self._phones),
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=user,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            latitude=lat,
            longitude=lon,
            service_radius_km=radius,
            availability=(
                WorkerProfile.Availability.AVAILABLE
                if available
                else WorkerProfile.Availability.UNAVAILABLE
            ),
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )
        profile.service_categories.add(self.category)
        ServiceProviderVerification.objects.create(
            user=user,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        return {
            'user': user,
            'profile': profile,
            'token': Token.objects.create(user=user),
        }

    def ready(self):
        self.request.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.request.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)

    def respond(self, worker, offer, decision):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {worker["token"].key}')
        return self.client.post(
            f'/api/v1/workers/daily-offers/{offer.pk}/respond/',
            {'decision': decision},
            format='json',
        )

    @override_settings(KAAMDO_MATCH_BATCH_SIZE=3, KAAMDO_MATCH_RADIUS_STAGES=(8, 15, 20))
    def test_first_batch_is_the_nearest_three(self):
        far = self.make_worker(7)
        mid = self.make_worker(4)
        near = self.make_worker(1)
        extra = self.make_worker(6)
        self.ready()
        result = advance_matching(self.request)
        self.request.refresh_from_db()
        offered = list(
            ServiceOffer.objects.filter(request=self.request).values_list('profile_id', flat=True)
        )
        self.assertEqual(self.request.status, DailyServiceRequest.Status.OFFERING)
        self.assertEqual(len(result.created_offer_ids), 3)
        self.assertIn(near['profile'].pk, offered)
        self.assertIn(mid['profile'].pk, offered)
        self.assertIn(extra['profile'].pk, offered)
        self.assertNotIn(far['profile'].pk, offered)

    @override_settings(KAAMDO_MATCH_BATCH_SIZE=1, KAAMDO_MATCH_OFFER_WINDOW_SECONDS=30)
    def test_expired_offer_is_rejected_and_the_next_worker_is_offered(self):
        first = self.make_worker(1)
        second = self.make_worker(2)
        self.ready()
        advance_matching(self.request)
        offer = ServiceOffer.objects.get(request=self.request, profile=first['profile'])
        past = timezone.now() - timedelta(seconds=40)
        offer.offered_at = past
        offer.expires_at = past
        offer.save(update_fields=['offered_at', 'expires_at'])
        late = self.respond(first, offer, 'accept')
        offer.refresh_from_db()
        self.request.refresh_from_db()
        self.assertEqual(late.status_code, 400)
        self.assertEqual(offer.state, ServiceOffer.State.EXPIRED)
        next_offer = ServiceOffer.objects.get(request=self.request, profile=second['profile'])
        self.assertEqual(next_offer.state, ServiceOffer.State.OFFERED)
        self.assertIsNone(self.request.assigned_profile_id)

    @override_settings(KAAMDO_MATCH_BATCH_SIZE=1)
    def test_decline_offers_the_next_eligible_worker(self):
        first = self.make_worker(1)
        second = self.make_worker(2)
        self.ready()
        advance_matching(self.request)
        first_offer = ServiceOffer.objects.get(request=self.request, profile=first['profile'])
        declined = self.respond(first, first_offer, 'decline')
        second_offer = ServiceOffer.objects.get(request=self.request, profile=second['profile'])
        self.request.refresh_from_db()
        self.assertEqual(declined.status_code, 200)
        self.assertEqual(self.request.status, DailyServiceRequest.Status.OFFERING)
        self.assertEqual(second_offer.state, ServiceOffer.State.OFFERED)

    @override_settings(KAAMDO_MATCH_BATCH_SIZE=3)
    def test_a_busy_provider_is_not_offered_a_second_request(self):
        worker = self.make_worker(1)
        other = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Other Guest',
            contact_email='other-life@example.com',
            description='A second fan.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        other.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        other.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        other.transition_to(DailyServiceRequest.Status.OFFERING)
        ServiceOffer.objects.create(request=other, profile=worker['profile'])
        self.ready()
        result = advance_matching(self.request)
        self.request.refresh_from_db()
        self.assertEqual(result.created_offer_ids, ())
        self.assertFalse(
            ServiceOffer.objects.filter(request=self.request, profile=worker['profile']).exists()
        )
        self.assertEqual(self.request.status, DailyServiceRequest.Status.NO_WORKERS)

    @override_settings(KAAMDO_MATCH_RADIUS_STAGES=(8, 15, 20), KAAMDO_MATCH_BATCH_SIZE=3)
    def test_radius_expansion_needs_consent_beyond_the_original_choice(self):
        worker = self.make_worker(12)
        self.request.radius_km = 8
        self.request.save(update_fields=['radius_km'])
        self.ready()
        first = advance_matching(self.request)
        self.request.refresh_from_db()
        self.assertEqual(first.created_offer_ids, ())
        self.assertEqual(self.request.status, DailyServiceRequest.Status.NO_WORKERS)
        self.assertEqual(self.request.match_reason, 'needs_radius_consent')
        self.client.credentials()
        expanded = self.client.post(
            '/api/v1/workers/daily-requests/expand/',
            {
                'reference': self.request.pk,
                'access_key': self.access_key,
                'radius_km': 15,
            },
            format='json',
        )
        offer = ServiceOffer.objects.get(request=self.request, profile=worker['profile'])
        self.request.refresh_from_db()
        self.assertEqual(expanded.status_code, 200)
        self.assertIn('does not add a travel fee', expanded.data['detail'])
        self.assertEqual(self.request.status, DailyServiceRequest.Status.OFFERING)
        self.assertEqual(offer.state, ServiceOffer.State.OFFERED)
        self.assertEqual(self.request.consented_radius_km, 15)

    def test_guest_cancel_withdraws_open_offers(self):
        worker = self.make_worker(1)
        self.ready()
        advance_matching(self.request)
        cancelled = self.client.post(
            '/api/v1/workers/daily-requests/cancel/',
            {'reference': self.request.pk, 'access_key': self.access_key},
            format='json',
        )
        offer = ServiceOffer.objects.get(request=self.request, profile=worker['profile'])
        self.request.refresh_from_db()
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(self.request.status, DailyServiceRequest.Status.CANCELLED)
        self.assertEqual(offer.state, ServiceOffer.State.WITHDRAWN)
        self.assertIsNone(self.request.assigned_profile_id)

    def test_wrong_access_key_cannot_cancel_or_expand(self):
        self.ready()
        cancelled = self.client.post(
            '/api/v1/workers/daily-requests/cancel/',
            {'reference': self.request.pk, 'access_key': 'not-the-real-key-value-xx'},
            format='json',
        )
        expanded = self.client.post(
            '/api/v1/workers/daily-requests/expand/',
            {
                'reference': self.request.pk,
                'access_key': 'not-the-real-key-value-xx',
                'radius_km': 20,
            },
            format='json',
        )
        self.request.refresh_from_db()
        self.assertEqual(cancelled.status_code, 404)
        self.assertEqual(expanded.status_code, 404)
        self.assertEqual(self.request.status, DailyServiceRequest.Status.DISPATCH_PENDING)

    @override_settings(KAAMDO_MATCH_BATCH_SIZE=1, KAAMDO_MATCH_OFFER_WINDOW_SECONDS=30)
    def test_process_command_expires_and_reassigns_without_a_browser(self):
        first = self.make_worker(1)
        second = self.make_worker(2)
        self.ready()
        advance_matching(self.request)
        offer = ServiceOffer.objects.get(request=self.request, profile=first['profile'])
        past = timezone.now() - timedelta(seconds=40)
        offer.offered_at = past
        offer.expires_at = past
        offer.save(update_fields=['offered_at', 'expires_at'])
        call_command('process_daily_matching')
        offer.refresh_from_db()
        next_offer = ServiceOffer.objects.get(request=self.request, profile=second['profile'])
        self.request.refresh_from_db()
        self.assertEqual(offer.state, ServiceOffer.State.EXPIRED)
        self.assertEqual(next_offer.state, ServiceOffer.State.OFFERED)
        self.assertEqual(self.request.status, DailyServiceRequest.Status.OFFERING)

    def test_command_is_idempotent_when_an_offer_is_still_open(self):
        self.make_worker(1)
        self.ready()
        first = process_due_matching()
        second = process_due_matching()
        self.assertEqual(ServiceOffer.objects.filter(request=self.request).count(), 1)
        self.assertEqual(second['expired_offers'], 0)
        self.assertGreaterEqual(first['requests'], 1)
