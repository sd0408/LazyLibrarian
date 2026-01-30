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

"""
Database migration framework for Bookbag of Holding.

This module provides a proper migration framework to replace the legacy
dbupgrade.py approach. It supports:
- Versioned migrations with up/down methods
- Migration discovery and registration
- Safe rollback support
- Migration logging and tracking
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

import bookbagofholding
from bookbagofholding import logger


class MigrationError(Exception):
    """Exception raised when a migration fails."""
    pass


class Migration(ABC):
    """Base class for database migrations.

    Each migration should inherit from this class and implement
    the up() method. The down() method is optional but recommended
    for rollback support.

    Attributes:
        version: The migration version number (must be unique)
        description: A brief description of what this migration does
        dependencies: Optional list of version numbers this depends on
    """

    version: int = 0
    description: str = ""
    dependencies: List[int] = []

    def __init__(self, db: Any):
        """Initialize the migration with a database connection.

        Args:
            db: Database connection object (DBConnection instance)
        """
        self.db = db
        self._log_file = None

    def set_log_file(self, log_file) -> None:
        """Set the log file for migration output.

        Args:
            log_file: File object to write log messages to
        """
        self._log_file = log_file

    def log(self, message: str) -> None:
        """Log a migration message.

        Args:
            message: The message to log
        """
        timestamp = time.ctime()
        log_message = "%s v%d: %s" % (timestamp, self.version, message)

        # Log to logger
        logger.debug(log_message)

        # Log to file if available
        if self._log_file:
            self._log_file.write(log_message + "\n")
            self._log_file.flush()

        # Update global progress message
        bookbagofholding.UPDATE_MSG = message

    def has_column(self, table: str, column: str) -> bool:
        """Check if a column exists in a table.

        Args:
            table: Table name
            column: Column name

        Returns:
            True if column exists, False otherwise
        """
        columns = self.db.select('PRAGMA table_info(%s)' % table)
        if not columns:
            return False
        for item in columns:
            if item[1] == column:
                return True
        return False

    def has_table(self, table: str) -> bool:
        """Check if a table exists.

        Args:
            table: Table name

        Returns:
            True if table exists, False otherwise
        """
        result = self.db.match(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table]
        )
        return result is not None

    def has_index(self, index_name: str) -> bool:
        """Check if an index exists.

        Args:
            index_name: Index name

        Returns:
            True if index exists, False otherwise
        """
        result = self.db.match(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            [index_name]
        )
        return result is not None

    def add_column(self, table: str, column: str, column_type: str,
                   default: Optional[str] = None) -> bool:
        """Add a column to a table if it doesn't exist.

        Args:
            table: Table name
            column: Column name
            column_type: Column type (TEXT, INTEGER, etc.)
            default: Optional default value

        Returns:
            True if column was added, False if it already exists
        """
        if self.has_column(table, column):
            return False

        sql = 'ALTER TABLE %s ADD COLUMN %s %s' % (table, column, column_type)
        if default is not None:
            sql += ' DEFAULT %s' % default

        self.db.action(sql)
        self.log("Added column %s to table %s" % (column, table))
        return True

    def create_index(self, table: str, columns: List[str],
                     unique: bool = False, index_name: Optional[str] = None) -> bool:
        """Create an index on a table.

        Args:
            table: Table name
            columns: List of column names to index
            unique: Whether the index should be unique
            index_name: Optional custom index name

        Returns:
            True if index was created, False if it already exists
        """
        if not index_name:
            index_name = '%s_%s_index' % (table, '_'.join(columns))

        if self.has_index(index_name):
            return False

        unique_str = 'UNIQUE ' if unique else ''
        column_str = ', '.join(columns)
        sql = 'CREATE %sINDEX %s ON %s (%s)' % (unique_str, index_name, table, column_str)

        self.db.action(sql)
        self.log("Created index %s on %s(%s)" % (index_name, table, column_str))
        return True

    @abstractmethod
    def up(self) -> None:
        """Apply the migration.

        This method must be implemented by subclasses.
        It should contain the forward migration logic.
        """
        pass

    def down(self) -> None:
        """Rollback the migration.

        This method is optional. Subclasses can override it
        to provide rollback support.

        Raises:
            MigrationError: If rollback is not supported
        """
        raise MigrationError(
            "Migration v%d does not support rollback" % self.version
        )


class MigrationRegistry:
    """Registry for database migrations.

    This class maintains a registry of all available migrations
    and provides methods to discover and retrieve them.
    """

    _migrations: Dict[int, Type[Migration]] = {}

    @classmethod
    def register(cls, migration_class: Type[Migration]) -> Type[Migration]:
        """Register a migration class.

        This can be used as a decorator:
            @MigrationRegistry.register
            class Migration0045(Migration):
                ...

        Args:
            migration_class: The migration class to register

        Returns:
            The migration class (for use as decorator)

        Raises:
            MigrationError: If version is invalid or duplicate
        """
        version = migration_class.version
        if version <= 0:
            raise MigrationError(
                "Migration %s has invalid version %d" %
                (migration_class.__name__, version)
            )
        if version in cls._migrations:
            raise MigrationError(
                "Duplicate migration version %d: %s and %s" %
                (version, cls._migrations[version].__name__, migration_class.__name__)
            )
        cls._migrations[version] = migration_class
        return migration_class

    @classmethod
    def get(cls, version: int) -> Optional[Type[Migration]]:
        """Get a migration by version.

        Args:
            version: The migration version number

        Returns:
            The migration class, or None if not found
        """
        return cls._migrations.get(version)

    @classmethod
    def get_all(cls) -> Dict[int, Type[Migration]]:
        """Get all registered migrations.

        Returns:
            Dictionary mapping version numbers to migration classes
        """
        return cls._migrations.copy()

    @classmethod
    def get_versions(cls) -> List[int]:
        """Get all registered version numbers in sorted order.

        Returns:
            Sorted list of version numbers
        """
        return sorted(cls._migrations.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered migrations.

        Primarily for testing purposes.
        """
        cls._migrations.clear()


