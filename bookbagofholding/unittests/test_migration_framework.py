#  This file is part of Bookbag of Holding.
#  Bookbag of Holding is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for the database migration framework."""

import unittest
from unittest.mock import Mock, MagicMock, patch

from bookbagofholding.database_v2.migration_framework import (
    Migration,
    MigrationRegistry,
    MigrationRunner,
    MigrationError,
    migration,
)


class TestMigration(unittest.TestCase):
    """Test cases for the Migration base class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_db.select = Mock(return_value=[])
        self.mock_db.match = Mock(return_value=None)
        self.mock_db.action = Mock()

    def test_migration_has_column_true(self):
        """has_column should return True when column exists."""
        self.mock_db.select.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),
            (1, 'name', 'TEXT', 0, None, 0),
        ]

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        self.assertTrue(m.has_column('test_table', 'name'))

    def test_migration_has_column_false(self):
        """has_column should return False when column doesn't exist."""
        self.mock_db.select.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),
        ]

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        self.assertFalse(m.has_column('test_table', 'name'))

    def test_migration_has_table_true(self):
        """has_table should return True when table exists."""
        self.mock_db.match.return_value = {'name': 'test_table'}

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        self.assertTrue(m.has_table('test_table'))

    def test_migration_has_table_false(self):
        """has_table should return False when table doesn't exist."""
        self.mock_db.match.return_value = None

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        self.assertFalse(m.has_table('nonexistent'))

    def test_migration_add_column_new(self):
        """add_column should add column when it doesn't exist."""
        self.mock_db.select.return_value = [(0, 'id', 'INTEGER', 0, None, 1)]

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        result = m.add_column('test_table', 'new_col', 'TEXT')

        self.assertTrue(result)
        self.mock_db.action.assert_called_once()
        call_args = self.mock_db.action.call_args[0][0]
        self.assertIn('ALTER TABLE test_table ADD COLUMN new_col TEXT', call_args)

    def test_migration_add_column_exists(self):
        """add_column should return False when column exists."""
        self.mock_db.select.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),
            (1, 'existing_col', 'TEXT', 0, None, 0),
        ]

        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        result = m.add_column('test_table', 'existing_col', 'TEXT')

        self.assertFalse(result)
        self.mock_db.action.assert_not_called()

    def test_migration_down_not_implemented(self):
        """down() should raise MigrationError by default."""
        class TestMigration(Migration):
            version = 1
            def up(self):
                pass

        m = TestMigration(self.mock_db)
        with self.assertRaises(MigrationError):
            m.down()


class TestMigrationRegistry(unittest.TestCase):
    """Test cases for MigrationRegistry."""

    def setUp(self):
        """Clear registry before each test."""
        MigrationRegistry.clear()

    def tearDown(self):
        """Clear registry after each test."""
        MigrationRegistry.clear()

    def test_register_migration(self):
        """register should add migration to registry."""
        class TestMigration(Migration):
            version = 42
            def up(self):
                pass

        MigrationRegistry.register(TestMigration)
        self.assertIn(42, MigrationRegistry.get_versions())
        self.assertEqual(MigrationRegistry.get(42), TestMigration)

    def test_register_duplicate_version(self):
        """register should raise error for duplicate version."""
        class Migration1(Migration):
            version = 1
            def up(self):
                pass

        class Migration2(Migration):
            version = 1
            def up(self):
                pass

        MigrationRegistry.register(Migration1)
        with self.assertRaises(MigrationError):
            MigrationRegistry.register(Migration2)

    def test_register_invalid_version(self):
        """register should raise error for invalid version."""
        class InvalidMigration(Migration):
            version = 0
            def up(self):
                pass

        with self.assertRaises(MigrationError):
            MigrationRegistry.register(InvalidMigration)

    def test_get_versions_sorted(self):
        """get_versions should return sorted list."""
        class Migration5(Migration):
            version = 5
            def up(self):
                pass

        class Migration2(Migration):
            version = 2
            def up(self):
                pass

        class Migration8(Migration):
            version = 8
            def up(self):
                pass

        MigrationRegistry.register(Migration5)
        MigrationRegistry.register(Migration2)
        MigrationRegistry.register(Migration8)

        versions = MigrationRegistry.get_versions()
        self.assertEqual(versions, [2, 5, 8])

    def test_get_nonexistent(self):
        """get should return None for nonexistent version."""
        self.assertIsNone(MigrationRegistry.get(999))


