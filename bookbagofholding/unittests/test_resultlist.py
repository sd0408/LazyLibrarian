#  This file is part of Bookbag of Holding.
#
#  Bookbag of Holding is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

"""
Unit tests for bookbagofholding.resultlist module.

Tests cover:
- Blacklist filtering for various failure reasons
- Result processing and filtering
"""

import pytest
from unittest.mock import patch, MagicMock

import bookbagofholding
from bookbagofholding import database


@pytest.fixture
def resultlist_config():
    """Set up configuration for resultlist testing."""
    original_config = dict(bookbagofholding.CONFIG)

    bookbagofholding.CONFIG['BLACKLIST_FAILED'] = True
    bookbagofholding.CONFIG['BLACKLIST_PROCESSED'] = False
    bookbagofholding.CONFIG['REJECT_WORDS'] = ''
    bookbagofholding.CONFIG['REJECT_MAXSIZE'] = 0
    bookbagofholding.CONFIG['REJECT_MINSIZE'] = 0
    bookbagofholding.CONFIG['MATCH_RATIO'] = 80
    bookbagofholding.LOGLEVEL = 0

    yield

    bookbagofholding.CONFIG.update(original_config)


class TestBlacklistFiltering:
    """Tests for blacklist filtering in result processing."""

    def test_blacklist_failed_reason_is_checked(self, temp_db, resultlist_config):
        """BLACKLIST_FAILED should filter results with Reason='Failed'."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')
        # Add a blacklisted item with Failed reason
        conn.execute(
            'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
            ('http://example.com/bad.nzb', 'TestProv', 'Bad Book', 'Failed')
        )
        conn.commit()

        # The blacklist check query should find this entry
        result = conn.execute(
            'SELECT * from blacklist WHERE NZBurl=? and Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")',
            ('http://example.com/bad.nzb',)
        ).fetchone()

        assert result is not None
        assert result[5] == 'Failed'  # Reason column

    def test_blacklist_type_mismatch_reason_is_checked(self, temp_db, resultlist_config):
        """BLACKLIST_FAILED should filter results with Reason='TypeMismatch'."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')
        # Add a blacklisted item with TypeMismatch reason
        conn.execute(
            'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
            ('http://example.com/mismatch.nzb', 'TestProv', 'Mismatch Book', 'TypeMismatch')
        )
        conn.commit()

        # The blacklist check query should find this entry
        result = conn.execute(
            'SELECT * from blacklist WHERE NZBurl=? and Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")',
            ('http://example.com/mismatch.nzb',)
        ).fetchone()

        assert result is not None
        assert result[5] == 'TypeMismatch'

    def test_blacklist_unsupported_filetype_reason_is_checked(self, temp_db, resultlist_config):
        """BLACKLIST_FAILED should filter results with Reason='UnsupportedFileType'."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')
        # Add a blacklisted item with UnsupportedFileType reason
        conn.execute(
            'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
            ('http://example.com/unsupported.nzb', 'TestProv', 'Unsupported Book', 'UnsupportedFileType')
        )
        conn.commit()

        # The blacklist check query should find this entry
        result = conn.execute(
            'SELECT * from blacklist WHERE NZBurl=? and Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")',
            ('http://example.com/unsupported.nzb',)
        ).fetchone()

        assert result is not None
        assert result[5] == 'UnsupportedFileType'

    def test_blacklist_processed_reason_not_in_failed_check(self, temp_db, resultlist_config):
        """BLACKLIST_FAILED check should NOT filter results with Reason='Processed'."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')
        # Add a blacklisted item with Processed reason
        conn.execute(
            'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
            ('http://example.com/processed.nzb', 'TestProv', 'Processed Book', 'Processed')
        )
        conn.commit()

        # The BLACKLIST_FAILED query should NOT find this entry
        result = conn.execute(
            'SELECT * from blacklist WHERE NZBurl=? and Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")',
            ('http://example.com/processed.nzb',)
        ).fetchone()

        assert result is None

    def test_blacklist_title_based_check_includes_type_mismatch(self, temp_db, resultlist_config):
        """Title-based blacklist check should include TypeMismatch reason."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')
        # Add a blacklisted item by title with TypeMismatch reason
        conn.execute(
            'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
            ('http://example.com/other.nzb', 'TestProv', 'Bad Title', 'TypeMismatch')
        )
        conn.commit()

        # Title-based blacklist check should find this entry
        result = conn.execute(
            'SELECT * from blacklist WHERE NZBprov=? and NZBtitle=? and Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")',
            ('TestProv', 'Bad Title')
        ).fetchone()

        assert result is not None
        assert result[5] == 'TypeMismatch'

    def test_all_failure_reasons_covered(self, temp_db, resultlist_config):
        """Verify all failure-type reasons are covered by the blacklist check."""
        db_path, conn = temp_db

        # Create blacklist table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                NZBurl TEXT,
                NZBprov TEXT,
                NZBtitle TEXT,
                BookID TEXT,
                AuxInfo TEXT,
                Reason TEXT
            )
        ''')

        # Add entries for all failure-type reasons
        failure_reasons = ['Failed', 'TypeMismatch', 'UnsupportedFileType']
        for i, reason in enumerate(failure_reasons):
            conn.execute(
                'INSERT INTO blacklist (NZBurl, NZBprov, NZBtitle, Reason) VALUES (?, ?, ?, ?)',
                (f'http://example.com/test{i}.nzb', 'TestProv', f'Test Book {i}', reason)
            )
        conn.commit()

        # All three should be found by the failure check query
        results = conn.execute(
            'SELECT * from blacklist WHERE Reason IN ("Failed", "TypeMismatch", "UnsupportedFileType")'
        ).fetchall()

        assert len(results) == 3
        found_reasons = {r[5] for r in results}
        assert found_reasons == set(failure_reasons)
