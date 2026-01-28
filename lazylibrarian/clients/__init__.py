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
Download client infrastructure for LazyLibrarian.

This package provides base classes and utilities for download clients:
- base.py: Abstract base classes for NZB and Torrent clients
- http_wrapper.py: Consistent HTTP request handling
"""

from lazylibrarian.clients.base import DownloadClient, NzbClient, TorrentClient
from lazylibrarian.clients.http_wrapper import HTTPClientWrapper

__all__ = ['DownloadClient', 'NzbClient', 'TorrentClient', 'HTTPClientWrapper']
