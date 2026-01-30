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
HTTP client wrapper for consistent request handling.

Provides a unified interface for HTTP requests across all download clients
with consistent error handling, logging, and proxy support.
"""

import requests

import bookbagofholding
from bookbagofholding import logger
from bookbagofholding.common import proxyList
from bookbagofholding.formatter import check_int


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class HTTPTimeoutError(HTTPClientError):
    """Request timed out."""
    pass


class HTTPConnectionError(HTTPClientError):
    """Failed to connect to server."""
    pass


class HTTPResponseError(HTTPClientError):
    """Server returned an error response."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HTTPClientWrapper:
    """
    Wrapper for HTTP requests with consistent error handling and logging.

    Consolidates the common HTTP request patterns used across download clients:
    - Timeout handling
    - Proxy configuration
    - Error extraction and formatting
    - Debug logging
    """

    def __init__(self, client_name, timeout=None, proxies=None, verify_ssl=True):
        """
        Initialize the HTTP client wrapper.

        Args:
            client_name: Name of the client for logging (e.g., "SABnzbd", "qBittorrent")
            timeout: Request timeout in seconds (default: from config or 30)
            proxies: Proxy configuration dict (default: from config)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.client_name = client_name
        self.timeout = timeout or check_int(bookbagofholding.CONFIG.get('HTTP_TIMEOUT', 30), 30)
        self.proxies = proxies if proxies is not None else proxyList()
        self.verify_ssl = verify_ssl

    def get(self, url, params=None, headers=None, auth=None, **kwargs):
        """
        Perform a GET request.

        Args:
            url: The URL to request
            params: Optional query parameters dict
            headers: Optional headers dict
            auth: Optional authentication tuple (username, password)
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            requests.Response object

        Raises:
            HTTPTimeoutError: If the request times out
            HTTPConnectionError: If connection fails
            HTTPResponseError: If server returns an error
        """
        return self._request('GET', url, params=params, headers=headers, auth=auth, **kwargs)

    def post(self, url, data=None, json=None, headers=None, auth=None, **kwargs):
        """
        Perform a POST request.

        Args:
            url: The URL to request
            data: Optional form data dict or string
            json: Optional JSON data dict
            headers: Optional headers dict
            auth: Optional authentication tuple (username, password)
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            requests.Response object

        Raises:
            HTTPTimeoutError: If the request times out
            HTTPConnectionError: If connection fails
            HTTPResponseError: If server returns an error
        """
        return self._request('POST', url, data=data, json=json, headers=headers, auth=auth, **kwargs)

    def _request(self, method, url, **kwargs):
        """
        Internal method to perform HTTP requests with error handling.

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            url: The URL to request
            **kwargs: Arguments passed to requests

        Returns:
            requests.Response object

        Raises:
            HTTPTimeoutError: If the request times out
            HTTPConnectionError: If connection fails
        """
        # Set defaults
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('proxies', self.proxies)
        kwargs.setdefault('verify', self.verify_ssl)

        # Debug logging
        if bookbagofholding.LOGLEVEL & bookbagofholding.log_dlcomms:
            logger.debug('Request %s for <a href="%s">%s</a>' % (method, url, self.client_name))

        try:
            if method.upper() == 'GET':
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, **kwargs)
            else:
                response = requests.request(method, url, **kwargs)

            # Debug log response
            if bookbagofholding.LOGLEVEL & bookbagofholding.log_dlcomms:
                logger.debug('%s response status: %s' % (self.client_name, response.status_code))

            return response

        except requests.exceptions.Timeout:
            msg = "Timeout connecting to %s with URL: %s" % (self.client_name, url)
            logger.error(msg)
            raise HTTPTimeoutError(msg)

        except requests.exceptions.ConnectionError as e:
            msg = "Unable to connect to %s: %s" % (self.client_name, self._extract_error_message(e))
            logger.error(msg)
            raise HTTPConnectionError(msg)

        except Exception as e:
            msg = "Error communicating with %s: %s" % (self.client_name, self._extract_error_message(e))
            logger.error(msg)
            raise HTTPClientError(msg)

    def get_json(self, url, params=None, headers=None, auth=None, **kwargs):
        """
        Perform a GET request and parse JSON response.

        Args:
            url: The URL to request
            params: Optional query parameters dict
            headers: Optional headers dict
            auth: Optional authentication tuple
            **kwargs: Additional arguments

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            HTTPClientError: If request fails or JSON parsing fails
        """
        response = self.get(url, params=params, headers=headers, auth=auth, **kwargs)
        return self._parse_json_response(response)

    def post_json(self, url, data=None, json=None, headers=None, auth=None, **kwargs):
        """
        Perform a POST request and parse JSON response.

        Args:
            url: The URL to request
            data: Optional form data
            json: Optional JSON data
            headers: Optional headers dict
            auth: Optional authentication tuple
            **kwargs: Additional arguments

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            HTTPClientError: If request fails or JSON parsing fails
        """
        response = self.post(url, data=data, json=json, headers=headers, auth=auth, **kwargs)
        return self._parse_json_response(response)

    def _parse_json_response(self, response):
        """
        Parse a JSON response with error handling.

        Args:
            response: requests.Response object

        Returns:
            Parsed JSON data

        Raises:
            HTTPResponseError: If JSON parsing fails
        """
        try:
            result = response.json()
            if bookbagofholding.LOGLEVEL & bookbagofholding.log_dlcomms:
                logger.debug("Result from %s: %s" % (self.client_name, str(result)))
            return result
        except ValueError as e:
            msg = "%s returned invalid JSON: %s" % (self.client_name, str(e))
            logger.error(msg)
            raise HTTPResponseError(msg, response.status_code, response.text)

    @staticmethod
    def _extract_error_message(exception):
        """
        Extract a readable error message from an exception.

        Handles various exception types that may have different attributes
        for storing the error message.

        Args:
            exception: The exception to extract message from

        Returns:
            String error message
        """
        if hasattr(exception, 'reason'):
            return str(exception.reason)
        elif hasattr(exception, 'strerror'):
            return str(exception.strerror)
        else:
            return str(exception)

    def check_response_ok(self, response, expected_codes=None):
        """
        Check if a response indicates success.

        Args:
            response: requests.Response object
            expected_codes: List of acceptable status codes (default: [200])

        Returns:
            True if response is successful

        Raises:
            HTTPResponseError: If response indicates an error
        """
        if expected_codes is None:
            expected_codes = [200]

        if response.status_code not in expected_codes:
            msg = "%s returned error %d: %s" % (
                self.client_name, response.status_code, response.reason
            )
            logger.error(msg)
            raise HTTPResponseError(msg, response.status_code, response.text)

        return True


def make_result(success, message=''):
    """
    Create a standard result tuple.

    This is the common return format for download client operations:
    (success_value, error_message) where success_value can be:
    - True/False for simple success/failure
    - A string ID on success (e.g., download ID)
    - False on failure

    Args:
        success: Success value (True, False, or an ID string)
        message: Error message if failure, empty string on success

    Returns:
        Tuple of (success_value, message)
    """
    return success, message


def result_from_exception(exception, context=''):
    """
    Create a failure result tuple from an exception.

    Args:
        exception: The exception that occurred
        context: Optional context string for the error message

    Returns:
        Tuple of (False, error_message)
    """
    if context:
        msg = "%s: %s" % (context, str(exception))
    else:
        msg = str(exception)
    return False, msg
