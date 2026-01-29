#  This file is part of Lazylibrarian.
#
#  Lazylibrarian is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

"""
Unit tests for lazylibrarian.webServe module.

Tests cover:
- WebInterface class handlers
- serve_template function
- Permission checking
- User authentication flows
- DataTable JSON endpoints
"""

import hashlib
import pytest
from unittest.mock import Mock, patch, MagicMock

import cherrypy
import lazylibrarian
from lazylibrarian.database import DBConnection


# ============================================================================
# Test WebInterface Index/Home Handlers
# ============================================================================

@pytest.mark.web
class TestWebInterfaceIndex:
    """Tests for WebInterface index and home handlers."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_index_redirects_to_home(self, mock_response, mock_request, api_config, temp_db):
        """index() should redirect to home."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        wi = WebInterface()

        with pytest.raises(cherrypy.HTTPRedirect) as excinfo:
            wi.index()

        # HTTPRedirect stores the URLs in the exception
        assert 'home' in str(excinfo.value.urls)

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    @patch('lazylibrarian.webServe.serve_template')
    def test_home_serves_index_template(self, mock_serve, mock_response, mock_request, api_config, temp_db):
        """home() should serve index.html template with Dashboard title."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_serve.return_value = '<html>test</html>'
        lazylibrarian.IGNORED_AUTHORS = 0

        wi = WebInterface()
        result = wi.home()

        mock_serve.assert_called_once()
        call_kwargs = mock_serve.call_args[1]
        assert call_kwargs['templatename'] == 'index.html'
        assert call_kwargs['title'] == 'Dashboard'

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    @patch('lazylibrarian.webServe.serve_template')
    def test_home_shows_ignored_title_when_flag_set(self, mock_serve, mock_response, mock_request, api_config, temp_db):
        """home() should always show Dashboard regardless of IGNORED_AUTHORS flag."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_serve.return_value = '<html>test</html>'
        lazylibrarian.IGNORED_AUTHORS = 1

        wi = WebInterface()
        wi.home()

        call_kwargs = mock_serve.call_args[1]
        # Now always shows Dashboard
        assert call_kwargs['title'] == 'Dashboard'

        lazylibrarian.IGNORED_AUTHORS = 0


# ============================================================================
# Test User Authentication Handlers
# ============================================================================

@pytest.mark.web
class TestWebInterfaceLogout:
    """Tests for logout handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_logout_clears_cookie(self, mock_response, mock_request, api_config, temp_db):
        """logout() should clear the ll_uid cookie and redirect."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {'ll_uid': Mock(value='test-user')}
        # Use MagicMock to allow item assignment
        mock_response.cookie = MagicMock()

        wi = WebInterface()

        with pytest.raises(cherrypy.HTTPRedirect) as excinfo:
            wi.logout()

        # Verify redirect to home
        assert 'home' in str(excinfo.value.urls)
        # Verify cookie was set (even if to empty)
        assert mock_response.cookie.__setitem__.called or mock_response.cookie.__getitem__.called


