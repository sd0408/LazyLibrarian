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
Unit tests for bookbagofholding.web.handlers module.

Tests cover:
- AuthorHandler class for author operations
- BookHandler class for book operations
- Helper functions for validation and processing
"""

import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch

# Import cherrypy normally - it should be available from the environment
import cherrypy


# ============================================================================
# Handler Module Import Tests
# ============================================================================

class TestHandlerModuleImports:
    """Tests for handler module imports."""

    def test_author_handler_imports(self):
        """AuthorHandler should be importable."""
        from bookbagofholding.web.handlers.author_handler import AuthorHandler
        assert AuthorHandler is not None

    def test_book_handler_imports(self):
        """BookHandler should be importable."""
        from bookbagofholding.web.handlers.book_handler import BookHandler
        assert BookHandler is not None

    def test_handlers_init_imports(self):
        """Handlers __init__ module should be importable."""
        from bookbagofholding.web import handlers
        assert handlers is not None
        assert hasattr(handlers, 'AuthorHandler')
        assert hasattr(handlers, 'BookHandler')


# ============================================================================
# AuthorHandler Helper Functions Tests
# ============================================================================

class TestValidateDate:
    """Tests for _validate_date helper function."""

    def test_validate_date_accepts_valid_date(self):
        """_validate_date should accept valid YYYY/MM/DD format."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('2020/01/15', None, 'Born')
        assert result == '2020/01/15'

    def test_validate_date_rejects_invalid_format(self):
        """_validate_date should reject invalid date format."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('invalid', 'current', 'Born')
        assert result == 'current'

    def test_validate_date_rejects_wrong_length(self):
        """_validate_date should reject dates with wrong length."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('2020', 'current', 'Born')
        assert result == 'current'

    def test_validate_date_handles_none(self):
        """_validate_date should handle None values."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date(None, 'current', 'Born')
        assert result == 'current'

    def test_validate_date_handles_empty_string(self):
        """_validate_date should handle empty string."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('', 'current', 'Born')
        assert result == 'current'

    def test_validate_date_rejects_invalid_month(self):
        """_validate_date should reject invalid month values."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('2020/13/01', 'current', 'Born')
        assert result == 'current'

    def test_validate_date_rejects_invalid_day(self):
        """_validate_date should reject invalid day values."""
        from bookbagofholding.web.handlers.author_handler import _validate_date

        result = _validate_date('2020/02/31', 'current', 'Born')
        assert result == 'current'


class TestCacheAuthorImage:
    """Tests for _cache_author_image helper function."""

    def test_cache_author_image_handles_none_path(self):
        """_cache_author_image should handle 'none' path."""
        from bookbagofholding.web.handlers.author_handler import _cache_author_image

        with patch('bookbagofholding.web.handlers.author_handler.bookbagofholding') as mock_bb:
            mock_bb.PROG_DIR = '/app'

            result, success = _cache_author_image('1', 'none')

            assert success is True
            assert 'nophoto.png' in result

    def test_cache_author_image_rejects_invalid_path(self):
        """_cache_author_image should reject paths that don't exist."""
        from bookbagofholding.web.handlers.author_handler import _cache_author_image

        result, success = _cache_author_image('1', '/nonexistent/path.jpg')

        assert success is False

    def test_cache_author_image_rejects_non_image_url(self):
        """_cache_author_image should reject non-image URLs."""
        from bookbagofholding.web.handlers.author_handler import _cache_author_image

        result, success = _cache_author_image('1', 'http://example.com/file.txt')

        assert success is False


# ============================================================================
# BookHandler Helper Functions Tests
# ============================================================================

