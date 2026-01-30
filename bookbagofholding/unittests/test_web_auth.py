"""
Tests for simplified authentication module (Radarr-style).

The auth module has been simplified to support:
- None: No authentication
- Forms: Login page with username/password from config
- Basic: HTTP Basic Auth
- External: Trust reverse proxy headers
"""

import hashlib
import pytest
from unittest.mock import MagicMock, Mock, patch

# Import the auth module so we can patch objects on it
from bookbagofholding.web import auth as auth_module


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_tuple(self):
        """hash_password should return (hash, algorithm) tuple with bcrypt by default."""
        from bookbagofholding.web.auth import hash_password

        password = "testpassword"
        result_hash, result_algo = hash_password(password)

        # bcrypt is the default algorithm
        assert result_algo == 'bcrypt'
        assert len(result_hash) == 60  # bcrypt hash is 60 chars
        assert result_hash.startswith('$2b$')  # bcrypt prefix

    def test_hash_password_md5_legacy_function(self):
        """hash_password_md5 should return just the hash string."""
        from bookbagofholding.web.auth import hash_password_md5

        password = "testpassword"
        expected = hashlib.md5(password.encode('utf-8')).hexdigest()

        result = hash_password_md5(password)
        assert result == expected
        assert len(result) == 32

    def test_hash_password_different_for_different_passwords(self):
        """hash_password should return different hashes for different passwords."""
        from bookbagofholding.web.auth import hash_password

        hash1, _ = hash_password("password1")
        hash2, _ = hash_password("password2")
        assert hash1 != hash2

    def test_hash_password_handles_unicode(self):
        """hash_password should handle unicode passwords."""
        from bookbagofholding.web.auth import hash_password

        password = "pässwörd123"
        result_hash, result_algo = hash_password(password)
        assert result_algo == 'bcrypt'
        assert len(result_hash) == 60  # bcrypt hash is 60 chars

    def test_hash_password_handles_empty_string(self):
        """hash_password should handle empty password."""
        from bookbagofholding.web.auth import hash_password

        result_hash, result_algo = hash_password("")
        assert result_algo == 'bcrypt'
        assert len(result_hash) == 60  # bcrypt hash is 60 chars
        assert result_hash.startswith('$2b$')  # bcrypt prefix


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_returns_true_for_match(self):
        """verify_password should return True for correct password."""
        from bookbagofholding.web.auth import hash_password, verify_password

        password = "testpassword"
        hashed, algo = hash_password(password)

        assert verify_password(password, hashed, algo) is True

    def test_verify_password_returns_false_for_mismatch(self):
        """verify_password should return False for incorrect password."""
        from bookbagofholding.web.auth import hash_password, verify_password

        hashed, algo = hash_password("correct_password")

        assert verify_password("wrong_password", hashed, algo) is False

    def test_verify_password_case_sensitive(self):
        """verify_password should be case sensitive."""
        from bookbagofholding.web.auth import hash_password, verify_password

        hashed, algo = hash_password("Password")

        assert verify_password("password", hashed, algo) is False
        assert verify_password("PASSWORD", hashed, algo) is False
        assert verify_password("Password", hashed, algo) is True


class TestCheckPermission:
    """Tests for check_permission function."""

    def test_check_permission_returns_true_when_granted(self):
        """check_permission should return True when user has permission."""
        from bookbagofholding.web.auth import check_permission, Permission

        user_perm = Permission.CONFIG | Permission.LOGS
        assert check_permission(Permission.CONFIG, user_perm) is True

    def test_check_permission_returns_false_when_not_granted(self):
        """check_permission should return False when user lacks permission."""
        from bookbagofholding.web.auth import check_permission, Permission

        user_perm = Permission.LOGS
        assert check_permission(Permission.CONFIG, user_perm) is False

    def test_check_permission_admin_has_all(self):
        """Admin (65535) should have all permissions."""
        from bookbagofholding.web.auth import check_permission, Permission, PERM_ADMIN

        assert check_permission(Permission.CONFIG, PERM_ADMIN) is True
        assert check_permission(Permission.DOWNLOAD, PERM_ADMIN) is True
        assert check_permission(Permission.EDIT, PERM_ADMIN) is True


