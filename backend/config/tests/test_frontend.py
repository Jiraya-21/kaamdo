from django.test import SimpleTestCase


def _body(response):
    return b''.join(response.streaming_content)


class FrontendServeTests(SimpleTestCase):
    def test_home_serves_index_html(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'KaamDo', _body(response))

    def test_asset_path_is_served(self):
        response = self.client.get('/assets/js/config.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'resolveKaamdoApiBase', _body(response))

    def test_path_traversal_is_blocked(self):
        response = self.client.get('/../backend/config/settings.py')
        self.assertEqual(response.status_code, 404)
