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
Web handlers for Bookbag of Holding.

This package contains domain-specific handler classes that are used by
the main WebInterface class in webServe.py.

Handler modules:
- author_handler.py - Author-related routes
- book_handler.py - Book-related routes
- magazine_handler.py - Magazine routes
- series_handler.py - Series routes
- config_handler.py - Configuration routes
- search_handler.py - Search routes
- download_handler.py - Download management
- system_handler.py - Logs, history, system
"""

from bookbagofholding.web.handlers.author_handler import AuthorHandler
from bookbagofholding.web.handlers.book_handler import BookHandler

__all__ = [
    'AuthorHandler',
    'BookHandler',
]