@pytest.mark.web
class TestWebInterfaceLogin:
    """Tests for user login handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_login_blocks_after_failed_attempts(self, mock_response, mock_request, api_config, temp_db):
        """user_login() should block IP after multiple failed attempts."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_request.remote = Mock(ip='192.168.1.100')
        mock_response.cookie = {}

        lazylibrarian.USER_BLOCKLIST = []

        # Add 5 failed attempts for this IP
        import time
        for i in range(5):
            lazylibrarian.USER_BLOCKLIST.append(('192.168.1.100', int(time.time())))

        wi = WebInterface()
        result = wi.user_login(username='test', password='wrong')

        assert 'blocked' in result.lower()

        lazylibrarian.USER_BLOCKLIST = []

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_login_accepts_valid_credentials(self, mock_response, mock_request, api_config, temp_db):
        """user_login() should accept valid username/password."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_request.remote = Mock(ip='127.0.0.1')
        mock_response.cookie = {}

        lazylibrarian.USER_BLOCKLIST = []
        lazylibrarian.SHOWLOGOUT = 0

        # Create test user
        db = DBConnection()
        pwd_hash = hashlib.md5('testpass'.encode()).hexdigest()
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['test-user-001', 'testuser', pwd_hash, 65535])

        wi = WebInterface()
        result = wi.user_login(username='testuser', password='testpass')

        # Empty string means success
        assert result == ''
        assert lazylibrarian.SHOWLOGOUT == 1

        lazylibrarian.USER_BLOCKLIST = []
        lazylibrarian.SHOWLOGOUT = 0

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_login_rejects_wrong_password(self, mock_response, mock_request, api_config, temp_db):
        """user_login() should reject wrong password."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_request.remote = Mock(ip='127.0.0.1')
        mock_response.cookie = {}

        lazylibrarian.USER_BLOCKLIST = []
        lazylibrarian.LOGIN_MSG = ''

        # Create test user
        db = DBConnection()
        pwd_hash = hashlib.md5('testpass'.encode()).hexdigest()
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['test-user-002', 'wrongpassuser', pwd_hash, 65535])

        wi = WebInterface()
        result = wi.user_login(username='wrongpassuser', password='wrongpassword')

        assert 'wrong password' in result.lower() or 'attempt' in result.lower()

        lazylibrarian.USER_BLOCKLIST = []

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_login_rejects_invalid_user(self, mock_response, mock_request, api_config, temp_db):
        """user_login() should reject invalid username."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_request.remote = Mock(ip='127.0.0.1')
        mock_response.cookie = {}

        lazylibrarian.USER_BLOCKLIST = []

        wi = WebInterface()
        result = wi.user_login(username='nonexistent', password='anypass')

        assert 'invalid' in result.lower()

        lazylibrarian.USER_BLOCKLIST = []


# ============================================================================
# Test getIndex DataTable Handler
# ============================================================================

@pytest.mark.web
class TestWebInterfaceGetIndex:
    """Tests for getIndex DataTable JSON handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_getIndex_returns_json_structure(self, mock_response, mock_request, api_config, temp_db):
        """getIndex() should return proper DataTable JSON structure."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        lazylibrarian.IGNORED_AUTHORS = 0

        wi = WebInterface()
        result = wi.getIndex(iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0='asc', sSearch='')

        assert 'iTotalRecords' in result
        assert 'iTotalDisplayRecords' in result
        assert 'aaData' in result

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_getIndex_returns_authors(self, mock_response, mock_request, api_config, temp_db, sample_author_data):
        """getIndex() should return authors from database."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        lazylibrarian.IGNORED_AUTHORS = 0

        # Insert test author with required columns
        db = DBConnection()
        db.action(
            """INSERT INTO authors (AuthorID, AuthorName, AuthorImg, Status, HaveBooks, UnignoredBooks,
               LastBook, LastDate, LastBookID, AuthorLink, LastLink)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [sample_author_data['AuthorID'], sample_author_data['AuthorName'],
             sample_author_data['AuthorImg'], 'Active', 5, 10, 'Last Book', '2023-01-01',
             'last-book-id', 'http://example.com', 'http://example.com/last']
        )

        wi = WebInterface()
        result = wi.getIndex(iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0='asc', sSearch='')

        assert result['iTotalRecords'] >= 1
        assert len(result['aaData']) >= 1

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_getIndex_handles_empty_database(self, mock_response, mock_request, api_config, temp_db):
        """getIndex() should handle empty database gracefully."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        lazylibrarian.IGNORED_AUTHORS = 0

        wi = WebInterface()
        result = wi.getIndex(iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0='asc', sSearch='')

        assert result['iTotalRecords'] == 0
        assert result['aaData'] == []

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_getIndex_filters_by_search_term(self, mock_response, mock_request, api_config, temp_db, sample_author_data):
        """getIndex() should filter results by search term."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        lazylibrarian.IGNORED_AUTHORS = 0

        # Insert two authors
        db = DBConnection()
        db.action(
            """INSERT INTO authors (AuthorID, AuthorName, AuthorImg, Status, HaveBooks, UnignoredBooks,
               LastBook, LastDate, LastBookID, AuthorLink, LastLink)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [sample_author_data['AuthorID'], 'John Smith', '', 'Active', 5, 10, '', '', '', '', '']
        )
        db.action(
            """INSERT INTO authors (AuthorID, AuthorName, AuthorImg, Status, HaveBooks, UnignoredBooks,
               LastBook, LastDate, LastBookID, AuthorLink, LastLink)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ['other-author', 'Jane Doe', '', 'Active', 3, 8, '', '', '', '', '']
        )

        wi = WebInterface()
        result = wi.getIndex(iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0='asc', sSearch='John')

        assert result['iTotalDisplayRecords'] == 1

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_getIndex_excludes_ignored_authors_by_default(self, mock_response, mock_request, api_config, temp_db):
        """getIndex() should exclude ignored authors when IGNORED_AUTHORS is 0."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        lazylibrarian.IGNORED_AUTHORS = 0

        db = DBConnection()
        db.action(
            """INSERT INTO authors (AuthorID, AuthorName, AuthorImg, Status, HaveBooks, UnignoredBooks,
               LastBook, LastDate, LastBookID, AuthorLink, LastLink)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ['ignored-author', 'Ignored Person', '', 'Ignored', 0, 0, '', '', '', '', '']
        )

        wi = WebInterface()
        result = wi.getIndex(iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0='asc', sSearch='')

        assert result['iTotalRecords'] == 0


# ============================================================================
# Test User Admin Handlers
# ============================================================================

@pytest.mark.web
class TestWebInterfaceAdminDelete:
    """Tests for admin user deletion handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_admin_delete_prevents_last_admin_deletion(self, mock_response, mock_request, api_config, temp_db):
        """admin_delete() should prevent deleting the last administrator."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}

        # Create only one admin user (perms & 1 = config permission = admin indicator)
        db = DBConnection()
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['admin-001', 'lastadmin', 'hash', 65535])

        wi = WebInterface()
        result = wi.admin_delete(user='lastadmin')

        assert 'unable to delete last administrator' in result.lower()

        # Verify user still exists
        user = db.match("SELECT * FROM users WHERE UserName=?", ('lastadmin',))
        assert user is not None

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_admin_delete_allows_deletion_when_multiple_admins(self, mock_response, mock_request, api_config, temp_db):
        """admin_delete() should allow deletion when multiple admins exist."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}

        # Create two admin users
        db = DBConnection()
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['admin-001', 'admin1', 'hash', 65535])
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['admin-002', 'admin2', 'hash', 65535])

        wi = WebInterface()
        result = wi.admin_delete(user='admin1')

        assert 'deleted' in result.lower()

        # Verify user was deleted
        user = db.match("SELECT * FROM users WHERE UserName=?", ('admin1',))
        assert user is None or user == []

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_admin_delete_returns_error_for_nonexistent_user(self, mock_response, mock_request, api_config, temp_db):
        """admin_delete() should return error for nonexistent user."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}

        wi = WebInterface()
        result = wi.admin_delete(user='nonexistent')

        assert 'not found' in result.lower()


# ============================================================================
# Test User Registration Handler
# ============================================================================

@pytest.mark.web
class TestWebInterfaceUserRegister:
    """Tests for user registration handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    @patch('lazylibrarian.webServe.serve_template')
    def test_user_register_serves_register_template(self, mock_serve, mock_response, mock_request, api_config, temp_db):
        """user_register() should serve register.html template."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_serve.return_value = '<html>register</html>'

        wi = WebInterface()
        wi.user_register()

        mock_serve.assert_called_once()
        call_kwargs = mock_serve.call_args[1]
        assert 'register' in call_kwargs['templatename']


# ============================================================================
# Test User Update Handler
# ============================================================================

@pytest.mark.web
class TestWebInterfaceUserUpdate:
    """Tests for user update handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_update_rejects_mismatched_passwords(self, mock_response, mock_request, api_config, temp_db):
        """user_update() should reject mismatched passwords."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {'ll_uid': Mock(value='test-user')}

        wi = WebInterface()
        result = wi.user_update(password='pass1', password2='pass2', username='', fullname='', email='', sendto='', booktype='')

        assert 'passwords do not match' in result.lower()

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_update_rejects_short_password(self, mock_response, mock_request, api_config, temp_db):
        """user_update() should reject passwords shorter than 8 characters."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {'ll_uid': Mock(value='test-user')}

        wi = WebInterface()
        result = wi.user_update(password='short', password2='short', username='', fullname='', email='', sendto='', booktype='')

        assert 'at least 8' in result.lower()

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_user_update_returns_no_changes_without_cookie(self, mock_response, mock_request, api_config, temp_db):
        """user_update() should return 'No changes made' when no cookie is present."""
        from lazylibrarian.webServe import WebInterface

        # No cookie means no user to update
        mock_request.cookie = {}

        wi = WebInterface()
        result = wi.user_update(
            password='', password2='',
            username='testuser',
            fullname='Test Name',
            email='test@test.com',
            sendto='',
            booktype=''
        )

        assert 'no changes' in result.lower()


