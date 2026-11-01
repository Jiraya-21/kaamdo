"""In-app notifications. These tests do not send SMS or email."""

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import User
from notifications.models import InAppNotification
from notifications.services import notify_user


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notify-user',
            password='SafePass!234',
            phone_number='9000000701',
        )
        other = User.objects.create_user(
            username='notify-other',
            password='SafePass!234',
            phone_number='9000000702',
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.own = notify_user(
            self.user,
            kind='job_application_accepted',
            title='Application accepted',
            body='Your application for Shop assistant is now accepted.',
            payload={'job': 1, 'application': 2, 'status': 'accepted'},
        )
        notify_user(
            other,
            kind='job_application_rejected',
            title='Hidden',
            body='Should not appear.',
        )

    def test_list_returns_only_the_signed_in_users_rows(self):
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.own.pk)
        self.assertEqual(response.data[0]['kind'], 'job_application_accepted')
        self.assertIsNone(response.data[0]['read_at'])
        self.assertNotIn('9000000702', str(response.data))

    def test_owner_can_mark_read_and_others_cannot(self):
        marked = self.client.post(f'/api/v1/notifications/{self.own.pk}/read/')
        self.assertEqual(marked.status_code, 200)
        self.assertIsNotNone(marked.data['read_at'])
        stolen = InAppNotification.objects.exclude(user=self.user).first()
        missing = self.client.post(f'/api/v1/notifications/{stolen.pk}/read/')
        self.assertEqual(missing.status_code, 404)

    def test_anonymous_cannot_list(self):
        self.client.credentials()
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 401)
