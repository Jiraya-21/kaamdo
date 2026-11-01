"""Database engine selection. These tests do not open PostgreSQL or write SQLite."""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.database import (
    POSTGRES_ENGINE,
    SQLITE_ENGINE,
    database_settings,
    normalize_engine,
    sqlite_file,
)

BASE = Path('D:/kaamdo-settings-test-base')


class DatabaseSettingsTests(SimpleTestCase):
    def test_default_and_sqlite_always_use_the_project_sqlite_file(self):
        engine, databases = database_settings('', BASE, name='kaamdo_staging')
        sqlite_engine, sqlite_databases = database_settings(
            'sqlite',
            BASE,
            name='other.sqlite3',
            user='ignored',
            host='127.0.0.1',
            port='5433',
        )
        self.assertEqual(engine, 'sqlite')
        self.assertEqual(sqlite_engine, 'sqlite')
        self.assertEqual(databases['default']['ENGINE'], SQLITE_ENGINE)
        self.assertEqual(databases['default']['NAME'], sqlite_file(BASE))
        self.assertEqual(sqlite_databases['default']['NAME'], BASE / 'db.sqlite3')
        self.assertNotIn('kaamdo_staging', str(databases['default']['NAME']))
        self.assertNotEqual(sqlite_databases['default']['NAME'], BASE / 'other.sqlite3')

    def test_unknown_engine_does_not_fall_back_to_sqlite(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            database_settings('mysql', BASE)
        self.assertIn('sqlite or postgresql', str(caught.exception))
        self.assertEqual(normalize_engine('postgres'), 'postgresql')

    def test_postgresql_uses_a_database_name_not_a_file(self):
        engine, databases = database_settings(
            'postgresql',
            BASE,
            name='kaamdo_staging',
            user='kaamdo',
            password='unused-in-this-test',
            host='127.0.0.1',
            port='5433',
        )
        self.assertEqual(engine, 'postgresql')
        self.assertEqual(databases['default']['ENGINE'], POSTGRES_ENGINE)
        self.assertEqual(databases['default']['NAME'], 'kaamdo_staging')
        self.assertEqual(databases['default']['PORT'], '5433')
        self.assertNotIn('sqlite', databases['default']['ENGINE'])
        self.assertNotIn('db.sqlite3', str(databases['default']))

    def test_postgresql_refuses_a_sqlite_path_as_the_name(self):
        with self.assertRaises(ImproperlyConfigured):
            database_settings('postgresql', BASE, name='db.sqlite3', user='kaamdo')
        with self.assertRaises(ImproperlyConfigured):
            database_settings(
                'postgresql',
                BASE,
                name=str(BASE / 'db.sqlite3'),
                user='kaamdo',
            )
        with self.assertRaises(ImproperlyConfigured):
            database_settings('postgresql', BASE, name='kaamdo_staging', user='')
        with self.assertRaises(ImproperlyConfigured):
            database_settings('postgresql', BASE, name='', user='kaamdo')