class TestValidateBookDate:
    """Tests for _validate_book_date helper function."""

    def test_validate_book_date_accepts_year(self):
        """_validate_book_date should accept 4-digit year."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('2020') is True

    def test_validate_book_date_accepts_year_month(self):
        """_validate_book_date should accept YYYY-MM format."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('2020-01') is True

    def test_validate_book_date_accepts_full_date(self):
        """_validate_book_date should accept YYYY-MM-DD format."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('2020-01-15') is True

    def test_validate_book_date_rejects_invalid(self):
        """_validate_book_date should reject invalid dates."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('invalid') is False
        assert _validate_book_date('20') is False

    def test_validate_book_date_rejects_invalid_month(self):
        """_validate_book_date should reject invalid month."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('2020-13-01') is False

    def test_validate_book_date_rejects_invalid_day(self):
        """_validate_book_date should reject invalid day."""
        from bookbagofholding.web.handlers.book_handler import _validate_book_date

        assert _validate_book_date('2020-02-31') is False


class TestProcessCoverChange:
    """Tests for _process_cover_change helper function."""

    def test_process_cover_change_returns_current_for_unknown(self):
        """_process_cover_change should return current for unknown source."""
        from bookbagofholding.web.handlers.book_handler import _process_cover_change

        result = _process_cover_change('1', 'unknown_source', 'current.jpg')
        assert result == 'current.jpg'

    def test_process_cover_change_returns_current_for_empty(self):
        """_process_cover_change should return current for empty source."""
        from bookbagofholding.web.handlers.book_handler import _process_cover_change

        result = _process_cover_change('1', '', 'current.jpg')
        assert result == 'current.jpg'

    def test_process_cover_change_handles_librarything(self):
        """_process_cover_change should handle librarything source."""
        from bookbagofholding.web.handlers.book_handler import _process_cover_change

        with patch('bookbagofholding.web.handlers.book_handler.bookbagofholding') as mock_bb:
            mock_bb.CACHEDIR = '/cache'

            result = _process_cover_change('book1', 'librarything', 'current.jpg')
            # Without the actual file, should return current
            assert result == 'current.jpg'


class TestProcessSeriesChanges:
    """Tests for _process_series_changes helper function."""

    def test_process_series_changes_returns_false_for_no_changes(self):
        """_process_series_changes should return False when no changes."""
        from bookbagofholding.web.handlers.book_handler import _process_series_changes

        myDB = MagicMock()
        myDB.select.return_value = []

        result = _process_series_changes(myDB, 'book1', {})
        assert result is False

    def test_process_series_changes_handles_new_series(self):
        """_process_series_changes should handle new series."""
        from bookbagofholding.web.handlers.book_handler import _process_series_changes

        myDB = MagicMock()
        myDB.select.return_value = []
        myDB.match.return_value = None

        kwargs = {
            'series[new][name]': 'New Series',
            'series[new][number]': '1'
        }

        result = _process_series_changes(myDB, 'book1', kwargs)
        assert result is True


class TestProcessReadStatus:
    """Tests for _process_read_status helper function."""

    def test_process_read_status_handles_no_cookie(self):
        """_process_read_status should handle missing cookie."""
        from bookbagofholding.web.handlers.book_handler import _process_read_status

        with patch('bookbagofholding.web.handlers.book_handler.cherrypy') as mock_cp:
            mock_cp.request.cookie = {}
            myDB = MagicMock()

            # Should not raise
            _process_read_status(myDB, 'book1', 'Read')
            # DB should not be called when no cookie
            assert not myDB.match.called

    def test_process_read_status_handles_no_user(self):
        """_process_read_status should handle no user in DB."""
        from bookbagofholding.web.handlers.book_handler import _process_read_status

        with patch('bookbagofholding.web.handlers.book_handler.cherrypy') as mock_cp:
            mock_cp.request.cookie = {'ll_uid': MagicMock(value='user1')}
            myDB = MagicMock()
            myDB.match.return_value = None

            _process_read_status(myDB, 'book1', 'Read')
            # Should have tried to find user
            myDB.match.assert_called()


class TestProcessStatusChange:
    """Tests for _process_status_change helper function."""

    def test_process_status_change_handles_missing_book(self):
        """_process_status_change should handle missing book."""
        from bookbagofholding.web.handlers.book_handler import _process_status_change

        myDB = MagicMock()
        myDB.match.return_value = None
        check_totals = []

        _process_status_change(myDB, 'book1', 'Wanted', 'eBook', check_totals)

        # Should not update anything
        assert not myDB.upsert.called
        assert len(check_totals) == 0

    def test_process_status_change_updates_ebook_status(self):
        """_process_status_change should update eBook status."""
        from bookbagofholding.web.handlers.book_handler import _process_status_change

        myDB = MagicMock()
        myDB.match.return_value = {'AuthorID': 'auth1', 'BookName': 'Test Book'}
        check_totals = []

        _process_status_change(myDB, 'book1', 'Wanted', 'eBook', check_totals)

        myDB.upsert.assert_called()
        assert 'auth1' in check_totals

    def test_process_status_change_updates_audio_status(self):
        """_process_status_change should update AudioBook status."""
        from bookbagofholding.web.handlers.book_handler import _process_status_change

        myDB = MagicMock()
        myDB.match.return_value = {'AuthorID': 'auth1', 'BookName': 'Test Book'}
        check_totals = []

        _process_status_change(myDB, 'book1', 'Wanted', 'AudioBook', check_totals)

        myDB.upsert.assert_called()


class TestProcessBookRemoval:
    """Tests for _process_book_removal helper function."""

    def test_process_book_removal_handles_missing_book(self):
        """_process_book_removal should handle missing book."""
        from bookbagofholding.web.handlers.book_handler import _process_book_removal

        myDB = MagicMock()
        myDB.match.return_value = None
        check_totals = []

        _process_book_removal(myDB, 'book1', 'Remove', 'eBook', check_totals)

        assert len(check_totals) == 0

    def test_process_book_removal_sets_ignored_for_active_author(self):
        """_process_book_removal should set Ignored for active author."""
        from bookbagofholding.web.handlers.book_handler import _process_book_removal

        myDB = MagicMock()
        myDB.match.side_effect = [
            {'AuthorID': 'auth1', 'BookName': 'Test', 'BookFile': None, 'AudioFile': None},
            {'Status': 'Active'}  # Author is Active
        ]
        check_totals = []

        _process_book_removal(myDB, 'book1', 'Remove', 'eBook', check_totals)

        # Should set status to Ignored instead of deleting
        upsert_calls = [call for call in myDB.upsert.call_args_list]
        assert any('Ignored' in str(call) for call in upsert_calls)


class TestStartWantedSearch:
    """Tests for _start_wanted_search helper function."""

    def test_start_wanted_search_does_nothing_when_autosearch_disabled(self):
        """_start_wanted_search should do nothing when IMP_AUTOSEARCH is False."""
        from bookbagofholding.web.handlers.book_handler import _start_wanted_search

        with patch('bookbagofholding.web.handlers.book_handler.bookbagofholding') as mock_bb, \
             patch('bookbagofholding.web.handlers.book_handler.threading') as mock_thread:
            mock_bb.CONFIG = {'IMP_AUTOSEARCH': False}

            _start_wanted_search({'book1': True}, 'eBook')

            assert not mock_thread.Thread.called


class TestHandleBookRedirect:
    """Tests for _handle_book_redirect helper function."""

    def test_handle_book_redirect_to_author(self):
        """_handle_book_redirect should redirect to author page."""
        from bookbagofholding.web.handlers.book_handler import _handle_book_redirect
        import bookbagofholding.web.handlers.book_handler as bh

        # Get the actual HTTPRedirect class used by the module
        HTTPRedirect = bh.cherrypy.HTTPRedirect

        with pytest.raises(HTTPRedirect):
            _handle_book_redirect('author', 'author1', None, 'eBook')

    def test_handle_book_redirect_to_books(self):
        """_handle_book_redirect should redirect to books page."""
        from bookbagofholding.web.handlers.book_handler import _handle_book_redirect
        import bookbagofholding.web.handlers.book_handler as bh

        HTTPRedirect = bh.cherrypy.HTTPRedirect

        with pytest.raises(HTTPRedirect):
            _handle_book_redirect('books', None, None, 'eBook')

    def test_handle_book_redirect_to_audio(self):
        """_handle_book_redirect should redirect to audio page."""
        from bookbagofholding.web.handlers.book_handler import _handle_book_redirect
        import bookbagofholding.web.handlers.book_handler as bh

        HTTPRedirect = bh.cherrypy.HTTPRedirect

        with pytest.raises(HTTPRedirect):
            _handle_book_redirect('audio', None, None, 'AudioBook')

    def test_handle_book_redirect_to_members(self):
        """_handle_book_redirect should redirect to members page."""
        from bookbagofholding.web.handlers.book_handler import _handle_book_redirect
        import bookbagofholding.web.handlers.book_handler as bh

        HTTPRedirect = bh.cherrypy.HTTPRedirect

        with pytest.raises(HTTPRedirect):
            _handle_book_redirect('members', None, 'series1', 'eBook')


# ============================================================================
# AuthorHandler Static Method Tests
# ============================================================================

class TestAuthorHandlerStaticMethods:
    """Tests for AuthorHandler static methods that don't require full setup."""

    def test_get_author_page_redirects_when_author_none(self):
        """get_author_page should redirect when author is None."""
        from bookbagofholding.web.handlers.author_handler import AuthorHandler
        import bookbagofholding.web.handlers.author_handler as ah

        HTTPRedirect = ah.cherrypy.HTTPRedirect

        with patch.object(ah, 'database') as mock_db, \
             patch.object(ah, 'bookbagofholding') as mock_bb:
            mock_conn = MagicMock()
            mock_db.DBConnection.return_value = mock_conn
            mock_conn.select.return_value = []
            mock_conn.match.return_value = None  # Author not found

            with pytest.raises(HTTPRedirect):
                AuthorHandler.get_author_page('nonexistent')

    def test_remove_author_redirects_to_home(self):
        """remove_author should always redirect to home."""
        from bookbagofholding.web.handlers.author_handler import AuthorHandler
        import bookbagofholding.web.handlers.author_handler as ah

        HTTPRedirect = ah.cherrypy.HTTPRedirect

        with patch.object(ah, 'database') as mock_db:
            mock_conn = MagicMock()
            mock_db.DBConnection.return_value = mock_conn
            mock_conn.match.return_value = {'AuthorName': 'Test'}

            with pytest.raises(HTTPRedirect):
                AuthorHandler.remove_author('1')

    def test_toggle_ignored_authors_toggles_flag(self):
        """toggle_ignored_authors should toggle the IGNORED_AUTHORS flag."""
        from bookbagofholding.web.handlers.author_handler import AuthorHandler
        import bookbagofholding.web.handlers.author_handler as ah

        HTTPRedirect = ah.cherrypy.HTTPRedirect

        with patch.object(ah, 'bookbagofholding') as mock_bb:
            mock_bb.IGNORED_AUTHORS = False

            with pytest.raises(HTTPRedirect):
                AuthorHandler.toggle_ignored_authors()

            assert mock_bb.IGNORED_AUTHORS is True

    def test_get_edit_author_page_returns_empty_when_not_found(self):
        """get_edit_author_page should return empty string when author not found."""
        from bookbagofholding.web.handlers.author_handler import AuthorHandler
        import bookbagofholding.web.handlers.author_handler as ah

        with patch.object(ah, 'database') as mock_db:
            mock_conn = MagicMock()
            mock_db.DBConnection.return_value = mock_conn
            mock_conn.match.return_value = None

            result = AuthorHandler.get_edit_author_page('nonexistent')
            assert result == ''