# ============================================================================
# Test Admin User Data Handler
# ============================================================================

@pytest.mark.web
class TestWebInterfaceAdminUserData:
    """Tests for admin user data retrieval handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_admin_userdata_returns_user_details(self, mock_response, mock_request, api_config, temp_db):
        """admin_userdata() should return user details as JSON."""
        import json
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}

        # Create test user with all fields
        db = DBConnection()
        db.action(
            """INSERT INTO users (UserID, UserName, Password, Name, Email, Perms,
               CalibreRead, CalibreToRead, SendTo, BookType)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ['user-data-test', 'datauser', 'hash', 'Test Name', 'test@email.com',
             65535, 'read_col', 'toread_col', 'sendto@email.com', 'epub']
        )

        wi = WebInterface()
        result = wi.admin_userdata(user='datauser')

        parsed = json.loads(result)
        assert parsed['email'] == 'test@email.com'
        assert parsed['name'] == 'Test Name'
        assert parsed['userid'] == 'user-data-test'

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_admin_userdata_returns_empty_for_missing_user(self, mock_response, mock_request, api_config, temp_db):
        """admin_userdata() should return empty data for nonexistent user."""
        import json
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}

        wi = WebInterface()
        result = wi.admin_userdata(user='nonexistent')

        parsed = json.loads(result)
        assert parsed['email'] == ''
        assert parsed['userid'] == ''


