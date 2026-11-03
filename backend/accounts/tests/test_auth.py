"""
Accounts API tests.
Registration, login, logout, and the current-user endpoint.
"""

from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import AccountCapability, Capability, PhoneOtpChallenge, User
from accounts.permissions import HasCapability


class AccountsApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def register(self, **overrides):
        payload = {
            'phone_number': '9876543210',
            'password': 'SafePass!234',
            'role': 'worker',
            'full_name': 'Basavaraj Patil',
        }
        payload.update(overrides)
        return self.client.post('/api/v1/auth/register/', payload, format='json')

    def test_register_creates_hashed_password_and_token(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone_number='9876543210')
        self.assertEqual(user.username, '9876543210')
        self.assertEqual(user.capability_codes(), [Capability.SERVICE_PROVIDER, Capability.CUSTOMER])
        self.assertEqual(user.active_mode, Capability.SERVICE_PROVIDER)
        self.assertEqual(user.first_name, 'Basavaraj')
        self.assertEqual(user.last_name, 'Patil')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(check_password('SafePass!234', user.password))
        self.assertNotIn('password', response.data['user'])
        self.assertNotIn('role', response.data['user'])
        self.assertNotIn('is_staff', response.data['user'])
        self.assertEqual(response.data['token'], Token.objects.get(user=user).key)
        self.assertEqual(response.data['user']['capabilities'], ['service_provider', 'customer'])
        self.assertEqual(response.data['user']['active_mode'], 'service_provider')

    def test_register_rejects_duplicate_phone(self):
        self.register()
        response = self.register(full_name='Another Person')

        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_register_rejects_phone_that_matches_existing_username(self):
        User.objects.create_user(username='9876543210', password='SafePass!234')

        response = self.register()

        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.data)

    def test_register_rejects_invalid_password(self):
        response = self.register(password='123')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_register_rejects_unknown_role_and_ignores_privileges(self):
        response = self.register(role='farmer', is_superuser=True, is_staff=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn('role', response.data)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_login_returns_token_and_hides_bad_credentials(self):
        self.register()

        success = self.client.post(
            '/api/v1/auth/login/',
            {'phone_number': '9876543210', 'password': 'SafePass!234'},
            format='json',
        )
        failure = self.client.post(
            '/api/v1/auth/login/',
            {'phone_number': '9876543210', 'password': 'wrong-password'},
            format='json',
        )
        missing = self.client.post(
            '/api/v1/auth/login/',
            {'phone_number': '9123456780', 'password': 'SafePass!234'},
            format='json',
        )

        self.assertEqual(success.status_code, 200)
        self.assertEqual(success.data['user']['phone_number'], '9876543210')
        self.assertTrue(success.data['token'])
        self.assertNotIn('SafePass!234', str(success.data))
        self.assertEqual(failure.status_code, 401)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(failure.data['detail'], missing.data['detail'])
        self.assertNotIn('wrong-password', str(failure.data))

    def test_logout_deletes_token(self):
        registered = self.register()
        token = registered.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        logout = self.client.post('/api/v1/auth/logout/', {}, format='json')
        me = self.client.get('/api/v1/auth/me/')

        self.assertEqual(logout.status_code, 204)
        self.assertFalse(Token.objects.filter(key=token).exists())
        self.assertEqual(me.status_code, 401)

    def test_me_requires_authentication_and_returns_profile(self):
        anonymous = self.client.get('/api/v1/auth/me/')
        registered = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        me = self.client.get('/api/v1/auth/me/')

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['phone_number'], '9876543210')
        self.assertEqual(me.data['full_name'], 'Basavaraj Patil')
        self.assertEqual(me.data['capabilities'], ['service_provider', 'customer'])
        self.assertEqual(me.data['service_provider']['verification_status'], 'not_submitted')
        self.assertNotIn('password', me.data)
        self.assertNotIn('is_superuser', me.data)
        self.assertNotIn('is_staff', me.data)
        self.assertIsNone(me.data['test_payment'])

    def test_logout_requires_authentication(self):
        response = self.client.post('/api/v1/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_register_accepts_several_capabilities_and_ignores_staff_flags(self):
        response = self.register(
            role='customer',
            capabilities=['customer', 'equipment_owner', 'customer'],
            active_mode='service_provider',
            is_superuser=True,
            is_staff=True,
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone_number='9876543210')
        self.assertEqual(user.capability_codes(), ['customer', 'equipment_owner'])
        self.assertEqual(user.active_mode, Capability.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotIn('is_staff', response.data['user'])

    def test_capability_enable_does_not_change_mode_or_token(self):
        registered = self.register(role='customer')
        token = registered.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        enabled = self.client.post(
            '/api/v1/auth/capabilities/',
            {'capability': 'job_seeker', 'is_staff': True},
            format='json',
        )
        again = self.client.post(
            '/api/v1/auth/capabilities/',
            {'capability': 'job_seeker'},
            format='json',
        )

        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(enabled.data['active_mode'], 'customer')
        self.assertEqual(enabled.data['capabilities'], ['customer', 'job_seeker'])
        self.assertEqual(again.data['capabilities'], ['customer', 'job_seeker'])
        self.assertEqual(AccountCapability.objects.filter(code='job_seeker').count(), 1)
        self.assertFalse(User.objects.get(phone_number='9876543210').is_staff)
        self.assertEqual(Token.objects.get(key=token).user.phone_number, '9876543210')

    def test_active_mode_switches_without_granting_a_capability(self):
        registered = self.register(capabilities=['customer', 'employer'])
        token = registered.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        denied = self.client.patch(
            '/api/v1/auth/mode/',
            {'active_mode': 'equipment_owner'},
            format='json',
        )
        switched = self.client.patch(
            '/api/v1/auth/mode/',
            {'active_mode': 'employer'},
            format='json',
        )
        me = self.client.get('/api/v1/auth/me/')

        self.assertEqual(denied.status_code, 400)
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.data['active_mode'], 'employer')
        self.assertEqual(switched.data['capabilities'], ['customer', 'employer'])
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['active_mode'], 'employer')
        self.assertTrue(Token.objects.filter(key=token).exists())

    def test_invalid_token_cannot_read_the_current_user(self):
        registered = self.register()
        valid_token = registered.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token not-a-real-token')

        me = self.client.get('/api/v1/auth/me/')
        logout = self.client.post('/api/v1/auth/logout/', {}, format='json')

        self.assertEqual(me.status_code, 401)
        self.assertEqual(logout.status_code, 401)
        self.assertTrue(Token.objects.filter(key=valid_token).exists())

    def test_logout_removes_only_the_current_token(self):
        first = self.register()
        second = self.register(phone_number='9123456780', full_name='Asha Rao')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {first.data["token"]}')

        logout = self.client.post('/api/v1/auth/logout/', {}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {second.data["token"]}')
        me = self.client.get('/api/v1/auth/me/')

        self.assertEqual(logout.status_code, 204)
        self.assertFalse(Token.objects.filter(key=first.data['token']).exists())
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['phone_number'], '9123456780')

    def test_permission_class_checks_the_database_capability(self):
        response = self.register(role='customer')
        user = User.objects.get(phone_number='9876543210')
        request = type('Request', (), {'user': user})()
        permission = type(
            'NeedsEquipment',
            (HasCapability,),
            {'required_capability': Capability.EQUIPMENT_OWNER},
        )()

        self.assertFalse(permission.has_permission(request, None))
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')
        self.client.post(
            '/api/v1/auth/capabilities/',
            {'capability': 'equipment_owner'},
            format='json',
        )
        user.refresh_from_db()
        self.assertTrue(permission.has_permission(request, None))

    @override_settings(DEBUG=True, OTP_DELIVERY='development')
    def test_otp_rejects_a_wrong_code_and_accepts_the_issued_code(self):
        registered = self.register(role='customer')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        sent = self.client.post(
            '/api/v1/auth/otp/send/',
            {'purpose': 'account'},
            format='json',
        )
        wrong = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': '000000'},
            format='json',
        )
        verified = self.client.post(
            '/api/v1/auth/otp/verify/',
            {'purpose': 'account', 'code': sent.data['dev_code']},
            format='json',
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['delivery'], 'development')
        self.assertNotIn(sent.data['dev_code'], sent.data['detail'])
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(verified.status_code, 200)

    @override_settings(DEBUG=True, OTP_DELIVERY='unconfigured')
    def test_unconfigured_otp_creates_no_code(self):
        registered = self.register(role='customer')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        sent = self.client.post('/api/v1/auth/otp/send/', {'purpose': 'account'}, format='json')
        self.assertEqual(sent.status_code, 400)
        self.assertNotIn('dev_code', sent.data)
        self.assertIn('not configured', str(sent.data).lower())
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    @override_settings(DEBUG=False, OTP_DELIVERY='development')
    def test_registered_otp_is_hidden_when_debug_is_off(self):
        registered = self.register(role='customer')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        sent = self.client.post('/api/v1/auth/otp/send/', {'purpose': 'account'}, format='json')
        self.assertEqual(sent.status_code, 400)
        self.assertNotIn('dev_code', sent.data)
        self.assertEqual(PhoneOtpChallenge.objects.count(), 0)

    def test_test_payment_flag_is_staff_only_and_off_by_default(self):
        registered = self.register(role='customer')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        ordinary = self.client.get('/api/v1/auth/me/')
        staff = User.objects.create_user(
            username='9000000999',
            password='SafePass!234',
            phone_number='9000000999',
            is_staff=True,
        )
        staff_token = Token.objects.create(user=staff)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')
        staff_off = self.client.get('/api/v1/auth/me/')
        with override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='test_bypass'):
            staff_on = self.client.get('/api/v1/auth/me/')
        with override_settings(DEBUG=False, KAAMDO_VISIT_PAYMENT='test_bypass'):
            staff_prod = self.client.get('/api/v1/auth/me/')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {registered.data["token"]}')
        with override_settings(DEBUG=True, KAAMDO_VISIT_PAYMENT='test_bypass'):
            ordinary_on = self.client.get('/api/v1/auth/me/')

        self.assertEqual(ordinary.status_code, 200)
        self.assertIsNone(ordinary.data['test_payment'])
        self.assertNotIn('is_staff', ordinary.data)
        self.assertIsNone(staff_off.data['test_payment'])
        self.assertEqual(staff_on.data['test_payment']['enabled'], True)
        self.assertEqual(staff_on.data['test_payment']['money_received'], False)
        self.assertIn('Inspection fee paid', staff_on.data['test_payment']['label'])
        self.assertNotIn('is_staff', staff_on.data)
        self.assertIsNone(staff_prod.data['test_payment'])
        self.assertIsNone(ordinary_on.data['test_payment'])
