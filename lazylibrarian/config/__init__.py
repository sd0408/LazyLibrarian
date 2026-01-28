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
Configuration module for LazyLibrarian.

This module provides type-safe configuration management.
"""

from lazylibrarian.config.settings import (
    Configuration,
    GeneralSettings,
    HttpSettings,
    SearchSettings,
    DownloadSettings,
    NotificationSettings,
    LibrarySettings,
    PostProcessSettings,
    ConfigError,
)
from lazylibrarian.config.loader import ConfigLoader

__all__ = [
    'Configuration',
    'GeneralSettings',
    'HttpSettings',
    'SearchSettings',
    'DownloadSettings',
    'NotificationSettings',
    'LibrarySettings',
    'PostProcessSettings',
    'ConfigLoader',
    'ConfigError',
]
