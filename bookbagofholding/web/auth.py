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
Authentication utilities for Bookbag of Holding.

This module provides:
- Database-backed user authentication
- Session management
- Role-based permissions
- Password hashing (MD5 legacy + bcrypt)

AUTH_METHOD options:
- None: No authentication required
- Forms: Login page with username/password (database-backed)
- Basic: HTTP Basic Auth
- External: Trust reverse proxy header
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from enum import IntFlag
from typing import Optional, Tuple

import cherrypy

import bookbagofholding
from bookbagofholding import database

# Try to import bcrypt for secure password hashing
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


class Permission(IntFlag):
    """Permission flags for role-based access control."""
    CONFIG = 1 << 0       # 1 - Access config page
    LOGS = 1 << 1         # 2 - Access logs
    HISTORY = 1 << 2      # 4 - Access history
    MANAGE_BOOKS = 1 << 3 # 8 - Access manage page
    MAGAZINES = 1 << 4    # 16 - Access magazines
    AUDIO = 1 << 5        # 32 - Access audiobooks
    EBOOK = 1 << 6        # 64 - Access ebooks
    SERIES = 1 << 7       # 128 - Access series
    EDIT = 1 << 8         # 256 - Edit book/author details
    SEARCH = 1 << 9       # 512 - Search Goodreads/Google
    STATUS = 1 << 10      # 1024 - Change book status
    FORCE = 1 << 11       # 2048 - Run background tasks
    DOWNLOAD = 1 << 12    # 4096 - Download files


# Pre-defined permission sets
PERM_ADMIN = 65535
PERM_MANAGER = 65532  # All except config/logs
PERM_FRIEND = 5856    # Browse, search, request
PERM_GUEST = 4320     # Browse and download
PERM_READONLY = 240   # View only

# Role to permissions mapping
ROLE_PERMISSIONS = {
    'admin': PERM_ADMIN,
    'manager': PERM_MANAGER,
    'friend': PERM_FRIEND,
    'guest': PERM_GUEST,
    'readonly': PERM_READONLY,
}

AVAILABLE_ROLES = [
    {'value': 'admin', 'label': 'Admin', 'description': 'Full access to all features'},
    {'value': 'manager', 'label': 'Manager', 'description': 'All features except configuration'},
    {'value': 'friend', 'label': 'Friend', 'description': 'Browse, search, and request books'},
    {'value': 'guest', 'label': 'Guest', 'description': 'Browse and download only'},
    {'value': 'readonly', 'label': 'Read Only', 'description': 'View only, no downloads'},
]


# =============================================================================
# Password Functions
# =============================================================================

def hash_password(password: str, algorithm: str = 'bcrypt') -> Tuple[str, str]:
    """Hash a password using bcrypt (preferred) or MD5 (fallback).

    Args:
        password: The plaintext password
        algorithm: 'bcrypt' (default) or 'md5'

    Returns:
        Tuple of (hash, algorithm_used)
    """
    if algorithm == 'bcrypt' and BCRYPT_AVAILABLE:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8'), 'bcrypt'
    # Fallback to MD5
    return hashlib.md5(password.encode('utf-8')).hexdigest(), 'md5'


def hash_password_md5(password: str) -> str:
    """Hash a password using MD5 (legacy support).

    Args:
        password: The plaintext password

    Returns:
        The MD5 hex digest of the password
    """
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def verify_password(password: str, stored_hash: str, algorithm: str = 'md5') -> bool:
    """Verify a password against its hash.

    Supports both MD5 (legacy) and bcrypt algorithms.

    Args:
        password: The plaintext password to verify
        stored_hash: The stored password hash
        algorithm: 'md5' or 'bcrypt'

    Returns:
        True if the password matches
    """
    if algorithm == 'bcrypt' and BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except (ValueError, TypeError):
            return False
    # MD5 comparison
    return hashlib.md5(password.encode('utf-8')).hexdigest() == stored_hash


# =============================================================================
# Database User Functions
# =============================================================================

