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
URL building and normalization utilities.

Consolidates URL construction patterns used across download clients.
"""

from urllib.parse import urlparse, urlunparse


class URLBuilder:
    """Utility class for building and normalizing URLs."""

    @staticmethod
    def normalize_host(hostname, port=None, use_https=False):
        """
        Normalize hostname to proper URL format.

        Handles:
        - Adding http/https protocol if missing
        - Removing duplicate protocols
        - Stripping trailing slashes
        - Appending port numbers

        Args:
            hostname: The hostname or URL to normalize
            port: Optional port number (int or str)
            use_https: If True, use https:// protocol (default: False)

        Returns:
            Normalized URL string, or empty string if hostname is empty
        """
        if not hostname:
            return ''

        hostname = str(hostname).strip()

        # Detect if https is already specified
        if hostname.startswith('https://'):
            use_https = True
            hostname = hostname[8:]
        elif hostname.startswith('http://'):
            hostname = hostname[7:]

        # Remove trailing slashes
        hostname = hostname.rstrip('/')

        # Remove /gui suffix if present (common in torrent clients)
        if hostname.endswith('/gui'):
            hostname = hostname[:-4]

        # Build URL
        protocol = 'https' if use_https else 'http'
        url = '%s://%s' % (protocol, hostname)

        # Add port if specified and valid
        if port:
            try:
                port_int = int(port)
                if port_int > 0:
                    url = '%s:%d' % (url, port_int)
            except (ValueError, TypeError):
                pass

        return url

    @staticmethod
    def append_path(base_url, path):
        """
        Append a path segment to a base URL.

        Args:
            base_url: The base URL
            path: Path segment to append (leading/trailing slashes handled)

        Returns:
            Combined URL string
        """
        if not base_url:
            return ''
        if not path:
            return base_url

        base_url = base_url.rstrip('/')
        path = path.strip('/')

        return '%s/%s' % (base_url, path)

    @staticmethod
    def build_api_url(base_url, endpoint, params=None):
        """
        Build an API URL with optional query parameters.

        Args:
            base_url: The base URL
            endpoint: API endpoint path
            params: Optional dict of query parameters

        Returns:
            Complete API URL string
        """
        from urllib.parse import urlencode

        url = URLBuilder.append_path(base_url, endpoint)

        if params:
            # Filter out None values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url = '%s?%s' % (url, urlencode(filtered_params))

        return url

    @staticmethod
    def extract_host_port(url):
        """
        Extract host and port from a URL.

        Args:
            url: URL string to parse

        Returns:
            Tuple of (host, port) where port may be None
        """
        if not url:
            return None, None

        # Add protocol if missing for proper parsing
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url

        parsed = urlparse(url)
        return parsed.hostname, parsed.port

    @staticmethod
    def is_https(url):
        """
        Check if a URL uses HTTPS.

        Args:
            url: URL string to check

        Returns:
            True if URL uses HTTPS, False otherwise
        """
        if not url:
            return False
        return str(url).lower().startswith('https://')