# Decorator for registering migrations
def migration(version: int, description: str = "") -> Callable[[Type[Migration]], Type[Migration]]:
    """Decorator to register a migration.

    Usage:
        @migration(45, "Add audiobook chapters table")
        class AddAudiobookChapters(Migration):
            ...

    Args:
        version: The migration version number
        description: Description of the migration

    Returns:
        Decorator function
    """
    def decorator(cls: Type[Migration]) -> Type[Migration]:
        cls.version = version
        cls.description = description
        return MigrationRegistry.register(cls)
    return decorator


class MigrationRunner:
    """Runs database migrations.

    This class handles:
    - Determining which migrations need to run
    - Running migrations in order
    - Tracking progress and logging
    - Handling errors and rollback
    """

    def __init__(self, db: Any, log_dir: Optional[str] = None):
        """Initialize the migration runner.

        Args:
            db: Database connection object
            log_dir: Directory for migration logs (default: config LOGDIR)
        """
        self.db = db
        self.log_dir = log_dir or bookbagofholding.CONFIG.get('LOGDIR', '')
        self._log_file = None

    def get_current_version(self) -> int:
        """Get the current database version.

        Returns:
            Current version number, or 0 if not set
        """
        result = self.db.match('PRAGMA user_version')
        if result and result[0]:
            value = str(result[0])
            if value.isdigit():
                return int(value)
        return 0

    def set_version(self, version: int) -> None:
        """Set the database version.

        Args:
            version: Version number to set
        """
        self.db.action('PRAGMA user_version=%d' % version)

    def get_pending_migrations(self, target_version: Optional[int] = None) -> List[Type[Migration]]:
        """Get migrations that need to be run.

        Args:
            target_version: Target version (default: latest)

        Returns:
            List of migration classes to run, in order
        """
        current = self.get_current_version()
        versions = MigrationRegistry.get_versions()

        if target_version is None:
            target_version = max(versions) if versions else 0

        pending = []
        for version in versions:
            if current < version <= target_version:
                migration_class = MigrationRegistry.get(version)
                if migration_class:
                    pending.append(migration_class)

        return pending

    def needs_upgrade(self, target_version: Optional[int] = None) -> bool:
        """Check if database needs upgrading.

        Args:
            target_version: Target version (default: latest)

        Returns:
            True if upgrades are needed
        """
        return len(self.get_pending_migrations(target_version)) > 0

    def run(self, target_version: Optional[int] = None) -> bool:
        """Run pending migrations.

        Args:
            target_version: Target version (default: latest)

        Returns:
            True if all migrations succeeded

        Raises:
            MigrationError: If a migration fails
        """
        pending = self.get_pending_migrations(target_version)
        if not pending:
            logger.debug("No migrations to run")
            return True

        current = self.get_current_version()
        target = target_version or (max(m.version for m in pending) if pending else current)

        # Open log file
        log_path = os.path.join(self.log_dir, 'dbupgrade.log') if self.log_dir else None
        if log_path:
            self._log_file = open(log_path, 'a')

        try:
            bookbagofholding.UPDATE_MSG = 'Updating database from version %d to %d' % (current, target)
            logger.info(bookbagofholding.UPDATE_MSG)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))

            for migration_class in pending:
                self._run_migration(migration_class)

            # Set final version
            self.set_version(target)

            # Vacuum the database
            bookbagofholding.UPDATE_MSG = 'Cleaning Database'
            logger.info(bookbagofholding.UPDATE_MSG)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))
            self.db.action('vacuum')

            bookbagofholding.UPDATE_MSG = 'Database updated to version %d' % target
            logger.info(bookbagofholding.UPDATE_MSG)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))

            return True

        except Exception as e:
            msg = 'Migration failed: %s' % str(e)
            logger.error(msg)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), msg))
            raise MigrationError(msg) from e

        finally:
            bookbagofholding.UPDATE_MSG = ''
            if self._log_file:
                self._log_file.close()
                self._log_file = None

    def _run_migration(self, migration_class: Type[Migration]) -> None:
        """Run a single migration.

        Args:
            migration_class: The migration class to run

        Raises:
            MigrationError: If the migration fails
        """
        migration = migration_class(self.db)
        migration.set_log_file(self._log_file)

        bookbagofholding.UPDATE_MSG = 'Running migration v%d: %s' % (
            migration.version, migration.description or 'No description'
        )
        logger.info(bookbagofholding.UPDATE_MSG)
        if self._log_file:
            self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))

        try:
            migration.up()
            migration.log("complete")
        except Exception as e:
            msg = 'Migration v%d failed: %s %s' % (migration.version, type(e).__name__, str(e))
            logger.error(msg)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), msg))
            raise MigrationError(msg) from e

    def rollback(self, target_version: int) -> bool:
        """Rollback to a specific version.

        Args:
            target_version: Version to rollback to

        Returns:
            True if rollback succeeded

        Raises:
            MigrationError: If rollback fails or is not supported
        """
        current = self.get_current_version()
        if target_version >= current:
            logger.debug("No rollback needed")
            return True

        versions = MigrationRegistry.get_versions()
        rollback_versions = [v for v in versions if target_version < v <= current]
        rollback_versions.sort(reverse=True)  # Rollback in reverse order

        # Open log file
        log_path = os.path.join(self.log_dir, 'dbupgrade.log') if self.log_dir else None
        if log_path:
            self._log_file = open(log_path, 'a')

        try:
            bookbagofholding.UPDATE_MSG = 'Rolling back database from version %d to %d' % (current, target_version)
            logger.info(bookbagofholding.UPDATE_MSG)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))

            for version in rollback_versions:
                migration_class = MigrationRegistry.get(version)
                if migration_class:
                    migration = migration_class(self.db)
                    migration.set_log_file(self._log_file)

                    bookbagofholding.UPDATE_MSG = 'Rolling back migration v%d' % version
                    logger.info(bookbagofholding.UPDATE_MSG)
                    migration.down()
                    migration.log("rollback complete")

            self.set_version(target_version)

            bookbagofholding.UPDATE_MSG = 'Database rolled back to version %d' % target_version
            logger.info(bookbagofholding.UPDATE_MSG)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), bookbagofholding.UPDATE_MSG))

            return True

        except Exception as e:
            msg = 'Rollback failed: %s' % str(e)
            logger.error(msg)
            if self._log_file:
                self._log_file.write("%s: %s\n" % (time.ctime(), msg))
            raise MigrationError(msg) from e

        finally:
            bookbagofholding.UPDATE_MSG = ''
            if self._log_file:
                self._log_file.close()
                self._log_file = None