def get_user_by_username(username: str) -> Optional[dict]:
    """Fetch a user from the database by username.

    Args:
        username: The username to look up

    Returns:
        User dict or None if not found
    """
    myDB = database.DBConnection()
    return myDB.match('SELECT * FROM users WHERE UserName=?', (username,))


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Fetch a user from the database by user ID.

    Args:
        user_id: The UserID to look up

    Returns:
        User dict or None if not found
    """
    myDB = database.DBConnection()
    return myDB.match('SELECT * FROM users WHERE UserID=?', (user_id,))


def get_user_by_session(session_id: str) -> Optional[dict]:
    """Fetch a user from the database by session ID.

    Only returns user if session exists and hasn't expired.

    Args:
        session_id: The session ID from cookie

    Returns:
        User dict or None if session invalid/expired
    """
    if not session_id:
        return None
    myDB = database.DBConnection()
    return myDB.match('''
        SELECT u.* FROM users u
        JOIN sessions s ON u.UserID = s.UserID
        WHERE s.SessionID=? AND s.ExpiresAt > datetime('now')
    ''', (session_id,))


def get_user_count() -> int:
    """Get the total number of users in the database.

    Returns:
        Number of users
    """
    myDB = database.DBConnection()
    result = myDB.match('SELECT count(*) as cnt FROM users')
    return result['cnt'] if result else 0


def create_user(username: str, password: str, email: str = '', name: str = '',
                role: str = 'guest', perms: int = None) -> str:
    """Create a new user in the database.

    Args:
        username: The username
        password: Plaintext password (will be hashed)
        email: Email address
        name: Full name
        role: Role name ('admin', 'manager', 'friend', 'guest', 'readonly')
        perms: Permission bitmask (if None, derived from role)

    Returns:
        The new user's UserID
    """
    from bookbagofholding.common import pwd_generator

    user_id = pwd_generator(16)
    password_hash, algorithm = hash_password(password)

    if perms is None:
        perms = ROLE_PERMISSIONS.get(role, PERM_GUEST)

    myDB = database.DBConnection()
    myDB.action('''
        INSERT INTO users (UserID, UserName, Password, PasswordAlgorithm, Email,
                          Name, Perms, Role, CreatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, password_hash, algorithm, email, name or username,
          perms, role, datetime.now().isoformat()))

    return user_id


# =============================================================================
# Session Functions
# =============================================================================

def create_session(user_id: str, ip_address: str = '', user_agent: str = '') -> str:
    """Create a new session for a user.

    Args:
        user_id: The user's ID
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        The new session ID
    """
    session_id = secrets.token_hex(16)
    timeout_hours = bookbagofholding.CONFIG.get('SESSION_TIMEOUT_HOURS', 24)
    expiry = datetime.now() + timedelta(hours=int(timeout_hours))

    myDB = database.DBConnection()
    myDB.action('''
        INSERT INTO sessions (SessionID, UserID, CreatedAt, ExpiresAt, IPAddress, UserAgent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, user_id, datetime.now().isoformat(), expiry.isoformat(),
          ip_address, user_agent))

    # Enforce max sessions per user
    max_sessions = bookbagofholding.CONFIG.get('MAX_SESSIONS_PER_USER', 5)
    cleanup_excess_sessions(user_id, int(max_sessions))

    return session_id


def validate_session(session_id: str) -> Optional[dict]:
    """Validate a session and return session data if valid.

    Args:
        session_id: The session ID to validate

    Returns:
        Session dict or None if invalid/expired
    """
    if not session_id:
        return None
    myDB = database.DBConnection()
    return myDB.match('''
        SELECT * FROM sessions
        WHERE SessionID=? AND ExpiresAt > datetime('now')
    ''', (session_id,))


def extend_session(session_id: str) -> bool:
    """Extend a session's expiry time.

    Args:
        session_id: The session ID to extend

    Returns:
        True if session was extended
    """
    timeout_hours = bookbagofholding.CONFIG.get('SESSION_TIMEOUT_HOURS', 24)
    new_expiry = datetime.now() + timedelta(hours=int(timeout_hours))

    myDB = database.DBConnection()
    myDB.action('UPDATE sessions SET ExpiresAt=? WHERE SessionID=?',
                (new_expiry.isoformat(), session_id))
    return True


def revoke_session(session_id: str) -> bool:
    """Revoke (delete) a specific session.

    Args:
        session_id: The session ID to revoke

    Returns:
        True if session was deleted
    """
    myDB = database.DBConnection()
    myDB.action('DELETE FROM sessions WHERE SessionID=?', (session_id,))
    return True


def revoke_user_sessions(user_id: str, except_session_id: str = None) -> int:
    """Revoke all sessions for a user.

    Args:
        user_id: The user ID
        except_session_id: Optional session ID to keep (e.g., current session)

    Returns:
        Number of sessions revoked
    """
    myDB = database.DBConnection()
    if except_session_id:
        sessions = myDB.select(
            'SELECT SessionID FROM sessions WHERE UserID=? AND SessionID!=?',
            (user_id, except_session_id)
        )
        count = len(sessions) if sessions else 0
        myDB.action(
            'DELETE FROM sessions WHERE UserID=? AND SessionID!=?',
            (user_id, except_session_id)
        )
    else:
        sessions = myDB.select('SELECT SessionID FROM sessions WHERE UserID=?', (user_id,))
        count = len(sessions) if sessions else 0
        myDB.action('DELETE FROM sessions WHERE UserID=?', (user_id,))
    return count


def cleanup_expired_sessions() -> int:
    """Delete all expired sessions from the database.

    Returns:
        Number of sessions cleaned up
    """
    myDB = database.DBConnection()
    expired = myDB.select("SELECT SessionID FROM sessions WHERE ExpiresAt <= datetime('now')")
    count = len(expired) if expired else 0
    myDB.action("DELETE FROM sessions WHERE ExpiresAt <= datetime('now')")
    return count


def cleanup_excess_sessions(user_id: str, max_sessions: int) -> int:
    """Delete oldest sessions if user exceeds max allowed.

    Args:
        user_id: The user ID
        max_sessions: Maximum sessions allowed per user

    Returns:
        Number of sessions deleted
    """
    myDB = database.DBConnection()
    sessions = myDB.select('''
        SELECT SessionID FROM sessions
        WHERE UserID=?
        ORDER BY CreatedAt DESC
    ''', (user_id,))

    if not sessions or len(sessions) <= max_sessions:
        return 0

    # Delete oldest sessions beyond the limit
    to_delete = sessions[max_sessions:]
    for session in to_delete:
        myDB.action('DELETE FROM sessions WHERE SessionID=?', (session['SessionID'],))

    return len(to_delete)


def get_user_sessions(user_id: str = None) -> list:
    """Get active sessions for a user.

    Args:
        user_id: The user ID (if None, gets sessions for current user)

    Returns:
        List of session dicts
    """
    if not user_id:
        # Try to get current user's sessions
        session_id = get_session_from_cookie()
        user = get_user_by_session(session_id)
        if user:
            user_id = user['UserID']
        else:
            return []

    myDB = database.DBConnection()
    sessions = myDB.select('''
        SELECT SessionID, CreatedAt, ExpiresAt, IPAddress, UserAgent
        FROM sessions
        WHERE UserID=? AND ExpiresAt > datetime('now')
        ORDER BY CreatedAt DESC
    ''', (user_id,))

    return sessions if sessions else []


# =============================================================================
# Cookie Functions
# =============================================================================

def get_session_from_cookie() -> Optional[str]:
    """Get the session ID from the request cookie.

    Returns:
        Session ID string or None
    """
    try:
        cookie = cherrypy.request.cookie
        if cookie and 'll_uid' in cookie:
            return cookie['ll_uid'].value
    except Exception:
        pass
    return None


def set_session_cookie(session_id: str) -> None:
    """Set the session cookie in the response.

    Args:
        session_id: The session ID to set
    """
    timeout_hours = bookbagofholding.CONFIG.get('SESSION_TIMEOUT_HOURS', 24)
    max_age = int(timeout_hours) * 3600

    cherrypy.response.cookie['ll_uid'] = session_id
    cherrypy.response.cookie['ll_uid']['path'] = '/'
    cherrypy.response.cookie['ll_uid']['max-age'] = max_age
    cherrypy.response.cookie['ll_uid']['httponly'] = True


def clear_session_cookie() -> None:
    """Clear the session cookie, logging out the user."""
    cherrypy.response.cookie['ll_uid'] = ''
    cherrypy.response.cookie['ll_uid']['path'] = '/'
    cherrypy.response.cookie['ll_uid']['expires'] = 0
    cherrypy.response.cookie['ll_uid']['max-age'] = 0


# Legacy aliases
set_login_cookie = lambda: set_session_cookie('authenticated')  # For backward compat
clear_login_cookie = clear_session_cookie


# =============================================================================
# Authentication Functions
# =============================================================================

def is_authenticated() -> bool:
    """Check if the current request is authenticated.

    Returns:
        True if user is authenticated
    """
    auth_method = bookbagofholding.CONFIG.get('AUTH_METHOD', 'Forms')

    if auth_method == 'None':
        return True  # No auth = everyone authenticated

    if auth_method == 'External':
        header = bookbagofholding.CONFIG.get('AUTH_HEADER', 'X-Forwarded-User')
        return bool(cherrypy.request.headers.get(header, ''))

    if auth_method == 'Forms':
        session_id = get_session_from_cookie()
        if session_id:
            session = validate_session(session_id)
            return session is not None
        return False

    if auth_method == 'Basic':
        # If we get here, CherryPy's basic auth already passed
        return True

    return False


def get_current_user() -> Optional[dict]:
    """Get the currently authenticated user.

    Returns:
        User dict or None if not authenticated
    """
    auth_method = bookbagofholding.CONFIG.get('AUTH_METHOD', 'Forms')

    if auth_method == 'None':
        # Return a virtual admin user
        return {
            'UserID': 'admin',
            'UserName': 'admin',
            'Name': 'Administrator',
            'Email': '',
            'Perms': PERM_ADMIN,
            'Role': 'admin',
        }

    if auth_method == 'External':
        header = bookbagofholding.CONFIG.get('AUTH_HEADER', 'X-Forwarded-User')
        username = cherrypy.request.headers.get(header, '')
        if username:
            # Look up or create external user
            user = get_user_by_username(username)
            if not user:
                # Auto-create external users as guests
                user_id = create_user(username, secrets.token_hex(32), role='guest')
                user = get_user_by_id(user_id)
            return user
        return None

    if auth_method == 'Forms':
        session_id = get_session_from_cookie()
        return get_user_by_session(session_id)

    if auth_method == 'Basic':
        # For basic auth, use the config username
        username = bookbagofholding.CONFIG.get('HTTP_USER', 'admin')
        user = get_user_by_username(username)
        if user:
            return user
        # Return a virtual admin if no matching database user
        return {
            'UserID': 'basic_auth',
            'UserName': username,
            'Name': username,
            'Email': '',
            'Perms': PERM_ADMIN,
            'Role': 'admin',
        }

    return None


def get_username() -> str:
    """Get the current authenticated username.

    Returns:
        The username or 'admin' as default
    """
    user = get_current_user()
    if user:
        return user['UserName'] if user['UserName'] else 'admin'
    return 'admin'


def get_user_from_cookie() -> tuple:
    """Get user info from cookie/session.

    Returns:
        Tuple of (username, permissions)
    """
    user = get_current_user()
    if user:
        username = user['UserName'] if user['UserName'] else 'admin'
        perms = user['Perms'] if user['Perms'] else PERM_ADMIN
        return username, perms
    return None, 0


# =============================================================================
# Role Functions
# =============================================================================

def get_role_from_permissions(perms: int) -> str:
    """Get role name from permissions bitmask.

    Args:
        perms: The permission bitmask

    Returns:
        Role name string
    """
    if perms >= PERM_ADMIN:
        return 'admin'
    elif perms >= PERM_MANAGER:
        return 'manager'
    elif perms >= PERM_FRIEND:
        return 'friend'
    elif perms >= PERM_GUEST:
        return 'guest'
    elif perms > 0:
        return 'readonly'
    return 'guest'


def get_role_permissions(role: str) -> int:
    """Get permissions bitmask for a role.

    Args:
        role: The role name

    Returns:
        Permission bitmask
    """
    return ROLE_PERMISSIONS.get(role, PERM_GUEST)


def check_permission(required_perm: int, user_perm: int) -> bool:
    """Check if user has the required permission.

    Args:
        required_perm: The permission flag(s) required
        user_perm: The user's permission flags

    Returns:
        True if user has all required permissions
    """
    return bool(user_perm & required_perm)


def get_template_permission_for_page(templatename: str, username: str, perm: int) -> tuple:
    """Check page-specific permissions.

    Args:
        templatename: The template being requested
        username: The username
        perm: The user's permission bitmask

    Returns:
        Tuple of (templatename, perm)
    """
    # Could add page-specific permission checks here
    return templatename, perm


# =============================================================================
# API Key Functions
# =============================================================================

def generate_user_api_key(user_id: str) -> str:
    """Generate a new API key for a user.

    Args:
        user_id: The user ID

    Returns:
        The new API key
    """
    api_key = secrets.token_hex(16)
    myDB = database.DBConnection()
    myDB.action('UPDATE users SET ApiKey=? WHERE UserID=?', (api_key, user_id))
    return api_key


def revoke_user_api_key(user_id: str) -> bool:
    """Revoke a user's API key.

    Args:
        user_id: The user ID

    Returns:
        True if API key was revoked
    """
    myDB = database.DBConnection()
    myDB.action('UPDATE users SET ApiKey=NULL WHERE UserID=?', (user_id,))
    return True


def get_user_by_api_key(api_key: str) -> Optional[dict]:
    """Get a user by their API key.

    Args:
        api_key: The API key

    Returns:
        User dict or None
    """
    if not api_key:
        return None
    myDB = database.DBConnection()
    return myDB.match('SELECT * FROM users WHERE ApiKey=?', (api_key,))
