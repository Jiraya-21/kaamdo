"""Customer daily-request list and worker offer list. Neither path changes a visit payment."""

from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    VisitPayment,
    WorkerProfile,
)


class DailyAccountListTests(APITestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name='Electrician', slug='electrician')
        self.customer = self.make_user('9000000911', Capability.CUSTOMER)
        self.other_customer = self.make_user('9000000912', Capability.CUSTOMER)
        self.worker = self.make_worker('9000000913')
        self.other_worker = self.make_worker('9000000914')
        self.own_request = self.make_request(customer=self.customer['user'], description='My ceiling fan.')
        self.own_request.set_access_key('customer-account-access-key')
        self.own_request.save(update_fields=['access_key_hash'])
        self.other_request = self.make_request(customer=self.other_customer['user'], description='Their switchboard.')
        self.guest_request = self.make_request(
            customer=None,
            guest_name='Guest Person',
            contact_email='guest-account@example.com',
            description='A guest request.',
        )
        self.own_offer = ServiceOffer.objects.create(request=self.own_request, profile=self.worker['profile'])
        self.other_offer = ServiceOffer.objects.create(
            request=self.own_request,
            profile=self.other_worker['profile'],
        )
        self.payment = VisitPayment.objects.create(
            request=self.own_request,
            amount_inr=Decimal('99.00'),
            state=VisitPayment.State.PENDING,
            verification_source=VisitPayment.Source.NONE,
        )

    def make_user(self, phone, capability):
        user = User.objects.create_user(
            username=f'user-{phone}',
            password='SafePass!234',
            phone_number=phone,
            first_name='Asha',
            last_name='Rao',
        )
        AccountCapability.objects.create(user=user, code=capability)
        return {'user': user, 'token': Token.objects.create(user=user)}

    def make_worker(self, phone):
        made = self.make_user(phone, Capability.SERVICE_PROVIDER)
        profile = WorkerProfile.objects.create(
            user=made['user'],
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
            user=made['user'],
            status=ServiceProviderVerification.Status.APPROVED,
        )
        made['profile'] = profile
        return made

    def make_request(self, customer, description, guest_name='', contact_email=''):
        return DailyServiceRequest.objects.create(
            category=self.category,
            customer=customer,
            guest_name=guest_name,
            contact_email=contact_email,
            description=description,
            latitude=Decimal('12.000000'),
            longitude=Decimal('77.000000'),
            radius_km=15,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def payment_snapshot(self):
        self.payment.refresh_from_db()
        return (
            VisitPayment.objects.count(),
            self.payment.pk,
            self.payment.state,
            self.payment.verification_source,
            str(self.payment.amount_inr),
            self.payment.verified_at,
        )

    def test_customer_sees_only_their_requests_and_no_secrets(self):
        before = self.payment_snapshot()
        self.auth(self.customer['token'])
        response = self.client.get(
            f'/api/v1/workers/daily-requests/mine/?customer={self.other_customer["user"].pk}',
        )
        body = str(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row['reference'], self.own_request.pk)
        self.assertEqual(row['category'], 'Electrician')
        self.assertEqual(row['description'], 'My ceiling fan.')
        self.assertEqual(row['status'], 'draft')
        self.assertEqual(row['radius_km'], 15)
        self.assertNotIn('assigned_profile', row)
        self.assertNotIn('access_key', body)
        self.assertNotIn('contact_email', body)
        self.assertNotIn('guest-account@example.com', body)
        self.assertIn('payment', row)
        self.assertEqual(row['payment']['money_received'], False)
        self.assertNotIn(str(self.other_request.pk), [str(item['reference']) for item in response.data])
        self.assertEqual(self.payment_snapshot(), before)

    def test_guest_and_other_accounts_are_not_listed_for_a_customer(self):
        self.auth(self.other_customer['token'])
        response = self.client.get('/api/v1/workers/daily-requests/mine/')
        references = [item['reference'] for item in response.data]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(references, [self.other_request.pk])
        self.assertNotIn(self.guest_request.pk, references)

    def test_anonymous_cannot_list_requests_but_signed_in_provider_can(self):
        """Marketplace access is any signed-in account; Customer is not a gate."""
        anonymous = self.client.get('/api/v1/workers/daily-requests/mine/')
        self.auth(self.worker['token'])
        provider = self.client.get('/api/v1/workers/daily-requests/mine/')
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(provider.status_code, 200)
        self.assertEqual(provider.data, [])

    def test_worker_sees_only_their_offers(self):
        before = self.payment_snapshot()
        self.auth(self.worker['token'])
        response = self.client.get(
            f'/api/v1/workers/daily-offers/mine/?profile={self.other_worker["profile"].pk}',
        )
        body = str(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        offer = response.data[0]
        self.assertEqual(offer['id'], self.own_offer.pk)
        self.assertEqual(offer['state'], 'offered')
        self.assertEqual(offer['request']['reference'], self.own_request.pk)
        self.assertEqual(offer['request']['category'], 'Electrician')
        self.assertEqual(offer['request']['description'], 'My ceiling fan.')
        self.assertNotIn('access_key', body)
        self.assertNotIn('contact_email', body)
        self.assertIn('payment', offer['request'])
        self.assertEqual(offer['request']['payment']['money_received'], False)
        self.assertNotIn('latitude', body)
        self.assertEqual(self.payment_snapshot(), before)

    def test_anonymous_and_customer_cannot_list_offers(self):
        anonymous = self.client.get('/api/v1/workers/daily-offers/mine/')
        self.auth(self.customer['token'])
        customer = self.client.get('/api/v1/workers/daily-offers/mine/')
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(customer.status_code, 403)

    def test_decline_and_invalid_response_do_not_change_payment(self):
        before = self.payment_snapshot()
        self.auth(self.other_worker['token'])
        stolen = self.client.post(
            f'/api/v1/workers/daily-offers/{self.own_offer.pk}/respond/',
            {'decision': 'decline'},
            format='json',
        )
        self.auth(self.worker['token'])
        invalid = self.client.post(
            f'/api/v1/workers/daily-offers/{self.own_offer.pk}/respond/',
            {'decision': 'cancel'},
            format='json',
        )
        declined = self.client.post(
            f'/api/v1/workers/daily-offers/{self.own_offer.pk}/respond/',
            {'decision': 'decline'},
            format='json',
        )
        again = self.client.post(
            f'/api/v1/workers/daily-offers/{self.own_offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.own_offer.refresh_from_db()
        self.own_request.refresh_from_db()
        self.assertEqual(stolen.status_code, 404)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(declined.status_code, 200)
        self.assertEqual(declined.data['state'], 'declined')
        self.assertEqual(declined.data['request_status'], 'draft')
        self.assertEqual(again.status_code, 400)
        self.assertEqual(self.own_offer.state, ServiceOffer.State.DECLINED)
        self.assertEqual(self.own_request.status, DailyServiceRequest.Status.DRAFT)
        self.assertEqual(self.payment_snapshot(), before)

    def test_accept_assigns_the_request_without_changing_payment(self):
        self.own_request.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.own_request.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        self.own_request.transition_to(DailyServiceRequest.Status.OFFERING)
        before = self.payment_snapshot()
        self.auth(self.worker['token'])
        accepted = self.client.post(
            f'/api/v1/workers/daily-offers/{self.own_offer.pk}/respond/',
            {'decision': 'accept'},
            format='json',
        )
        self.own_request.refresh_from_db()
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['state'], 'accepted')
        self.assertEqual(accepted.data['request_status'], 'assigned')
        self.assertEqual(self.own_request.assigned_profile, self.worker['profile'])
        self.assertEqual(self.payment_snapshot(), before)
        self.auth(self.customer['token'])
        listed = self.client.get('/api/v1/workers/daily-requests/mine/')
        card = listed.data[0]['assigned_profile']
        self.assertEqual(card['display_name'], self.worker['profile'].display_name)
        self.assertEqual(card['locality'], 'Town centre')
        self.assertEqual(card['district'], 'Mandya')
        self.assertNotIn('phone', str(card))
        self.assertEqual(self.payment_snapshot(), before)

    def test_customer_creates_one_draft_without_a_worker_or_payment(self):
        before = self.payment_snapshot()
        retired = ServiceCategory.objects.create(name='Retired trade', slug='retired', is_active=False)
        self.auth(self.customer['token'])
        created = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': self.category.pk,
                'description': 'Replace a switch.',
                'latitude': '12.971891887766543',
                'longitude': '77.59456634567891',
                'radius_km': 12,
                'customer': self.other_customer['user'].pk,
                'status': 'assigned',
                'guest_name': 'Someone else',
                'contact_email': 'other@example.com',
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['status'], 'awaiting_payment')
        self.assertEqual(created.data['category'], 'Electrician')
        self.assertNotIn('access_key', created.data)
        self.assertNotIn('assigned_profile', created.data)
        self.assertNotIn('contact_email', created.data)
        record = DailyServiceRequest.objects.get(pk=created.data['reference'])
        self.assertEqual(record.latitude, Decimal('12.971892'))
        self.assertEqual(record.longitude, Decimal('77.594566'))
        self.assertEqual(record.customer, self.customer['user'])
        self.assertEqual(record.guest_name, '')
        self.assertEqual(record.contact_email, '')
        self.assertEqual(record.access_key_hash, '')
        self.assertIsNone(record.assigned_profile_id)
        self.assertEqual(VisitPayment.objects.filter(request=record).count(), 1)
        self.assertEqual(
            VisitPayment.objects.get(request=record).state,
            VisitPayment.State.PENDING,
        )
        self.assertNotEqual(self.payment_snapshot(), before)

        inactive = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': retired.pk,
                'description': 'Old trade.',
                'latitude': '12.500000',
                'longitude': '77.200000',
            },
            format='json',
        )
        self.assertEqual(inactive.status_code, 400)
        self.client.credentials()
        anonymous = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': self.category.pk,
                'description': 'Replace a switch.',
                'latitude': '12.500000',
                'longitude': '77.200000',
            },
            format='json',
        )
        self.assertEqual(anonymous.status_code, 401)
        self.auth(self.worker['token'])
        provider = self.client.post(
            '/api/v1/workers/daily-requests/mine/',
            {
                'category': self.category.pk,
                'description': 'Replace a switch.',
                'latitude': '12.500000',
                'longitude': '77.200000',
            },
            format='json',
        )
        self.assertEqual(provider.status_code, 201, provider.data)
        self.assertEqual(provider.data['status'], DailyServiceRequest.Status.AWAITING_PAYMENT)
        self.assertTrue(
            DailyServiceRequest.objects.filter(
                customer=self.worker['user'],
                description='Replace a switch.',
            ).exists()
        )
        self.assertEqual(
            VisitPayment.objects.filter(
                request__customer=self.worker['user'],
                request__description='Replace a switch.',
            ).count(),
            1,
        )
