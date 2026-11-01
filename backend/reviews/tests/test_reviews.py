"""Reviews are not implemented until completed-transaction rules are approved."""

from rest_framework.test import APITestCase


class ReviewsNotImplementedTests(APITestCase):
    def test_reviews_routes_are_not_implemented(self):
        response = self.client.get('/api/v1/reviews/')
        self.assertEqual(response.status_code, 404)