class TestMigrationDecorator(unittest.TestCase):
    """Test cases for the @migration decorator."""

    def setUp(self):
        """Clear registry before each test."""
        MigrationRegistry.clear()

    def tearDown(self):
        """Clear registry after each test."""
        MigrationRegistry.clear()

    def test_migration_decorator(self):
        """@migration decorator should set version and register."""
        @migration(99, "Test migration")
        class TestMigration(Migration):
            def up(self):
                pass

        self.assertEqual(TestMigration.version, 99)
        self.assertEqual(TestMigration.description, "Test migration")
        self.assertEqual(MigrationRegistry.get(99), TestMigration)


class TestMigrationRunner(unittest.TestCase):
    """Test cases for MigrationRunner."""

    def setUp(self):
        """Set up test fixtures."""
        MigrationRegistry.clear()
        self.mock_db = Mock()
        self.mock_db.match = Mock(return_value=[0])
        self.mock_db.action = Mock()

    def tearDown(self):
        """Clear registry after each test."""
        MigrationRegistry.clear()

    def test_get_current_version_zero(self):
        """get_current_version should return 0 for new database."""
        self.mock_db.match.return_value = [0]

        runner = MigrationRunner(self.mock_db, log_dir='')
        version = runner.get_current_version()

        self.assertEqual(version, 0)

    def test_get_current_version_existing(self):
        """get_current_version should return stored version."""
        self.mock_db.match.return_value = [44]

        runner = MigrationRunner(self.mock_db, log_dir='')
        version = runner.get_current_version()

        self.assertEqual(version, 44)

    def test_needs_upgrade_true(self):
        """needs_upgrade should return True when migrations pending."""
        self.mock_db.match.return_value = [0]

        class Migration1(Migration):
            version = 1
            def up(self):
                pass

        MigrationRegistry.register(Migration1)

        runner = MigrationRunner(self.mock_db, log_dir='')
        self.assertTrue(runner.needs_upgrade())

    def test_needs_upgrade_false(self):
        """needs_upgrade should return False when up to date."""
        self.mock_db.match.return_value = [5]

        class Migration5(Migration):
            version = 5
            def up(self):
                pass

        MigrationRegistry.register(Migration5)

        runner = MigrationRunner(self.mock_db, log_dir='')
        self.assertFalse(runner.needs_upgrade())

    def test_get_pending_migrations(self):
        """get_pending_migrations should return correct migrations."""
        self.mock_db.match.return_value = [2]

        class Migration1(Migration):
            version = 1
            def up(self):
                pass

        class Migration3(Migration):
            version = 3
            def up(self):
                pass

        class Migration5(Migration):
            version = 5
            def up(self):
                pass

        MigrationRegistry.register(Migration1)
        MigrationRegistry.register(Migration3)
        MigrationRegistry.register(Migration5)

        runner = MigrationRunner(self.mock_db, log_dir='')
        pending = runner.get_pending_migrations()

        # Should only include migrations > current version (2)
        self.assertEqual(len(pending), 2)
        self.assertIn(Migration3, pending)
        self.assertIn(Migration5, pending)
        self.assertNotIn(Migration1, pending)

    @patch('bookbagofholding.database_v2.migration_framework.bookbagofholding')
    def test_run_executes_migrations(self, mock_ll):
        """run should execute pending migrations in order."""
        mock_ll.UPDATE_MSG = ''
        mock_ll.CONFIG = {'LOGDIR': ''}
        self.mock_db.match.return_value = [0]

        executed = []

        class Migration1(Migration):
            version = 1
            def up(self):
                executed.append(1)

        class Migration2(Migration):
            version = 2
            def up(self):
                executed.append(2)

        MigrationRegistry.register(Migration1)
        MigrationRegistry.register(Migration2)

        runner = MigrationRunner(self.mock_db, log_dir='')
        runner.run()

        self.assertEqual(executed, [1, 2])


if __name__ == '__main__':
    unittest.main()
