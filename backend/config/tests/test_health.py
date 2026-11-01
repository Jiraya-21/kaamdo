"""Health check. This does not open the local SQLite file as a test database write."""

from rest_framework.test import APITestCase


class HealthViewTests(APITestCase):
    def test_healthz_is_public_and_does_not_expose_settings(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status': 'ok'})
        blob = str(response.data).lower()
        self.assertNotIn('secret', blob)
        self.assertNotIn('password', blob)
        self.assertNotIn('otp', blob)
        self.assertNotIn('debug', blob)
