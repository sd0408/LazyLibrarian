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
Web module for LazyLibrarian.

This module contains the refactored web interface handlers, organized by domain:
- handlers/author_handler.py - Author-related routes
- handlers/book_handler.py - Book-related routes
- handlers/magazine_handler.py - Magazine routes
- handlers/series_handler.py - Series routes
- handlers/config_handler.py - Configuration routes
- handlers/search_handler.py - Search routes
- handlers/download_handler.py - Download management
- handlers/system_handler.py - Logs, history, system

The WebInterface class in webServe.py delegates to these handlers.
"""

from lazylibrarian.web.auth import (
    check_permission,
    get_user_from_cookie,
    hash_password,
    verify_password,
    Permission,
)
from lazylibrarian.web.templates import serve_template

__all__ = [
    'check_permission',
    'get_user_from_cookie',
    'hash_password',
    'verify_password',
    'Permission',
    'serve_template',
]