class TestRoleFunctions:
    """Tests for role-related functions."""

    def test_get_role_from_permissions_admin(self):
        """get_role_from_permissions should return 'admin' for admin perms."""
        from bookbagofholding.web.auth import get_role_from_permissions, PERM_ADMIN

        assert get_role_from_permissions(PERM_ADMIN) == 'admin'
        assert get_role_from_permissions(65535) == 'admin'

    def test_get_role_from_permissions_manager(self):
        """get_role_from_permissions should return 'manager' for manager perms."""
        from bookbagofholding.web.auth import get_role_from_permissions, PERM_MANAGER

        assert get_role_from_permissions(PERM_MANAGER) == 'manager'

    def test_get_role_from_permissions_friend(self):
        """get_role_from_permissions should return 'friend' for friend perms."""
        from bookbagofholding.web.auth import get_role_from_permissions, PERM_FRIEND

        assert get_role_from_permissions(PERM_FRIEND) == 'friend'

    def test_get_role_from_permissions_guest(self):
        """get_role_from_permissions should return 'guest' for guest perms or zero."""
        from bookbagofholding.web.auth import get_role_from_permissions, PERM_GUEST

        assert get_role_from_permissions(PERM_GUEST) == 'guest'
        assert get_role_from_permissions(0) == 'guest'

    def test_get_role_from_permissions_readonly(self):
        """get_role_from_permissions should return 'readonly' for low non-zero perms."""
        from bookbagofholding.web.auth import get_role_from_permissions

        # Permission value 1 is just CONFIG, which is below GUEST level
        assert get_role_from_permissions(1) == 'readonly'

    def test_get_role_permissions_admin(self):
        """get_role_permissions should return 65535 for admin."""
        from bookbagofholding.web.auth import get_role_permissions, PERM_ADMIN

        assert get_role_permissions('admin') == PERM_ADMIN

    def test_get_role_permissions_other(self):
        """get_role_permissions should return appropriate permissions for roles."""
        from bookbagofholding.web.auth import get_role_permissions, PERM_GUEST

        assert get_role_permissions('guest') == PERM_GUEST
        # Unknown roles default to guest permissions
        assert get_role_permissions('unknown') == PERM_GUEST


class TestIsAuthenticated:
    """Tests for is_authenticated function."""

    @pytest.fixture
    def mock_bookbagofholding(self):
        with patch.object(auth_module, 'bookbagofholding') as mock:
            mock.CONFIG = {}
            yield mock

    @pytest.fixture
    def mock_cherrypy(self):
        with patch.object(auth_module, 'cherrypy') as mock:
            mock.request = MagicMock()
            mock.request.headers = {}
            mock.request.cookie = {}
            yield mock

    def test_is_authenticated_none_method(self, mock_bookbagofholding, mock_cherrypy):
        """AUTH_METHOD=None should always be authenticated."""
        from bookbagofholding.web.auth import is_authenticated

        mock_bookbagofholding.CONFIG = {'AUTH_METHOD': 'None'}
        assert is_authenticated() is True

    def test_is_authenticated_external_with_header(self, mock_bookbagofholding, mock_cherrypy):
        """AUTH_METHOD=External should be authenticated when header present."""
        from bookbagofholding.web.auth import is_authenticated

        mock_bookbagofholding.CONFIG = {'AUTH_METHOD': 'External', 'AUTH_HEADER': 'X-Forwarded-User'}
        mock_cherrypy.request.headers = {'X-Forwarded-User': 'testuser'}

        assert is_authenticated() is True

    def test_is_authenticated_external_without_header(self, mock_bookbagofholding, mock_cherrypy):
        """AUTH_METHOD=External should not be authenticated without header."""
        from bookbagofholding.web.auth import is_authenticated

        mock_bookbagofholding.CONFIG = {'AUTH_METHOD': 'External', 'AUTH_HEADER': 'X-Forwarded-User'}
        mock_cherrypy.request.headers = {}

        assert is_authenticated() is False

    def test_is_authenticated_forms_with_cookie(self, mock_bookbagofholding, mock_cherrypy):
        """AUTH_METHOD=Forms should be authenticated with valid session."""
        from bookbagofholding.web.auth import is_authenticated

        mock_bookbagofholding.CONFIG = {'AUTH_METHOD': 'Forms'}

        mock_cookie = MagicMock()
        mock_cookie.__contains__ = Mock(return_value=True)
        mock_cookie.__getitem__ = Mock(return_value=MagicMock(value='valid_session_id'))
        mock_cherrypy.request.cookie = mock_cookie

        # Mock the validate_session function to return a valid session
        with patch.object(auth_module, 'validate_session') as mock_validate:
            mock_validate.return_value = {'UserID': 'test_user', 'SessionID': 'valid_session_id'}
            assert is_authenticated() is True

    def test_is_authenticated_forms_without_cookie(self, mock_bookbagofholding, mock_cherrypy):
        """AUTH_METHOD=Forms should not be authenticated without cookie."""
        from bookbagofholding.web.auth import is_authenticated

        mock_bookbagofholding.CONFIG = {'AUTH_METHOD': 'Forms'}
        mock_cherrypy.request.cookie = {}

        assert is_authenticated() is False


