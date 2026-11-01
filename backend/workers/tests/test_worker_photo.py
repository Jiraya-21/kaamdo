"""Owner-only worker profile photo upload, validation, and public URL."""

from io import BytesIO
import os
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from accounts.models import AccountCapability, Capability, User
from workers.models import ServiceProviderVerification, WorkerProfile
from workers.photos import (
    PHOTO_MIGRATION_REQUIRED,
    WORKER_PHOTO_MAX_BYTES,
    reset_worker_photo_column_cache,
)


def image_bytes(fmt='JPEG', size=(48, 48), color=(20, 90, 40)):
    buffer = BytesIO()
    image = Image.new('RGB', size, color)
    save_format = 'JPEG' if fmt == 'JPG' else fmt
    image.save(buffer, format=save_format)
    return buffer.getvalue()


def upload(name, payload, content_type):
    return SimpleUploadedFile(name, payload, content_type=content_type)


class WorkerProfilePhotoTests(APITestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media.cleanup)

        self.worker = self.make_user('9876543299', Capability.SERVICE_PROVIDER, 'Basavaraj', 'Patil')
        self.other = self.make_user('9988001199', Capability.SERVICE_PROVIDER, 'Other', 'Worker')
        self.customer = self.make_user('9123456799', Capability.CUSTOMER, 'Asha', 'Rao')
        self.worker_token = Token.objects.create(user=self.worker)
        self.other_token = Token.objects.create(user=self.other)
        self.customer_token = Token.objects.create(user=self.customer)
        self.photo_url = '/api/v1/workers/profile/photo/'
        self.profile_url = '/api/v1/workers/profile/'

    def make_user(self, phone, capability, first_name, last_name):
        user = User.objects.create_user(
            username=phone,
            password='SafePass!234',
            phone_number=phone,
            active_mode=capability,
            first_name=first_name,
            last_name=last_name,
        )
        AccountCapability.objects.create(user=user, code=capability)
        return user

    def payload(self, **overrides):
        data = {
            'skills': ['Plumbing'],
            'experience_years': 4,
            'bio': 'Household plumbing and pipe repair.',
            'service_rate': '350.00',
            'pricing_basis': 'hourly',
            'district': 'Mandya',
            'locality': 'Town centre',
            'availability': 'available',
            'publication_status': 'draft',
        }
        data.update(overrides)
        return data

    def create_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        created = self.client.post(self.profile_url, self.payload(), format='json')
        self.assertEqual(created.status_code, 201)
        return created

    def test_missing_photo_serializes_as_null_without_storage_paths(self):
        created = self.create_profile()
        own = self.client.get(self.profile_url)

        self.assertIsNone(created.data['photo_url'])
        self.assertIsNone(own.data['photo_url'])
        self.assertNotIn('photo', created.data)
        self.assertNotIn('photo', own.data)
        blob = str(own.data)
        self.assertNotIn(self.media.name, blob)
        self.assertNotIn('\\media\\', blob)

    def test_owner_can_upload_replace_and_remove_a_photo(self):
        created = self.create_profile()
        first = self.client.post(
            self.photo_url,
            {'photo': upload('face.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(str(first.data['photo_url']).startswith('http'))
        self.assertIn('/media/worker_photos/', first.data['photo_url'])
        self.assertNotIn(self.media.name, str(first.data))
        self.assertNotIn('face.jpg', first.data['photo_url'])
        first_name = WorkerProfile.objects.get(pk=created.data['id']).photo.name

        second = self.client.post(
            self.photo_url,
            {'photo': upload('next.png', image_bytes('PNG'), 'image/png')},
            format='multipart',
        )
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.data['photo_url'], second.data['photo_url'])
        profile = WorkerProfile.objects.get(pk=created.data['id'])
        self.assertTrue(profile.photo.name.endswith('.png'))
        self.assertFalse(profile.photo.storage.exists(first_name))

        removed = self.client.delete(self.photo_url)
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.data['photo_url'])
        profile.refresh_from_db()
        self.assertFalse(bool(profile.photo))

    def test_public_listing_returns_photo_url_without_private_fields(self):
        created = self.create_profile()
        ServiceProviderVerification.objects.update_or_create(
            user=self.worker,
            defaults={'status': ServiceProviderVerification.Status.APPROVED},
        )
        self.client.post(
            self.photo_url,
            {'photo': upload('public.webp', image_bytes('WEBP'), 'image/webp')},
            format='multipart',
        )
        published = self.client.patch(
            self.profile_url,
            {'publication_status': 'published'},
            format='json',
        )
        self.assertEqual(published.status_code, 200)

        self.client.credentials()
        listing = self.client.get('/api/v1/workers/')
        detail = self.client.get(f'/api/v1/workers/{created.data["id"]}/')
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        public_row = listing.data['results'][0]
        for payload in (public_row, detail.data):
            self.assertTrue(str(payload['photo_url']).startswith('http'))
            self.assertNotIn('photo', payload)
            self.assertNotIn('phone_number', payload)
            self.assertNotIn('email', payload)
            self.assertNotIn('password', payload)
            self.assertNotIn(self.media.name, str(payload))

    def test_rejected_files_and_non_owners(self):
        self.create_profile()
        oversized = self.client.post(
            self.photo_url,
            {'photo': upload('big.jpg', b'\xff\xd8\xff' + (b'0' * (WORKER_PHOTO_MAX_BYTES + 1)), 'image/jpeg')},
            format='multipart',
        )
        svg = self.client.post(
            self.photo_url,
            {'photo': upload('icon.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', 'image/svg+xml')},
            format='multipart',
        )
        text = self.client.post(
            self.photo_url,
            {'photo': upload('notes.txt', b'not an image at all', 'text/plain')},
            format='multipart',
        )
        gif = self.client.post(
            self.photo_url,
            {'photo': upload('loop.gif', image_bytes('GIF'), 'image/gif')},
            format='multipart',
        )
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(svg.status_code, 400)
        self.assertEqual(text.status_code, 400)
        self.assertEqual(gif.status_code, 400)
        self.assertIsNone(WorkerProfile.objects.get(user=self.worker).photo.name or None)
        profile = WorkerProfile.objects.get(user=self.worker)
        self.assertFalse(bool(profile.photo))

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        other_missing = self.client.post(
            self.photo_url,
            {'photo': upload('other.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(other_missing.status_code, 404)
        self.assertFalse(bool(WorkerProfile.objects.get(user=self.worker).photo))

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        customer = self.client.post(
            self.photo_url,
            {'photo': upload('cust.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(customer.status_code, 403)

        self.client.credentials()
        anonymous = self.client.post(
            self.photo_url,
            {'photo': upload('anon.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(anonymous.status_code, 401)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        without_photo = self.client.delete(self.photo_url)
        self.assertEqual(without_photo.status_code, 200)

        WorkerProfile.objects.filter(user=self.worker).delete()
        missing = self.client.post(
            self.photo_url,
            {'photo': upload('late.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(missing.status_code, 404)

    def test_photo_files_land_only_in_the_temporary_media_root(self):
        self.create_profile()
        uploaded = self.client.post(
            self.photo_url,
            {'photo': upload('kept.jpg', image_bytes(), 'image/jpeg')},
            format='multipart',
        )
        self.assertEqual(uploaded.status_code, 200)
        stored = WorkerProfile.objects.get(user=self.worker).photo.path
        self.assertTrue(stored.startswith(self.media.name))
        self.assertTrue(os.path.isfile(stored))
        self.assertNotIn('backend' + os.sep + 'media', stored)

    def test_unmigrated_photo_column_does_not_break_public_lists_or_claim_upload(self):
        created = self.create_profile()
        ServiceProviderVerification.objects.update_or_create(
            user=self.worker,
            defaults={'status': ServiceProviderVerification.Status.APPROVED},
        )
        self.client.patch(self.profile_url, {'publication_status': 'published'}, format='json')
        missing = patch('workers.photos.worker_photo_column_ready', return_value=False)
        missing_model = patch('workers.models.worker_photo_column_ready', return_value=False)
        missing_view = patch('workers.views.worker_photo_column_ready', return_value=False)
        with missing, missing_model, missing_view:
            self.client.credentials()
            listing = self.client.get('/api/v1/workers/')
            detail = self.client.get(f'/api/v1/workers/{created.data["id"]}/')
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
            refused = self.client.post(
                self.photo_url,
                {'photo': upload('late.jpg', image_bytes(), 'image/jpeg')},
                format='multipart',
            )
            removed = self.client.delete(self.photo_url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(listing.data['results'][0]['photo_url'])
        self.assertIsNone(detail.data['photo_url'])
        self.assertEqual(refused.status_code, 503)
        self.assertEqual(removed.status_code, 503)
        self.assertEqual(refused.data['detail'], PHOTO_MIGRATION_REQUIRED)


class UnmigratedPhotoColumnTests(TransactionTestCase):
    """The local SQLite file may not have workers.0006. Lists must still load."""

    def test_public_list_loads_after_the_photo_column_is_removed(self):
        from django.db import connection

        worker = User.objects.create_user(
            username='9876500099',
            password='SafePass!234',
            phone_number='9876500099',
            active_mode=Capability.SERVICE_PROVIDER,
            first_name='Unmigrated',
            last_name='Worker',
        )
        AccountCapability.objects.create(user=worker, code=Capability.SERVICE_PROVIDER)
        ServiceProviderVerification.objects.update_or_create(
            user=worker,
            defaults={'status': ServiceProviderVerification.Status.APPROVED},
        )
        WorkerProfile.objects.create(
            user=worker,
            experience_years=2,
            bio='Pipe repair.',
            service_rate='200.00',
            pricing_basis='hourly',
            district='Mysuru',
            locality='Centre',
            availability='available',
            publication_status='published',
        )
        with connection.schema_editor() as editor:
            editor.remove_field(WorkerProfile, WorkerProfile._meta.get_field('photo'))
        reset_worker_photo_column_cache()
        try:
            listing = APIClient().get('/api/v1/workers/')
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.data['count'], 1)
            self.assertIsNone(listing.data['results'][0]['photo_url'])
        finally:
            reset_worker_photo_column_cache()
