"""Database rules for category-based daily service requests."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    Skill,
    VisitPayment,
    WorkerProfile,
    get_active_visit_fee,
)


class DailyServiceModelTests(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(
            name='Electrician',
            slug='electrician',
            is_active=True,
        )

    def request_values(self, **overrides):
        values = {
            'category': self.category,
            'guest_name': 'Asha Rao',
            'contact_email': 'Asha@Example.com',
            'description': 'The ceiling fan does not start.',
            'latitude': Decimal('12.521800'),
            'longitude': Decimal('76.895100'),
            'radius_km': 15,
        }
        values.update(overrides)
        return values

    def make_request(self, **overrides):
        record = DailyServiceRequest(**self.request_values(**overrides))
        record.full_clean()
        record.save()
        return record

    def make_profile(self, phone, radius):
        worker = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
        )
        return WorkerProfile.objects.create(
            user=worker,
            bio='Household electrical work.',
            service_rate=Decimal('100.00'),
            pricing_basis=WorkerProfile.PricingBasis.HOURLY,
            district='Mandya',
            locality='Town centre',
            service_radius_km=radius,
        )

    def test_service_categories_are_shared_links_and_are_not_copied_from_skills(self):
        plumber = ServiceCategory.objects.create(name='Plumber', slug='plumber', is_active=True)
        first = self.make_profile('9000000301', 10)
        second = self.make_profile('9000000302', 12)
        skill = Skill.objects.create(name='Electrician')
        first.skills.add(skill)
        first.service_categories.add(self.category, plumber)
        second.service_categories.add(self.category)
        untouched = self.make_profile('9000000303', 8)
        untouched.skills.add(skill)

        self.assertEqual(
            set(first.service_categories.values_list('slug', flat=True)),
            {'electrician', 'plumber'},
        )
        self.assertEqual(list(second.service_categories.values_list('slug', flat=True)), ['electrician'])
        self.assertEqual(self.category.worker_profiles.count(), 2)
        self.assertEqual(plumber.worker_profiles.count(), 1)
        self.assertEqual(untouched.service_categories.count(), 0)
        self.assertEqual(untouched.skills.count(), 1)

    def test_customer_radius_accepts_bounds_and_rejects_values_outside_them(self):
        for radius in (8, 15, 50):
            record = self.make_request(radius_km=radius)
            self.assertEqual(record.radius_km, radius)
            record.delete()
        for radius in (7, 51):
            record = DailyServiceRequest(**self.request_values(radius_km=radius))
            with self.assertRaises(ValidationError):
                record.full_clean()

    def test_inactive_category_cannot_start_a_request(self):
        self.category.is_active = False
        self.category.save()
        record = DailyServiceRequest(**self.request_values())
        with self.assertRaises(ValidationError):
            record.full_clean()
        self.category.is_active = True
        self.category.save()
        saved = self.make_request()
        self.category.is_active = False
        self.category.save()
        saved.description = 'Updated after the category was hidden.'
        saved.full_clean()

    def test_guest_request_does_not_need_a_user_and_registered_request_can_omit_guest_name(self):
        guest = self.make_request()
        self.assertIsNone(guest.customer_id)
        self.assertEqual(guest.contact_email, 'asha@example.com')
        customer = User.objects.create_user(
            username='9000000201',
            password='SafePass!234',
            phone_number='9000000201',
        )
        registered = self.make_request(customer=customer, guest_name='', contact_email='')
        self.assertEqual(registered.customer, customer)
        nameless = DailyServiceRequest(**self.request_values(guest_name='', contact_email=''))
        with self.assertRaises(ValidationError):
            nameless.full_clean()
        phone_only = DailyServiceRequest(
            **self.request_values(contact_email='', contact_phone='9876543210')
        )
        phone_only.full_clean()
        no_contact = DailyServiceRequest(**self.request_values(contact_email=''))
        with self.assertRaises(ValidationError):
            no_contact.full_clean()

    def test_access_key_is_hashed_and_plaintext_is_rejected(self):
        record = self.make_request()
        raw_key = 'guest-access-key-not-an-otp-value'
        record.set_access_key(raw_key)
        record.save()
        record.refresh_from_db()
        self.assertNotIn(raw_key, record.access_key_hash)
        self.assertTrue(record.check_access_key(raw_key))
        self.assertFalse(record.check_access_key('wrong-access-key-value'))
        record.access_key_hash = raw_key
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_status_transition_blocks_skipping_assignment_rules(self):
        record = self.make_request()
        with self.assertRaises(ValidationError):
            record.transition_to(DailyServiceRequest.Status.ASSIGNED)
        record.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.assertEqual(record.status, DailyServiceRequest.Status.AWAITING_PAYMENT)

    def test_duplicate_offer_is_rejected_and_reassignment_keeps_one_payment(self):
        record = self.make_request()
        first = self.make_profile('9000000202', 20)
        second = self.make_profile('9000000203', 12)
        ServiceOffer.objects.create(request=record, profile=first)
        ServiceOffer.objects.create(request=record, profile=second)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceOffer.objects.create(request=record, profile=first)
        fee = get_active_visit_fee()
        payment = VisitPayment.objects.create(request=record, amount_inr=fee.amount_inr)
        record.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        record.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        record.transition_to(DailyServiceRequest.Status.OFFERING)
        record.transition_to(DailyServiceRequest.Status.ASSIGNED, assigned_profile=first)
        record.transition_to(DailyServiceRequest.Status.WORKER_CANCELLED)
        record.transition_to(DailyServiceRequest.Status.OFFERING)
        self.assertIsNone(record.assigned_profile_id)
        self.assertEqual(VisitPayment.objects.filter(request=record).count(), 1)
        self.assertEqual(record.visit_payment.pk, payment.pk)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VisitPayment.objects.create(request=record, amount_inr=fee.amount_inr)

    def test_worker_travel_radius_is_separate_from_the_customer_radius(self):
        profile = self.make_profile('9000000204', 9)
        record = self.make_request(radius_km=50)
        self.assertEqual(profile.service_radius_km, 9)
        self.assertEqual(record.radius_km, 50)
        self.assertNotEqual(profile._meta.get_field('service_radius_km').name, record._meta.get_field('radius_km').name)

    def test_mock_payment_cannot_be_marked_as_real_money(self):
        record = self.make_request()
        fee = get_active_visit_fee()
        self.assertEqual(fee.amount_inr, Decimal('99.00'))
        fee.amount_inr = Decimal('125.00')
        fee.save()
        self.assertEqual(get_active_visit_fee().amount_inr, Decimal('125.00'))
        payment = VisitPayment(
            request=record,
            amount_inr=fee.amount_inr,
            state=VisitPayment.State.MOCK_RECORDED,
            verification_source=VisitPayment.Source.PAYMENT_GATEWAY,
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()
        payment.verification_source = VisitPayment.Source.MOCK_DEMO
        payment.verified_at = timezone.now()
        with self.assertRaises(ValidationError):
            payment.full_clean()
        payment.verified_at = None
        payment.full_clean()
        payment.save()
        with self.assertRaises(ValidationError):
            payment.transition_to(
                VisitPayment.State.GATEWAY_VERIFIED,
                verification_source=VisitPayment.Source.PAYMENT_GATEWAY,
                verified_at=timezone.now(),
            )
        self.assertNotIn('paid', {field.name for field in VisitPayment._meta.fields})
        fee.is_active = False
        fee.save()
        self.assertIsNone(get_active_visit_fee())