class TestPermissionConstants:
    """Tests for permission constants."""

    def test_permission_values(self):
        """Permission flags should have correct values."""
        from bookbagofholding.web.auth import Permission

        assert Permission.CONFIG == 1
        assert Permission.LOGS == 2
        assert Permission.HISTORY == 4
        assert Permission.MANAGE_BOOKS == 8
        assert Permission.MAGAZINES == 16
        assert Permission.AUDIO == 32
        assert Permission.EBOOK == 64
        assert Permission.SERIES == 128
        assert Permission.EDIT == 256
        assert Permission.SEARCH == 512
        assert Permission.STATUS == 1024
        assert Permission.FORCE == 2048
        assert Permission.DOWNLOAD == 4096

    def test_perm_admin_value(self):
        """PERM_ADMIN should be 65535."""
        from bookbagofholding.web.auth import PERM_ADMIN

        assert PERM_ADMIN == 65535


# ============================================================================
# User Management Tests (Database-backed)
# ============================================================================

@pytest.mark.auth
class TestCreateUser:
    """Tests for create_user function."""

    def test_create_user_returns_user_id(self, temp_db):
        """create_user should return a user ID."""
        from bookbagofholding.web.auth import create_user

        user_id = create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com',
            name='Test User',
            role='admin'
        )

        assert user_id is not None
        assert len(user_id) > 0

    def test_create_user_stores_in_database(self, temp_db):
        """create_user should store user in database."""
        from bookbagofholding.web.auth import create_user, get_user_by_username

        create_user(
            username='dbuser',
            password='testpassword123',
            email='db@example.com',
            name='DB User',
            role='admin'
        )

        user = get_user_by_username('dbuser')
        assert user is not None
        assert user['UserName'] == 'dbuser'
        assert user['Email'] == 'db@example.com'
        assert user['Name'] == 'DB User'
        assert user['Role'] == 'admin'

    def test_create_user_hashes_password(self, temp_db):
        """create_user should hash password, not store plaintext."""
        from bookbagofholding.web.auth import create_user, get_user_by_username

        create_user(
            username='hashuser',
            password='plaintextpassword',
            role='guest'
        )

        user = get_user_by_username('hashuser')
        assert user['Password'] != 'plaintextpassword'
        assert len(user['Password']) >= 32  # MD5 or bcrypt hash

    def test_create_user_sets_default_permissions(self, temp_db):
        """create_user should set permissions based on role."""
        from bookbagofholding.web.auth import create_user, get_user_by_username, PERM_ADMIN, PERM_GUEST

        create_user(username='adminuser', password='pass12345678', role='admin')
        create_user(username='guestuser', password='pass12345678', role='guest')

        admin = get_user_by_username('adminuser')
        guest = get_user_by_username('guestuser')

        assert admin['Perms'] == PERM_ADMIN
        assert guest['Perms'] == PERM_GUEST

    def test_create_user_duplicate_username_fails(self, temp_db):
        """create_user should fail for duplicate username."""
        from bookbagofholding.web.auth import create_user

        create_user(username='uniqueuser', password='pass12345678', role='guest')

        # Second creation with same username should raise an error
        with pytest.raises(Exception):
            create_user(username='uniqueuser', password='different123', role='admin')


