"""Owners and renters cannot read another person's bookings or inquiries."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, OtpPurpose, PhoneVerification, User
from equipment.models import EquipmentListing, FeeStatus, ListingStatus


class EquipmentPrivacyTests(APITestCase):
    def make_user(self, phone, capabilities):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            first_name='Asha',
            last_name='Rao',
        )
        for code in capabilities:
            AccountCapability.objects.create(user=user, code=code)
        return user, Token.objects.create(user=user)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def listing_payload(self):
        return {
            'title': 'Small tractor',
            'description': 'Available for field work near town.',
            'district': 'Mandya',
            'locality': 'Town centre',
            'pricing_basis': 'hourly',
            'rate': '500.00',
            'operator_included': True,
            'status': 'draft',
        }

    def publish(self, listing_id):
        listing = EquipmentListing.objects.get(pk=listing_id)
        listing.fee_status = FeeStatus.PAID
        listing.status = ListingStatus.PUBLISHED
        listing.save(update_fields=['fee_status', 'status'])

    def test_other_users_cannot_read_bookings_or_inquiries(self):
        owner, owner_token = self.make_user('9000000111', [Capability.EQUIPMENT_OWNER, Capability.CUSTOMER])
        other_owner, other_owner_token = self.make_user('9000000112', [Capability.EQUIPMENT_OWNER])
        renter, renter_token = self.make_user('9000000113', [Capability.EQUIPMENT_RENTER])
        other_renter, other_renter_token = self.make_user('9000000114', [Capability.EQUIPMENT_RENTER])
        customer, customer_token = self.make_user('9000000115', [Capability.CUSTOMER])
        PhoneVerification.objects.create(
            user=customer,
            phone_number=customer.phone_number,
            purpose=OtpPurpose.EQUIPMENT_INQUIRY,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        self.auth(owner_token)
        created = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        self.assertEqual(created.status_code, 201)
        listing_id = created.data['id']
        self.publish(listing_id)

        self.auth(renter_token)
        booked = self.client.post(
            f'/api/v1/equipment/{listing_id}/bookings/',
            {'start_date': '2026-11-01', 'end_date': '2026-11-03', 'note': 'Need it for ploughing.'},
            format='json',
        )
        self.assertEqual(booked.status_code, 201)
        booking_id = booked.data['id']
        mine = self.client.get('/api/v1/equipment/bookings/')
        own_detail = self.client.get(f'/api/v1/equipment/bookings/{booking_id}/')

        self.auth(other_renter_token)
        other_list = self.client.get('/api/v1/equipment/bookings/')
        stolen_detail = self.client.get(f'/api/v1/equipment/bookings/{booking_id}/')
        stolen_patch = self.client.patch(
            f'/api/v1/equipment/bookings/{booking_id}/',
            {'status': 'accepted'},
            format='json',
        )

        self.auth(other_owner_token)
        stolen_listing_bookings = self.client.get(f'/api/v1/equipment/{listing_id}/bookings/')
        stolen_listing_inquiries = self.client.get(f'/api/v1/equipment/{listing_id}/inquiries/')

        self.auth(customer_token)
        inquiry = self.client.post(
            f'/api/v1/equipment/{listing_id}/inquiries/',
            {'requirement': 'Need it for two mornings.'},
            format='json',
        )
        self.assertEqual(inquiry.status_code, 201)
        inquiry_id = inquiry.data['id']
        customer_list = self.client.get('/api/v1/equipment/inquiries/')
        stolen_inquiry_patch = self.client.patch(
            f'/api/v1/equipment/inquiries/{inquiry_id}/',
            {'status': 'closed'},
            format='json',
        )

        other_customer, other_customer_token = self.make_user('9000000116', [Capability.CUSTOMER])
        self.auth(other_customer_token)
        other_inquiries = self.client.get('/api/v1/equipment/inquiries/')
        other_inquiry_patch = self.client.patch(
            f'/api/v1/equipment/inquiries/{inquiry_id}/',
            {'status': 'seen'},
            format='json',
        )

        self.auth(owner_token)
        owner_bookings = self.client.get(f'/api/v1/equipment/{listing_id}/bookings/')
        owner_inquiries = self.client.get(f'/api/v1/equipment/{listing_id}/inquiries/')
        owner_booking_detail = self.client.get(f'/api/v1/equipment/bookings/{booking_id}/')
        owner_as_customer = self.client.get('/api/v1/equipment/inquiries/')

        self.client.credentials()
        anonymous_bookings = self.client.get('/api/v1/equipment/bookings/')
        anonymous_inquiries = self.client.get('/api/v1/equipment/inquiries/')
        anonymous_detail = self.client.get(f'/api/v1/equipment/bookings/{booking_id}/')

        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.data['count'], 1)
        self.assertEqual(own_detail.status_code, 200)
        self.assertEqual(other_list.status_code, 200)
        self.assertEqual(other_list.data['count'], 0)
        self.assertEqual(stolen_detail.status_code, 404)
        self.assertEqual(stolen_patch.status_code, 404)
        self.assertEqual(stolen_listing_bookings.status_code, 404)
        self.assertEqual(stolen_listing_inquiries.status_code, 404)
        self.assertEqual(customer_list.status_code, 200)
        self.assertEqual(customer_list.data['count'], 1)
        self.assertEqual(stolen_inquiry_patch.status_code, 404)
        self.assertEqual(other_inquiries.status_code, 200)
        self.assertEqual(other_inquiries.data['count'], 0)
        self.assertEqual(other_inquiry_patch.status_code, 404)
        self.assertEqual(owner_bookings.status_code, 200)
        self.assertEqual(len(owner_bookings.data), 1)
        self.assertEqual(owner_inquiries.status_code, 200)
        self.assertEqual(len(owner_inquiries.data), 1)
        self.assertEqual(owner_booking_detail.status_code, 200)
        self.assertEqual(owner_as_customer.status_code, 200)
        self.assertEqual(owner_as_customer.data['count'], 0)
        self.assertNotIn(customer.phone_number, str(mine.data))
        self.assertEqual(anonymous_bookings.status_code, 401)
        self.assertEqual(anonymous_inquiries.status_code, 401)
        self.assertEqual(anonymous_detail.status_code, 401)
