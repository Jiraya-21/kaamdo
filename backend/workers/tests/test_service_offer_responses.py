"""A worker accepts or declines one daily-service offer."""

from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    WorkerProfile,
)


class ServiceOfferResponseTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.daily_request = self.make_request()
        self.owner = self.make_worker('9000000801')
        self.other = self.make_worker('9000000802')
        self.offer = ServiceOffer.objects.create(request=self.daily_request, profile=self.owner['profile'])
        self.other_offer = ServiceOffer.objects.create(request=self.daily_request, profile=self.other['profile'])

    def make_request(self):
        return DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-offer@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )

    def make_worker(self, phone):
        user = User.objects.create_user(
            username=f'worker-{phone}',
            password='SafePass!234',
            phone_number=phone,
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=user,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            latitude=Decimal('12.010000'),
            longitude=Decimal('77.000000'),
            service_radius_km=20,
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
        )
        ServiceProviderVerification.objects.create(
            user=user,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        return {'user': user, 'profile': profile, 'token': Token.objects.create(user=user)}

    def respond(self, offer, token, decision):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return self.client.post(
            f'/api/v1/workers/daily-offers/{offer.pk}/respond/',
            {'decision': decision},
            format='json',
        )

    def move_to_offering(self, record):
        record.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        record.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        record.transition_to(DailyServiceRequest.Status.OFFERING)

    def test_owner_can_decline_without_being_assigned(self):
        response = self.respond(self.offer, self.owner['token'], 'decline')
        self.offer.refresh_from_db()
        self.daily_request.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], 'declined')
        self.assertEqual(self.offer.state, ServiceOffer.State.DECLINED)
        self.assertIsNotNone(self.offer.responded_at)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertIsNone(self.daily_request.assigned_profile_id)
        self.assertNotIn('guest-offer@example.com', str(response.data))

    def test_owner_can_accept_while_the_request_is_offering(self):
        self.move_to_offering(self.daily_request)
        response = self.respond(self.offer, self.owner['token'], 'accept')
        self.offer.refresh_from_db()
        self.daily_request.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], 'accepted')
        self.assertEqual(response.data['request_status'], 'assigned')
        self.assertEqual(self.offer.state, ServiceOffer.State.ACCEPTED)
        self.assertIsNotNone(self.offer.responded_at)
        self.assertEqual(self.daily_request.assigned_profile, self.owner['profile'])

    def test_another_worker_cannot_respond(self):
        response = self.respond(self.offer, self.other['token'], 'decline')
        self.offer.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.offer.state, ServiceOffer.State.OFFERED)
        self.assertIsNone(self.offer.responded_at)

    def test_invalid_decision_is_rejected(self):
        response = self.respond(self.offer, self.owner['token'], 'cancel')
        self.offer.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.offer.state, ServiceOffer.State.OFFERED)

    def test_an_answered_offer_cannot_be_answered_again(self):
        self.respond(self.offer, self.owner['token'], 'decline')
        again = self.respond(self.offer, self.owner['token'], 'accept')
        self.offer.refresh_from_db()
        self.daily_request.refresh_from_db()
        self.assertEqual(again.status_code, 400)
        self.assertEqual(self.offer.state, ServiceOffer.State.DECLINED)
        self.assertIsNone(self.daily_request.assigned_profile_id)

    def test_draft_request_cannot_be_assigned_by_acceptance(self):
        response = self.respond(self.offer, self.owner['token'], 'accept')
        self.offer.refresh_from_db()
        self.daily_request.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.offer.state, ServiceOffer.State.OFFERED)
        self.assertIsNone(self.offer.responded_at)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertIsNone(self.daily_request.assigned_profile_id)

    def test_two_workers_cannot_both_be_assigned(self):
        self.move_to_offering(self.daily_request)
        first = self.respond(self.offer, self.owner['token'], 'accept')
        second = self.respond(self.other_offer, self.other['token'], 'accept')
        self.offer.refresh_from_db()
        self.other_offer.refresh_from_db()
        self.daily_request.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(self.offer.state, ServiceOffer.State.ACCEPTED)
        self.assertEqual(self.other_offer.state, ServiceOffer.State.WITHDRAWN)
        self.assertEqual(self.daily_request.assigned_profile, self.owner['profile'])
        self.assertEqual(
            ServiceOffer.objects.filter(
                request=self.daily_request,
                state=ServiceOffer.State.ACCEPTED,
            ).count(),
            1,
        )
