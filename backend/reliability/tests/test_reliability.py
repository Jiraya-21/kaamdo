"""Reliability scores are not implemented until scoring rules are approved."""

from rest_framework.test import APITestCase


class ReliabilityNotImplementedTests(APITestCase):
    def test_reliability_routes_are_not_implemented(self):
        response = self.client.get('/api/v1/reliability/')
        self.assertEqual(response.status_code, 404)