@pytest.mark.auth
class TestGetUserFunctions:
    """Tests for get_user_by_* functions."""

    def test_get_user_by_username_returns_user(self, temp_db):
        """get_user_by_username should return user dict."""
        from bookbagofholding.web.auth import create_user, get_user_by_username

        create_user(username='findme', password='password1234', email='find@me.com', role='guest')

        user = get_user_by_username('findme')
        assert user is not None
        assert user['UserName'] == 'findme'
        assert user['Email'] == 'find@me.com'

    def test_get_user_by_username_returns_none_for_missing(self, temp_db):
        """get_user_by_username should return None/empty for non-existent user."""
        from bookbagofholding.web.auth import get_user_by_username

        user = get_user_by_username('nonexistent')
        assert not user  # Could be None or empty list

    def test_get_user_by_id_returns_user(self, temp_db):
        """get_user_by_id should return user dict."""
        from bookbagofholding.web.auth import create_user, get_user_by_id

        user_id = create_user(username='byiduser', password='password1234', role='guest')

        user = get_user_by_id(user_id)
        assert user is not None
        assert user['UserID'] == user_id
        assert user['UserName'] == 'byiduser'

    def test_get_user_by_id_returns_none_for_missing(self, temp_db):
        """get_user_by_id should return None/empty for non-existent ID."""
        from bookbagofholding.web.auth import get_user_by_id

        user = get_user_by_id('nonexistent-id')
        assert not user  # Could be None or empty list

    def test_get_user_count_returns_correct_count(self, temp_db):
        """get_user_count should return number of users."""
        from bookbagofholding.web.auth import create_user, get_user_count

        initial_count = get_user_count()
        create_user(username='countuser1', password='password1234', role='guest')
        create_user(username='countuser2', password='password1234', role='guest')

        assert get_user_count() == initial_count + 2


@pytest.mark.auth
class TestSessionManagement:
    """Tests for session management functions."""

    def test_create_session_returns_session_id(self, temp_db):
        """create_session should return a session ID."""
        from bookbagofholding.web.auth import create_user, create_session

        user_id = create_user(username='sessionuser', password='password1234', role='guest')
        session_id = create_session(user_id)

        assert session_id is not None
        assert len(session_id) == 32  # hex string of 16 bytes

    def test_get_user_by_session_returns_user(self, temp_db):
        """get_user_by_session should return user for valid session."""
        from bookbagofholding.web.auth import create_user, create_session, get_user_by_session

        user_id = create_user(username='sessionlookup', password='password1234', role='admin')
        session_id = create_session(user_id)

        user = get_user_by_session(session_id)
        assert user is not None
        assert user['UserID'] == user_id
        assert user['UserName'] == 'sessionlookup'

    def test_get_user_by_session_returns_none_for_invalid(self, temp_db):
        """get_user_by_session should return None/empty for invalid session."""
        from bookbagofholding.web.auth import get_user_by_session

        user = get_user_by_session('invalid-session-id')
        assert not user  # Could be None or empty list

    def test_validate_session_returns_session_data(self, temp_db):
        """validate_session should return session data for valid session."""
        from bookbagofholding.web.auth import create_user, create_session, validate_session

        user_id = create_user(username='validateuser', password='password1234', role='guest')
        session_id = create_session(user_id)

        session = validate_session(session_id)
        assert session is not None
        assert session['SessionID'] == session_id
        assert session['UserID'] == user_id

    def test_revoke_session_deletes_session(self, temp_db):
        """revoke_session should delete the session."""
        from bookbagofholding.web.auth import create_user, create_session, revoke_session, validate_session

        user_id = create_user(username='revokeuser', password='password1234', role='guest')
        session_id = create_session(user_id)

        # Session should exist
        assert validate_session(session_id)

        # Revoke session
        revoke_session(session_id)

        # Session should no longer exist
        assert not validate_session(session_id)

    def test_revoke_user_sessions_deletes_all_sessions(self, temp_db):
        """revoke_user_sessions should delete all sessions for user."""
        from bookbagofholding.web.auth import (
            create_user, create_session, revoke_user_sessions, validate_session
        )

        user_id = create_user(username='revokealluser', password='password1234', role='guest')
        session1 = create_session(user_id)
        session2 = create_session(user_id)
        session3 = create_session(user_id)

        # All sessions should exist
        assert validate_session(session1)
        assert validate_session(session2)
        assert validate_session(session3)

        # Revoke all sessions
        count = revoke_user_sessions(user_id)
        assert count == 3

        # All sessions should be gone
        assert not validate_session(session1)
        assert not validate_session(session2)
        assert not validate_session(session3)

    def test_revoke_user_sessions_except_current(self, temp_db):
        """revoke_user_sessions should keep specified session."""
        from bookbagofholding.web.auth import (
            create_user, create_session, revoke_user_sessions, validate_session
        )

        user_id = create_user(username='exceptuser', password='password1234', role='guest')
        current_session = create_session(user_id)
        other_session1 = create_session(user_id)
        other_session2 = create_session(user_id)

        # Revoke all except current
        count = revoke_user_sessions(user_id, except_session_id=current_session)
        assert count == 2

        # Current session should still exist
        assert validate_session(current_session)
        # Other sessions should be gone
        assert not validate_session(other_session1)
        assert not validate_session(other_session2)

    def test_get_user_sessions_returns_list(self, temp_db):
        """get_user_sessions should return list of sessions."""
        from bookbagofholding.web.auth import create_user, create_session, get_user_sessions

        user_id = create_user(username='listsessions', password='password1234', role='guest')
        create_session(user_id)
        create_session(user_id)

        sessions = get_user_sessions(user_id)
        assert len(sessions) == 2