# ============================================================================
# Test Label Thread Helper
# ============================================================================

@pytest.mark.web
class TestWebInterfaceLabelThread:
    """Tests for label_thread helper method."""

    def test_label_thread_sets_name(self, api_config):
        """label_thread() should set the thread name."""
        import threading
        from lazylibrarian.webServe import WebInterface

        wi = WebInterface()
        wi.label_thread("TEST-THREAD")

        assert threading.currentThread().name == "TEST-THREAD"

    def test_label_thread_sets_webserver_for_generic_threads(self, api_config):
        """label_thread() without name should set WEBSERVER for Thread-* names."""
        import threading
        from lazylibrarian.webServe import WebInterface

        # Save original name
        original_name = threading.currentThread().name

        # Set a Thread- style name
        threading.currentThread().name = "Thread-123"

        wi = WebInterface()
        wi.label_thread()

        assert threading.currentThread().name == "WEBSERVER"

        # Restore original name
        threading.currentThread().name = original_name


# ============================================================================
# Test Profile Handler
# ============================================================================

@pytest.mark.web
class TestWebInterfaceProfile:
    """Tests for user profile handler."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    @patch('lazylibrarian.webServe.serve_template')
    def test_profile_serves_profile_template_for_logged_in_user(self, mock_serve, mock_response, mock_request, api_config, temp_db):
        """profile() should serve profile.html for logged in user."""
        from lazylibrarian.webServe import WebInterface

        # Create test user
        db = DBConnection()
        db.action(
            "INSERT INTO users (UserID, UserName, Password, Name, Email, SendTo, Perms) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ['profile-test-user', 'profileuser', 'hash', 'Test Name', 'test@email.com', '', 65535]
        )

        mock_request.cookie = {'ll_uid': Mock(value='profile-test-user')}
        mock_serve.return_value = '<html>profile</html>'

        wi = WebInterface()
        wi.profile()

        mock_serve.assert_called()
        call_kwargs = mock_serve.call_args[1]
        assert call_kwargs['templatename'] == 'profile.html'

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    @patch('lazylibrarian.webServe.serve_template')
    def test_profile_redirects_to_index_without_cookie(self, mock_serve, mock_response, mock_request, api_config, temp_db):
        """profile() should redirect to index.html without logged in user."""
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_serve.return_value = '<html>index</html>'

        wi = WebInterface()
        wi.profile()

        mock_serve.assert_called()
        call_kwargs = mock_serve.call_args[1]
        assert call_kwargs['templatename'] == 'index.html'
