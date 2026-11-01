"""Confirm code migrations apply on Django's isolated test database."""

from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase


class IsolatedMigrationTests(TestCase):
    def test_pending_application_migrations_are_applied_here_only(self):
        applied = set(MigrationRecorder.Migration.objects.values_list('app', 'name'))
        self.assertIn(('workers', '0006_workerprofile_photo'), applied)
        self.assertIn(('workers', '0007_dailyservicerequest_contact_phone'), applied)
        self.assertIn(('workers', '0008_daily_matching_state'), applied)
        self.assertIn(('jobs', '0003_application_decisions'), applied)
        self.assertIn(('notifications', '0001_initial'), applied)
        self.assertIn(('accounts', '0006_guest_phone_verification'), applied)
        self.assertIn(('locations', '0001_initial'), applied)
        self.assertIn(('locations', '0001_initial'), applied)