@pytest.mark.auth
class TestApiKeyManagement:
    """Tests for API key management functions."""

    def test_generate_user_api_key_returns_key(self, temp_db):
        """generate_user_api_key should return an API key."""
        from bookbagofholding.web.auth import create_user, generate_user_api_key

        user_id = create_user(username='apikeyuser', password='password1234', role='guest')
        api_key = generate_user_api_key(user_id)

        assert api_key is not None
        assert len(api_key) == 32  # hex string of 16 bytes

    def test_generate_user_api_key_updates_database(self, temp_db):
        """generate_user_api_key should store key in database."""
        from bookbagofholding.web.auth import create_user, generate_user_api_key, get_user_by_id

        user_id = create_user(username='apidbuser', password='password1234', role='guest')
        api_key = generate_user_api_key(user_id)

        user = get_user_by_id(user_id)
        assert user['ApiKey'] == api_key

    def test_get_user_by_api_key_returns_user(self, temp_db):
        """get_user_by_api_key should return user for valid key."""
        from bookbagofholding.web.auth import create_user, generate_user_api_key, get_user_by_api_key

        user_id = create_user(username='apilookup', password='password1234', role='admin')
        api_key = generate_user_api_key(user_id)

        user = get_user_by_api_key(api_key)
        assert user is not None
        assert user['UserID'] == user_id
        assert user['UserName'] == 'apilookup'

    def test_get_user_by_api_key_returns_none_for_invalid(self, temp_db):
        """get_user_by_api_key should return None for invalid key."""
        from bookbagofholding.web.auth import get_user_by_api_key

        user = get_user_by_api_key('invalid-api-key')
        assert not user

    def test_revoke_user_api_key_clears_key(self, temp_db):
        """revoke_user_api_key should clear the API key."""
        from bookbagofholding.web.auth import (
            create_user, generate_user_api_key, revoke_user_api_key, get_user_by_id
        )

        user_id = create_user(username='revokeapiuser', password='password1234', role='guest')
        api_key = generate_user_api_key(user_id)

        # Key should exist
        user = get_user_by_id(user_id)
        assert user['ApiKey'] == api_key

        # Revoke key
        revoke_user_api_key(user_id)

        # Key should be cleared
        user = get_user_by_id(user_id)
        assert user['ApiKey'] is None


@pytest.mark.auth
class TestPasswordVerification:
    """Tests for password verification with database users."""

    def test_verify_password_md5_correct(self, temp_db):
        """verify_password should accept correct MD5 password."""
        from bookbagofholding.web.auth import create_user, get_user_by_username, verify_password

        create_user(username='md5user', password='correctpassword', role='guest')
        user = get_user_by_username('md5user')

        algorithm = user['PasswordAlgorithm'] if user['PasswordAlgorithm'] else 'md5'
        assert verify_password('correctpassword', user['Password'], algorithm) is True

    def test_verify_password_md5_incorrect(self, temp_db):
        """verify_password should reject incorrect password."""
        from bookbagofholding.web.auth import create_user, get_user_by_username, verify_password

        create_user(username='wrongpassuser', password='correctpassword', role='guest')
        user = get_user_by_username('wrongpassuser')

        algorithm = user['PasswordAlgorithm'] if user['PasswordAlgorithm'] else 'md5'
        assert verify_password('wrongpassword', user['Password'], algorithm) is False
