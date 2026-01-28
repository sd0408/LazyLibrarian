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
Authentication and permission utilities for LazyLibrarian web interface.

This module provides:
- Permission constants and checking
- User session management via cookies
- Password hashing and verification
"""

import hashlib
from enum import IntFlag
from typing import Optional, Tuple

import cherrypy

import lazylibrarian
from lazylibrarian import database, logger
from lazylibrarian.formatter import check_int


class Permission(IntFlag):
    """Permission flags for user access control.

    These flags can be combined using bitwise OR (|) to grant multiple permissions.
    Check permissions using bitwise AND (&).

    Example:
        user_perms = Permission.CONFIG | Permission.LOGS
        if user_perms & Permission.CONFIG:
            # User has config access
    """
    CONFIG = 1 << 0       # 1 - access to config page
    LOGS = 1 << 1         # 2 - access to logs
    HISTORY = 1 << 2      # 4 - access to history
    MANAGE_BOOKS = 1 << 3 # 8 - access to manage page
    MAGAZINES = 1 << 4    # 16 - access to magazines/issues/pastissues
    AUDIO = 1 << 5        # 32 - access to audiobooks page
    EBOOK = 1 << 6        # 64 - access to ebooks page
    SERIES = 1 << 7       # 128 - access to series/seriesmembers
    EDIT = 1 << 8         # 256 - can edit book or author details
    SEARCH = 1 << 9       # 512 - can search goodreads/googlebooks
    STATUS = 1 << 10      # 1024 - can change book status
    FORCE = 1 << 11       # 2048 - can use background tasks
    DOWNLOAD = 1 << 12    # 4096 - can download existing books/mags


# Pre-defined permission sets
PERM_AUTHOR_BOOKS = Permission.AUDIO | Permission.EBOOK
PERM_GUEST = Permission.DOWNLOAD | Permission.SERIES | PERM_AUTHOR_BOOKS | Permission.MAGAZINES
PERM_FRIEND = PERM_GUEST | Permission.SEARCH | Permission.STATUS
PERM_ADMIN = 65535


def get_user_from_cookie() -> Tuple[Optional[str], int]:
    """Get the current user from the session cookie.

    Returns:
        Tuple of (username, permissions). Returns (None, 0) if no valid session.
    """
    username = None
    perm = 0

    try:
        myDB = database.DBConnection()
        cookie = cherrypy.request.cookie

        if cookie and 'll_uid' in list(cookie.keys()):
            res = myDB.match(
                'SELECT UserName, Perms FROM users WHERE UserID=?',
                (cookie['ll_uid'].value,)
            )
            if res:
                perm = check_int(res['Perms'], 0)
                username = res['UserName']
        else:
            # Check for single-user auto-login
            cnt = myDB.match("SELECT count(*) as counter FROM users")
            if cnt and cnt['counter'] == 1 and lazylibrarian.CONFIG['SINGLE_USER']:
                res = myDB.match('SELECT UserName, Perms, UserID FROM users')
                if res:
                    cherrypy.response.cookie['ll_uid'] = res['UserID']
                    logger.debug("Auto-login for %s" % res['UserName'])
                    lazylibrarian.SHOWLOGOUT = 0
                    perm = check_int(res['Perms'], 0)
                    username = res['UserName']
            else:
                lazylibrarian.SHOWLOGOUT = 1

    except Exception as e:
        logger.error("Error getting user from cookie: %s" % str(e))

    return username, perm


def check_permission(required_perm: int, user_perm: int) -> bool:
    """Check if user has the required permission.

    Args:
        required_perm: The permission flag(s) required
        user_perm: The user's permission flags

    Returns:
        True if user has all required permissions
    """
    return bool(user_perm & required_perm)


def hash_password(password: str) -> str:
    """Hash a password using MD5.

    Note: MD5 is used for backward compatibility with existing user database.
    New implementations should consider using a more secure algorithm.

    Args:
        password: The plaintext password

    Returns:
        The MD5 hex digest of the password
    """
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: The plaintext password to verify
        hashed: The stored password hash

    Returns:
        True if the password matches
    """
    return hash_password(password) == hashed


def get_template_permission_for_page(templatename: str, username: str, perm: int) -> Tuple[str, bool]:
    """Check if user has permission to access a template and redirect if not.

    Args:
        templatename: The template being requested
        username: The current user's name
        perm: The user's permission flags

    Returns:
        Tuple of (templatename to render, should_log_warning)
        Returns login.html if user lacks permission.
    """
    permission_map = {
        'config.html': lazylibrarian.perm_config,
        'logs.html': lazylibrarian.perm_logs,
        'history.html': lazylibrarian.perm_history,
        'managebooks.html': lazylibrarian.perm_managebooks,
        'books.html': lazylibrarian.perm_ebook,
        'audio.html': lazylibrarian.perm_audio,
        'choosetype.html': lazylibrarian.perm_download,
    }

    # Special cases with multiple conditions
    if templatename == 'author.html':
        if not (perm & lazylibrarian.perm_ebook or perm & lazylibrarian.perm_audio):
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    elif templatename in ['magazines.html', 'issues.html', 'manageissues.html']:
        if not perm & lazylibrarian.perm_magazines:
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    elif templatename in ['series.html', 'members.html']:
        if not perm & lazylibrarian.perm_series:
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    elif templatename in ['editauthor.html', 'editbook.html']:
        if not perm & lazylibrarian.perm_edit:
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    elif templatename in ['manualsearch.html', 'searchresults.html']:
        if not perm & lazylibrarian.perm_search:
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    elif templatename in permission_map:
        required_perm = permission_map[templatename]
        if not perm & required_perm:
            logger.warn('User %s attempted to access %s' % (username, templatename))
            return 'login.html', True

    return templatename, False


def set_login_cookie(user_id: str) -> None:
    """Set the login cookie for a user.

    Args:
        user_id: The user's ID to store in the cookie
    """
    cherrypy.response.cookie['ll_uid'] = user_id


def clear_login_cookie() -> None:
    """Clear the login cookie, logging out the user."""
    cherrypy.response.cookie['ll_uid'] = ''
    cherrypy.response.cookie['ll_uid']['expires'] = 0
