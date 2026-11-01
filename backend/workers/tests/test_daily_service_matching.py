"""Staff matching creates offers. It does not assign a worker or take payment."""

import math
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    Skill,
    VisitPayment,
    WorkerProfile,
    get_active_visit_fee,
)
from workers.services import (
    create_service_offers,
    eligible_worker_profiles,
    geographic_distance_km,
)


def north_of(latitude, longitude, kilometres):
    """A point due north of the starting point, using the same Earth radius as matching."""
    delta = (kilometres / 6371.0) * (180 / math.pi)
    return (
        Decimal(str(latitude + delta)).quantize(Decimal('0.000001')),
        Decimal(str(longitude)).quantize(Decimal('0.000001')),
    )


class MatchingServiceTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.other = ServiceCategory.objects.create(name='Plumber', slug='plumber')
        self.request = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-match@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        self._phones = 9000000600

    def make_worker(
        self,
        *,
        categories=None,
        approved=True,
        published=True,
        active=True,
        available=True,
        latitude=Decimal('12.010000'),
        longitude=Decimal('77.000000'),
        radius=20,
        skill_name='',
    ):
        self._phones += 1
        user = User.objects.create_user(
            username=f'worker-{self._phones}',
            password='SafePass!234',
            phone_number=str(self._phones),
            is_active=active,
        )
        AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=user,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            latitude=latitude,
            longitude=longitude,
            service_radius_km=radius,
            availability=(
                WorkerProfile.Availability.AVAILABLE
                if available
                else WorkerProfile.Availability.UNAVAILABLE
            ),
            publication_status=(
                WorkerProfile.PublicationStatus.PUBLISHED
                if published
                else WorkerProfile.PublicationStatus.DRAFT
            ),
        )
        if approved:
            ServiceProviderVerification.objects.create(
                user=user,
                status=ServiceProviderVerification.Status.APPROVED,
            )
        if categories:
            profile.service_categories.set(categories)
        if skill_name:
            skill, _created = Skill.objects.get_or_create(name=skill_name)
            profile.skills.add(skill)
        return profile

    def test_distance_rejects_missing_and_invalid_coordinates(self):
        same = geographic_distance_km(12, 77, 12, 77)
        missing = geographic_distance_km(None, 77, 12, 77)
        invalid = geographic_distance_km(95, 77, 12, 77)
        self.assertEqual(same, 0)
        self.assertIsNone(missing)
        self.assertIsNone(invalid)

    def test_only_the_requested_category_matches(self):
        named_only = self.make_worker(skill_name='Electrician')
        other = self.make_worker(categories=[self.other])
        exact = self.make_worker(categories=[self.category, self.other])
        matched = eligible_worker_profiles(self.request)
        self.assertEqual(matched, [exact])
        self.assertEqual(named_only.service_categories.count(), 0)
        self.assertNotIn(other, matched)

    def test_unavailable_providers_are_excluded_from_category_matching(self):
        unavailable = self.make_worker(categories=[self.category], available=False)
        ready = self.make_worker(categories=[self.category])
        matched = eligible_worker_profiles(self.request)
        self.assertEqual(matched, [ready])
        self.assertNotIn(unavailable, matched)

    def test_verification_publication_account_and_availability_are_required(self):
        pending = self.make_worker(categories=[self.category], approved=False)
        ServiceProviderVerification.objects.create(
            user=pending.user,
            status=ServiceProviderVerification.Status.PENDING,
        )
        self.make_worker(categories=[self.category], published=False)
        self.make_worker(categories=[self.category], active=False)
        self.make_worker(categories=[self.category], available=False)
        ready = self.make_worker(categories=[self.category])
        self.assertEqual(eligible_worker_profiles(self.request), [ready])

    def test_missing_and_invalid_worker_coordinates_are_excluded(self):
        self.make_worker(categories=[self.category], latitude=None, longitude=None)
        self.make_worker(categories=[self.category], latitude=Decimal('95.000000'), longitude=Decimal('77.000000'))
        self.make_worker(categories=[self.category], latitude=Decimal('12.000000'), longitude=None)
        ready = self.make_worker(categories=[self.category])
        self.assertEqual(eligible_worker_profiles(self.request), [ready])

    def test_both_customer_and_worker_radii_must_cover_the_distance(self):
        near_lat, near_lon = north_of(12, 77, 10)
        far_lat, far_lon = north_of(12, 77, 40)
        outside_customer = self.make_worker(
            categories=[self.category],
            latitude=far_lat,
            longitude=far_lon,
            radius=100,
        )
        outside_worker = self.make_worker(
            categories=[self.category],
            latitude=near_lat,
            longitude=near_lon,
            radius=5,
        )
        covered = self.make_worker(
            categories=[self.category],
            latitude=near_lat,
            longitude=near_lon,
            radius=20,
        )
        matched = eligible_worker_profiles(self.request)
        distance = geographic_distance_km(self.request.latitude, self.request.longitude, near_lat, near_lon)
        self.assertGreater(distance, 5)
        self.assertLess(distance, 15)
        self.assertEqual(matched, [covered])
        self.assertNotIn(outside_customer, matched)
        self.assertNotIn(outside_worker, matched)

    def advance(self, record, target):
        for step in (
            DailyServiceRequest.Status.AWAITING_PAYMENT,
            DailyServiceRequest.Status.DISPATCH_PENDING,
            DailyServiceRequest.Status.OFFERING,
        ):
            record.transition_to(step)
            if record.status == target:
                return

    def test_early_statuses_are_refused_and_create_no_offers(self):
        fee = get_active_visit_fee()
        self.assertIsNotNone(fee)
        self.assertEqual(fee.amount_inr, Decimal('99.00'))
        with self.assertRaises(ValidationError):
            create_service_offers(self.request)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, DailyServiceRequest.Status.DRAFT)
        self.assertEqual(ServiceOffer.objects.count(), 0)
        self.assertEqual(VisitPayment.objects.count(), 0)

        self.request.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        with self.assertRaises(ValidationError):
            create_service_offers(self.request)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.assertEqual(ServiceOffer.objects.count(), 0)
        self.assertEqual(VisitPayment.objects.count(), 0)

    def test_no_eligible_workers_leaves_an_honest_unassigned_request(self):
        self.advance(self.request, DailyServiceRequest.Status.OFFERING)
        result = create_service_offers(self.request)
        self.request.refresh_from_db()
        self.assertEqual(result.eligible_count, 0)
        self.assertEqual(result.created_offer_ids, ())
        self.assertEqual(self.request.status, DailyServiceRequest.Status.NO_WORKERS)
        self.assertEqual(self.request.match_reason, 'needs_radius_consent')
        self.assertIsNone(self.request.assigned_profile_id)
        self.assertEqual(ServiceOffer.objects.count(), 0)
        self.assertEqual(VisitPayment.objects.count(), 0)

    def test_repeat_matching_preserves_existing_offers_and_request_state(self):
        self.advance(self.request, DailyServiceRequest.Status.OFFERING)
        profile = self.make_worker(categories=[self.category])
        kept = ServiceOffer.objects.create(
            request=self.request,
            profile=profile,
            state=ServiceOffer.State.DECLINED,
        )
        first = create_service_offers(self.request)
        second = create_service_offers(self.request)
        kept.refresh_from_db()
        self.request.refresh_from_db()
        self.assertEqual(first.created_offer_ids, ())
        self.assertEqual(second.created_offer_ids, ())
        self.assertEqual(ServiceOffer.objects.count(), 1)
        self.assertEqual(kept.state, ServiceOffer.State.DECLINED)
        self.assertEqual(self.request.status, DailyServiceRequest.Status.NO_ACCEPTANCE)
        self.assertIsNone(self.request.assigned_profile_id)

        with patch(
            'workers.matching.ServiceOffer.objects.get_or_create',
            side_effect=IntegrityError,
        ):
            raced = create_service_offers(self.request)
        self.assertEqual(ServiceOffer.objects.count(), 1)
        self.assertEqual(raced.created_offer_ids, ())


class MatchingApiTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.daily_request = DailyServiceRequest.objects.create(
            category=self.category,
            guest_name='Asha Rao',
            contact_email='guest-match@example.com',
            description='The ceiling fan does not start.',
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )
        worker = User.objects.create_user(
            username='worker-match-api',
            password='SafePass!234',
            phone_number='9000000701',
        )
        AccountCapability.objects.create(user=worker, code=Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=worker,
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
        profile.service_categories.add(self.category)
        ServiceProviderVerification.objects.create(
            user=worker,
            status=ServiceProviderVerification.Status.APPROVED,
        )
        self.customer = User.objects.create_user(
            username='customer-match-api',
            password='SafePass!234',
            phone_number='9000000702',
        )
        self.staff = User.objects.create_user(
            username='staff-match-api',
            password='SafePass!234',
            phone_number='9000000703',
            is_staff=True,
        )
        self.customer_token = Token.objects.create(user=self.customer)
        self.staff_token = Token.objects.create(user=self.staff)

    def advance_to_dispatch(self):
        self.daily_request.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.daily_request.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)

    def match(self, token=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        else:
            self.client.credentials()
        return self.client.post(f'/api/v1/workers/daily-requests/{self.daily_request.pk}/match/')

    def test_only_staff_can_match_and_the_response_stays_private(self):
        anonymous = self.match()
        customer = self.match(self.customer_token.key)
        staff = self.match(self.staff_token.key)
        self.daily_request.refresh_from_db()

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(customer.status_code, 403)
        self.assertEqual(staff.status_code, 400)
        self.assertEqual(ServiceOffer.objects.count(), 0)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertEqual(VisitPayment.objects.count(), 0)

        self.advance_to_dispatch()
        ready = self.match(self.staff_token.key)
        self.daily_request.refresh_from_db()
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(
            set(ready.data),
            {
                'detail',
                'reference',
                'status',
                'eligible_count',
                'offers_created',
                'offers_already_present',
                'match_reason',
                'search_radius_km',
            },
        )
        self.assertEqual(ready.data['status'], 'offering')
        self.assertEqual(ready.data['eligible_count'], 1)
        self.assertEqual(ready.data['offers_created'], 1)
        self.assertNotIn('guest-match@example.com', str(ready.data))
        self.assertNotIn('access_key', ready.data)
        self.assertIsNone(self.daily_request.assigned_profile_id)
        self.assertEqual(ServiceOffer.objects.filter(request=self.daily_request).count(), 1)
        self.assertEqual(VisitPayment.objects.count(), 0)

        repeated = self.match(self.staff_token.key)
        self.daily_request.refresh_from_db()
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data['offers_created'], 0)
        self.assertEqual(repeated.data['offers_already_present'], 1)
        self.assertEqual(self.daily_request.status, DailyServiceRequest.Status.OFFERING)
        self.assertEqual(ServiceOffer.objects.filter(request=self.daily_request).count(), 1)
        self.assertEqual(VisitPayment.objects.count(), 0)
