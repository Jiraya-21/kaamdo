"""
Tests for equipment listings and rental requests.
"""

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from equipment.models import BookingStatus, EquipmentBooking, EquipmentListing, FeeStatus


class EquipmentApiTests(APITestCase):
    def make_user(self, phone, capabilities, active_mode=None):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            first_name='Ravi',
            last_name='Kumar',
            active_mode=active_mode or capabilities[0],
        )
        for code in capabilities:
            AccountCapability.objects.create(user=user, code=code)
        return user, Token.objects.create(user=user)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def listing_payload(self, **overrides):
        data = {
            'title': 'Small tractor',
            'description': 'Available for field work near town.',
            'district': 'Mandya',
            'locality': 'Town centre',
            'pricing_basis': 'hourly',
            'rate': '500.00',
            'operator_included': True,
            'status': 'draft',
        }
        data.update(overrides)
        return data

    def publish_for_fee(self, listing_id, owner_token):
        listing = EquipmentListing.objects.get(pk=listing_id)
        listing.fee_status = FeeStatus.PAID
        listing.save(update_fields=['fee_status'])
        self.auth(owner_token)
        return self.client.patch(
            f'/api/v1/equipment/{listing_id}/',
            {'status': 'published'},
            format='json',
        )
        data.update(overrides)
        return data

    def test_only_an_owner_capability_can_create_a_listing(self):
        owner, owner_token = self.make_user(
            '9876543210',
            [Capability.EQUIPMENT_OWNER],
            active_mode=Capability.CUSTOMER,
        )
        pretender, pretender_token = self.make_user(
            '9123456780',
            [Capability.AGRICULTURAL_EMPLOYER],
            active_mode=Capability.EQUIPMENT_OWNER,
        )
        self.auth(owner_token)
        created = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        invalid = self.client.post('/api/v1/equipment/', self.listing_payload(rate='0.00'), format='json')
        self.auth(pretender_token)
        denied = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        owner.refresh_from_db()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['pricing_basis'], 'hourly')
        self.assertEqual(created.data['rate'], '500.00')
        self.assertTrue(created.data['operator_included'])
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(owner.is_staff)
        self.assertEqual(EquipmentListing.objects.count(), 1)

    def test_owner_controls_the_listing_and_the_renter_controls_the_request(self):
        owner, owner_token = self.make_user('9000000011', [Capability.EQUIPMENT_OWNER])
        other_owner, other_token = self.make_user('9000000012', [Capability.EQUIPMENT_OWNER])
        renter, renter_token = self.make_user('9000000013', [Capability.EQUIPMENT_RENTER])
        self.auth(owner_token)
        published = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        self.publish_for_fee(published.data['id'], owner_token)
        draft = self.client.post(
            '/api/v1/equipment/',
            self.listing_payload(title='Hidden tiller', status='draft'),
            format='json',
        )
        self.auth(other_token)
        stolen = self.client.patch(
            f"/api/v1/equipment/{published.data['id']}/",
            {'rate': '900.00'},
            format='json',
        )
        self.client.credentials()
        hidden = self.client.get(f"/api/v1/equipment/{draft.data['id']}/")
        visible = self.client.get('/api/v1/equipment/')

        self.auth(renter_token)
        bad_dates = self.client.post(
            f"/api/v1/equipment/{published.data['id']}/bookings/",
            {'start_date': '2026-11-10', 'end_date': '2026-11-01', 'note': 'Too soon.'},
            format='json',
        )
        forced = self.client.post(
            f"/api/v1/equipment/{published.data['id']}/bookings/",
            {'start_date': '2026-11-01', 'end_date': '2026-11-03', 'status': 'accepted'},
            format='json',
        )
        booked = self.client.post(
            f"/api/v1/equipment/{published.data['id']}/bookings/",
            {'start_date': '2026-11-01', 'end_date': '2026-11-03', 'note': 'Need it for ploughing.'},
            format='json',
        )
        duplicate = self.client.post(
            f"/api/v1/equipment/{published.data['id']}/bookings/",
            {'start_date': '2026-11-04', 'end_date': '2026-11-05'},
            format='json',
        )
        self.auth(owner_token)
        accepted = self.client.patch(
            f"/api/v1/equipment/bookings/{booked.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        self.auth(renter_token)
        locked = self.client.patch(
            f"/api/v1/equipment/bookings/{booked.data['id']}/",
            {'note': 'Changed my mind.'},
            format='json',
        )

        self.assertEqual(stolen.status_code, 403)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(visible.data['count'], 1)
        self.assertNotIn('9000000011', str(visible.data))
        self.assertEqual(bad_dates.status_code, 400)
        self.assertEqual(forced.status_code, 400)
        self.assertEqual(booked.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(locked.status_code, 400)
        self.assertEqual(EquipmentBooking.objects.get(pk=booked.data['id']).status, BookingStatus.ACCEPTED)

    def test_a_declined_request_can_be_sent_again_and_only_the_owner_decides(self):
        owner, owner_token = self.make_user('9000000021', [Capability.EQUIPMENT_OWNER])
        renter, renter_token = self.make_user('9000000022', [Capability.EQUIPMENT_RENTER])
        self.auth(owner_token)
        listing = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        self.publish_for_fee(listing.data['id'], owner_token)
        self.auth(renter_token)
        first = self.client.post(
            f"/api/v1/equipment/{listing.data['id']}/bookings/",
            {'start_date': '2026-12-01', 'end_date': '2026-12-02'},
            format='json',
        )
        self_accept = self.client.patch(
            f"/api/v1/equipment/bookings/{first.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        self.auth(owner_token)
        declined = self.client.patch(
            f"/api/v1/equipment/bookings/{first.data['id']}/",
            {'status': 'declined'},
            format='json',
        )
        self.auth(renter_token)
        second = self.client.post(
            f"/api/v1/equipment/{listing.data['id']}/bookings/",
            {'start_date': '2026-12-10', 'end_date': '2026-12-12'},
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['status'], 'requested')
        self.assertEqual(self_accept.status_code, 400)
        self.assertEqual(declined.status_code, 200)
        self.assertEqual(declined.data['status'], 'declined')
        self.assertEqual(second.status_code, 201)
        self.assertEqual(
            EquipmentBooking.objects.filter(status=BookingStatus.REQUESTED).count(),
            1,
        )

    def test_unpaid_listings_stay_private_and_inquiries_do_not_create_bookings(self):
        from datetime import timedelta

        from django.utils import timezone

        from accounts.models import OtpPurpose, PhoneVerification

        owner, owner_token = self.make_user('9000000031', [Capability.EQUIPMENT_OWNER, Capability.CUSTOMER])
        customer, customer_token = self.make_user('9000000032', [Capability.CUSTOMER])
        self.auth(owner_token)
        refused = self.client.post('/api/v1/equipment/', self.listing_payload(status='published'), format='json')
        created = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        fee_hack = self.client.patch(
            f"/api/v1/equipment/{created.data['id']}/",
            {'fee_status': 'paid', 'status': 'published'},
            format='json',
        )
        self.client.credentials()
        hidden = self.client.get('/api/v1/equipment/')
        listing = EquipmentListing.objects.get(pk=created.data['id'])
        listing.fee_status = FeeStatus.PAID
        listing.status = 'published'
        listing.save(update_fields=['fee_status', 'status'])
        PhoneVerification.objects.create(
            user=customer,
            phone_number=customer.phone_number,
            purpose=OtpPurpose.EQUIPMENT_INQUIRY,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.auth(customer_token)
        inquiry = self.client.post(
            f"/api/v1/equipment/{listing.id}/inquiries/",
            {'requirement': 'Need it for two mornings.'},
            format='json',
        )
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['fee_status'], 'unpaid')
        self.assertEqual(fee_hack.status_code, 400)
        self.assertEqual(hidden.data['count'], 0)
        self.assertEqual(inquiry.status_code, 201)
        self.assertEqual(EquipmentBooking.objects.count(), 0)
        self.assertEqual(inquiry.data['contact_phone'], customer.phone_number)

    def test_accepted_booking_blocks_overlapping_dates(self):
        owner, owner_token = self.make_user('9000000401', [Capability.EQUIPMENT_OWNER])
        first_renter, first_token = self.make_user('9000000402', [Capability.EQUIPMENT_RENTER])
        second_renter, second_token = self.make_user('9000000403', [Capability.EQUIPMENT_RENTER])
        self.auth(owner_token)
        listing = self.client.post('/api/v1/equipment/', self.listing_payload(), format='json')
        self.publish_for_fee(listing.data['id'], owner_token)
        self.auth(first_token)
        first = self.client.post(
            f"/api/v1/equipment/{listing.data['id']}/bookings/",
            {'start_date': '2026-12-01', 'end_date': '2026-12-05'},
            format='json',
        )
        self.auth(owner_token)
        accepted = self.client.patch(
            f"/api/v1/equipment/bookings/{first.data['id']}/",
            {'status': 'accepted'},
            format='json',
        )
        self.auth(second_token)
        overlap = self.client.post(
            f"/api/v1/equipment/{listing.data['id']}/bookings/",
            {'start_date': '2026-12-04', 'end_date': '2026-12-08'},
            format='json',
        )
        later = self.client.post(
            f"/api/v1/equipment/{listing.data['id']}/bookings/",
            {'start_date': '2026-12-10', 'end_date': '2026-12-12'},
            format='json',
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(overlap.status_code, 400)
        self.assertEqual(later.status_code, 201)