# ============================================================================
# BookHandler Static Method Tests
# ============================================================================

class TestBookHandlerStaticMethods:
    """Tests for BookHandler static methods that don't require full setup."""

    def test_start_book_search_handles_empty_books(self):
        """start_book_search should handle empty book list."""
        from bookbagofholding.web.handlers.book_handler import BookHandler
        import bookbagofholding.web.handlers.book_handler as bh

        with patch.object(bh, 'threading') as mock_thread:
            BookHandler.start_book_search([])

            # Thread should not be started for empty list
            assert not mock_thread.Thread.called

    def test_start_book_search_warns_when_no_methods(self):
        """start_book_search should warn when no search methods configured."""
        from bookbagofholding.web.handlers.book_handler import BookHandler
        import bookbagofholding.web.handlers.book_handler as bh

        with patch.object(bh, 'bookbagofholding') as mock_bb, \
             patch.object(bh, 'threading') as mock_thread, \
             patch.object(bh, 'logger') as mock_logger:
            mock_bb.USE_NZB.return_value = False
            mock_bb.USE_TOR.return_value = False
            mock_bb.USE_RSS.return_value = False
            mock_bb.USE_DIRECT.return_value = False

            BookHandler.start_book_search([{'bookid': 'book1'}])

            mock_logger.warn.assert_called()

    def test_get_edit_book_page_returns_empty_when_not_found(self):
        """get_edit_book_page should return empty string when book not found."""
        from bookbagofholding.web.handlers.book_handler import BookHandler
        import bookbagofholding.web.handlers.book_handler as bh

        with patch.object(bh, 'database') as mock_db, \
             patch.object(bh, 'cherrypy') as mock_cp:
            mock_cp.response.headers = {}
            mock_conn = MagicMock()
            mock_db.DBConnection.return_value = mock_conn
            mock_conn.select.return_value = []
            mock_conn.match.return_value = None

            result = BookHandler.get_edit_book_page('nonexistent')
            assert result == ''
