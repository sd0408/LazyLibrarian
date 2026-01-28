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
API v2 module for LazyLibrarian.

This module contains the refactored API handlers, organized by domain:
- author_api.py - Author-related API endpoints
- book_api.py - Book-related API endpoints
- magazine_api.py - Magazine-related API endpoints
- series_api.py - Series-related API endpoints
- system_api.py - System and configuration endpoints

The Api class in the original api.py can delegate to these handlers.
"""

from lazylibrarian.api_v2.base import ApiBase, api_endpoint, require_param
from lazylibrarian.api_v2.author_api import AuthorApi
from lazylibrarian.api_v2.book_api import BookApi
from lazylibrarian.api_v2.magazine_api import MagazineApi
from lazylibrarian.api_v2.system_api import SystemApi

__all__ = [
    'ApiBase',
    'api_endpoint',
    'require_param',
    'AuthorApi',
    'BookApi',
    'MagazineApi',
    'SystemApi',
]
