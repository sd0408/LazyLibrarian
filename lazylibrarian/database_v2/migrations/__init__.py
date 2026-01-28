#  This file is part of Lazylibrarian.
#  Lazylibrarian is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

"""
Database migrations for LazyLibrarian.

This package contains individual migration modules. Each migration
is automatically registered when imported.

Migration naming convention:
    m0001_initial_schema.py
    m0002_add_author_column.py
    etc.

Usage:
    from lazylibrarian.database_v2 import MigrationRunner
    from lazylibrarian.database_v2.migrations import *  # Import all migrations

    runner = MigrationRunner(db)
    if runner.needs_upgrade():
        runner.run()
"""

# Import all migrations to register them
# New migrations should be added here
# from lazylibrarian.database.migrations import m0045_example
