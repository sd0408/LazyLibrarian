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
Base classes for download clients.

Provides abstract base classes that define the interface for NZB and Torrent
download clients, along with common functionality like configuration loading,
URL building, and error handling.
"""

from abc import ABC, abstractmethod

import bookbagofholding
from bookbagofholding import logger
from bookbagofholding.formatter import check_int
from bookbagofholding.utils.url_builder import URLBuilder
from bookbagofholding.clients.http_wrapper import (
    HTTPClientWrapper, HTTPClientError, HTTPTimeoutError,
    HTTPConnectionError, make_result, result_from_exception
)


class DownloadClient(ABC):
    """
    Abstract base class for all download clients.

    Provides common functionality:
    - Configuration loading from bookbagofholding.CONFIG
    - URL building and normalization
    - HTTP client setup
    - Standard error handling patterns

    Subclasses must implement:
    - CLIENT_NAME: Human-readable name for logging
    - CONFIG_PREFIX: Prefix for config keys (e.g., 'SAB', 'QBITTORRENT')
    - check_link(): Test connection to the client
    """

    # Override in subclasses
    CLIENT_NAME = None  # e.g., "SABnzbd", "qBittorrent"
    CONFIG_PREFIX = None  # e.g., "SAB", "QBITTORRENT"

    def __init__(self):
        """Initialize the download client."""
        self._http = None
        self._base_url = None
        self._validate_class_attrs()

    def _validate_class_attrs(self):
        """Ensure required class attributes are set."""
        if not self.CLIENT_NAME:
            raise NotImplementedError("Subclass must define CLIENT_NAME")
        if not self.CONFIG_PREFIX:
            raise NotImplementedError("Subclass must define CONFIG_PREFIX")

    @property
    def config(self):
        """Access the global config dict."""
        return bookbagofholding.CONFIG

    def get_config(self, key, default=None):
        """
        Get a configuration value for this client.

        Args:
            key: Config key name (without prefix)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        full_key = '%s_%s' % (self.CONFIG_PREFIX, key)
        return self.config.get(full_key, default)

    def get_config_int(self, key, default=0):
        """
        Get a configuration value as an integer.

        Args:
            key: Config key name (without prefix)
            default: Default value if key not found or not an int

        Returns:
            Integer configuration value or default
        """
        return check_int(self.get_config(key), default)

    @property
    def host(self):
        """Get the configured host."""
        return self.get_config('HOST', '')

    @property
    def port(self):
        """Get the configured port."""
        return self.get_config_int('PORT', 0)

    @property
    def username(self):
        """Get the configured username."""
        return self.get_config('USER', '')

    @property
    def password(self):
        """Get the configured password."""
        return self.get_config('PASS', '')

    @property
    def base_url(self):
        """
        Get the base URL for this client.

        Builds the URL from host and port configuration.
        Override in subclasses if additional URL components needed.
        """
        if self._base_url is None:
            use_https = self.get_config('HTTPS', False) or self.host.startswith('https://')
            self._base_url = URLBuilder.normalize_host(self.host, self.port, use_https)
        return self._base_url

    def validate_config(self):
        """
        Validate that required configuration is present.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.host:
            return False, "Invalid %s host, check your config" % self.CLIENT_NAME

        if not self.port:
            return False, "Invalid %s port, check your config" % self.CLIENT_NAME

        return True, ''

    @property
    def http(self):
        """
        Get the HTTP client wrapper for this client.

        Lazily initializes the HTTPClientWrapper.
        """
        if self._http is None:
            self._http = HTTPClientWrapper(self.CLIENT_NAME)
        return self._http

    @abstractmethod
    def check_link(self):
        """
        Test the connection to the download client.

        Returns:
            String message describing the connection status
        """
        pass

    def _make_result(self, success, message=''):
        """Create a standard result tuple."""
        return make_result(success, message)

    def _error_result(self, message):
        """Create an error result tuple."""
        logger.error(message)
        return make_result(False, message)

    def _handle_exception(self, exception, context=''):
        """
        Handle an exception and return a result tuple.

        Args:
            exception: The exception that occurred
            context: Optional context string for logging

        Returns:
            Tuple of (False, error_message)
        """
        return result_from_exception(exception, context or self.CLIENT_NAME)


class NzbClient(DownloadClient):
    """
    Base class for NZB download clients (SABnzbd, NZBGet).

    Extends DownloadClient with NZB-specific functionality:
    - Category/group configuration
    - Priority settings
    - NZB submission

    Subclasses must implement:
    - send_nzb(): Send an NZB to the client
    """

    @property
    def category(self):
        """Get the configured category/group for downloads."""
        return self.get_config('CAT', '')

    @property
    def api_key(self):
        """Get the configured API key."""
        return self.get_config('API', '') or self.get_config('APIKEY', '')

    @abstractmethod
    def send_nzb(self, title, nzb_url):
        """
        Send an NZB to the download client.

        Args:
            title: Title/name for the download
            nzb_url: URL of the NZB file

        Returns:
            Tuple of (success, message_or_id)
            On success: (download_id, '')
            On failure: (False, error_message)
        """
        pass

    def get_queue(self):
        """
        Get the current download queue.

        Override in subclasses if supported.

        Returns:
            List of queue items or None if not supported
        """
        return None

    def get_history(self):
        """
        Get the download history.

        Override in subclasses if supported.

        Returns:
            List of history items or None if not supported
        """
        return None

    def delete_download(self, download_id, remove_data=False):
        """
        Delete a download from the queue or history.

        Override in subclasses if supported.

        Args:
            download_id: ID of the download to delete
            remove_data: Whether to also delete downloaded files

        Returns:
            Tuple of (success, message)
        """
        return False, "Delete not supported for %s" % self.CLIENT_NAME


class TorrentClient(DownloadClient):
    """
    Base class for Torrent download clients.

    Extends DownloadClient with torrent-specific functionality:
    - Label/category configuration
    - Torrent submission (URL and file)
    - Progress tracking
    - Seeding management

    Subclasses must implement:
    - add_torrent(): Add a torrent via URL/magnet
    - get_progress(): Get torrent download progress
    - remove_torrent(): Remove a torrent
    """

    @property
    def label(self):
        """Get the configured label/category for torrents."""
        return self.get_config('LABEL', '') or self.get_config('CAT', '')

    @property
    def download_dir(self):
        """Get the configured download directory."""
        return self.get_config('DIR', '')

    @abstractmethod
    def add_torrent(self, link, hashid):
        """
        Add a torrent via URL or magnet link.

        Args:
            link: Torrent URL or magnet link
            hashid: Expected torrent hash (lowercase)

        Returns:
            Tuple of (success, message)
        """
        pass

    def add_torrent_file(self, data, hashid, title):
        """
        Add a torrent from file data.

        Override in subclasses if supported.

        Args:
            data: Raw torrent file data
            hashid: Expected torrent hash (lowercase)
            title: Title for the torrent

        Returns:
            Tuple of (success, message)
        """
        return False, "Torrent file upload not supported for %s" % self.CLIENT_NAME

    @abstractmethod
    def get_progress(self, hashid):
        """
        Get the progress of a torrent.

        Args:
            hashid: Torrent hash (lowercase)

        Returns:
            Tuple of (progress_percent, state_string) or (False, '') on error
            progress_percent: 0-100 or -1 if not found
        """
        pass

    @abstractmethod
    def remove_torrent(self, hashid, remove_data=False):
        """
        Remove a torrent.

        Args:
            hashid: Torrent hash (lowercase)
            remove_data: Whether to also delete downloaded files

        Returns:
            True if removed, False otherwise
        """
        pass

    def get_name(self, hashid):
        """
        Get the name of a torrent.

        Override in subclasses if supported.

        Args:
            hashid: Torrent hash (lowercase)

        Returns:
            Torrent name string or empty string if not found
        """
        return ''

    def get_folder(self, hashid):
        """
        Get the download folder for a torrent.

        Override in subclasses if supported.

        Args:
            hashid: Torrent hash (lowercase)

        Returns:
            Folder path or None if not found
        """
        return None

    def get_files(self, hashid):
        """
        Get the files in a torrent.

        Override in subclasses if supported.

        Args:
            hashid: Torrent hash (lowercase)

        Returns:
            List of file info dicts or empty string if not found
        """
        return ''

    def should_wait_for_seeding(self):
        """
        Check if we should wait for seeding before removing.

        Returns:
            True if SEED_WAIT config is enabled
        """
        return bool(bookbagofholding.CONFIG.get('SEED_WAIT', False))

    def is_seeding(self, state):
        """
        Check if a torrent state indicates seeding.

        Args:
            state: Torrent state string

        Returns:
            True if torrent is seeding
        """
        seeding_states = ['uploading', 'stalledup', 'seeding', 'queuedup']
        return state.lower().replace('_', '') in seeding_states
