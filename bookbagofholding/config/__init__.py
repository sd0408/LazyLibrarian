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
Configuration module for Bookbag of Holding.

This module provides type-safe configuration management.
"""

from bookbagofholding.config.settings import (
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
from bookbagofholding.config.loader import ConfigLoader

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
