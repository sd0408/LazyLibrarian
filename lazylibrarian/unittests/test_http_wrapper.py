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

"""Unit tests for HTTP client wrapper."""

import pytest
from unittest.mock import Mock, patch
import requests as requests_lib

import lazylibrarian
from lazylibrarian.clients.http_wrapper import (
    HTTPClientWrapper, HTTPClientError, HTTPTimeoutError,
    HTTPConnectionError, HTTPResponseError, make_result, result_from_exception
)


@pytest.fixture
def setup_http_config():
    """Setup HTTP config for tests."""
    original = lazylibrarian.CONFIG.copy()
    original_loglevel = lazylibrarian.LOGLEVEL
    original_log_dlcomms = lazylibrarian.log_dlcomms
    lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
    lazylibrarian.LOGLEVEL = 0
    lazylibrarian.log_dlcomms = 0
    yield
    lazylibrarian.CONFIG.clear()
    lazylibrarian.CONFIG.update(original)
    lazylibrarian.LOGLEVEL = original_loglevel
    lazylibrarian.log_dlcomms = original_log_dlcomms


class TestHTTPClientWrapper:
    """Tests for HTTPClientWrapper class."""

    def test_initialization(self, setup_http_config):
        """Should initialize with client name and timeout."""
        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        assert wrapper.client_name == 'TestClient'
        assert wrapper.timeout == 10
        assert wrapper.verify_ssl is True

    def test_initialization_defaults(self, setup_http_config):
        """Should use default timeout from config."""
        wrapper = HTTPClientWrapper('TestClient')
        assert wrapper.timeout == 30  # from mock_config

    @patch('lazylibrarian.clients.http_wrapper.requests.get')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_get_success(self, mock_proxies, mock_get, setup_http_config):
        """GET request should return response."""
        mock_proxies.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        response = wrapper.get('http://localhost/api')

        assert response == mock_response
        mock_get.assert_called_once()

    @patch('lazylibrarian.clients.http_wrapper.requests.get')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_get_timeout_raises_error(self, mock_proxies, mock_get, setup_http_config):
        """GET timeout should raise HTTPTimeoutError."""
        mock_proxies.return_value = None
        mock_get.side_effect = requests_lib.exceptions.Timeout()

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        with pytest.raises(HTTPTimeoutError) as exc_info:
            wrapper.get('http://localhost/api')

        assert 'Timeout' in str(exc_info.value)
        assert 'TestClient' in str(exc_info.value)

    @patch('lazylibrarian.clients.http_wrapper.requests.get')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_get_connection_error_raises_error(self, mock_proxies, mock_get, setup_http_config):
        """GET connection error should raise HTTPConnectionError."""
        mock_proxies.return_value = None
        mock_get.side_effect = requests_lib.exceptions.ConnectionError('Connection refused')

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        with pytest.raises(HTTPConnectionError) as exc_info:
            wrapper.get('http://localhost/api')

        assert 'Unable to connect' in str(exc_info.value)

    @patch('lazylibrarian.clients.http_wrapper.requests.post')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_post_success(self, mock_proxies, mock_post, setup_http_config):
        """POST request should return response."""
        mock_proxies.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        response = wrapper.post('http://localhost/api', data={'key': 'value'})

        assert response == mock_response
        mock_post.assert_called_once()

    @patch('lazylibrarian.clients.http_wrapper.requests.get')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_get_json_success(self, mock_proxies, mock_get, setup_http_config):
        """get_json should parse JSON response."""
        mock_proxies.return_value = None
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        result = wrapper.get_json('http://localhost/api')

        assert result == {'status': 'ok'}

    @patch('lazylibrarian.clients.http_wrapper.requests.get')
    @patch('lazylibrarian.clients.http_wrapper.proxyList')
    def test_get_json_invalid_json_raises_error(self, mock_proxies, mock_get, setup_http_config):
        """get_json should raise HTTPResponseError on invalid JSON."""
        mock_proxies.return_value = None
        mock_response = Mock()
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_response.status_code = 200
        mock_response.text = 'not json'
        mock_get.return_value = mock_response

        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        with pytest.raises(HTTPResponseError) as exc_info:
            wrapper.get_json('http://localhost/api')

        assert 'invalid JSON' in str(exc_info.value)

    def test_check_response_ok_success(self, setup_http_config):
        """check_response_ok should return True for 200."""
        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        mock_response = Mock()
        mock_response.status_code = 200

        assert wrapper.check_response_ok(mock_response) is True

    def test_check_response_ok_failure(self, setup_http_config):
        """check_response_ok should raise HTTPResponseError for non-200."""
        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason = 'Unauthorized'
        mock_response.text = 'Auth failed'

        with pytest.raises(HTTPResponseError) as exc_info:
            wrapper.check_response_ok(mock_response)

        assert exc_info.value.status_code == 401

    def test_check_response_ok_custom_codes(self, setup_http_config):
        """check_response_ok should accept custom expected codes."""
        wrapper = HTTPClientWrapper('TestClient', timeout=10)
        mock_response = Mock()
        mock_response.status_code = 201

        assert wrapper.check_response_ok(mock_response, expected_codes=[200, 201]) is True


class TestExtractErrorMessage:
    """Tests for _extract_error_message static method."""

    def test_extracts_reason_attribute(self):
        """Should extract error from 'reason' attribute."""

        class ErrorWithReason:
            reason = "Connection refused"

        msg = HTTPClientWrapper._extract_error_message(ErrorWithReason())
        assert msg == "Connection refused"

    def test_extracts_strerror_attribute(self):
        """Should extract error from 'strerror' attribute."""

        class ErrorWithStrerror:
            strerror = "No such file"

        msg = HTTPClientWrapper._extract_error_message(ErrorWithStrerror())
        assert msg == "No such file"

    def test_falls_back_to_str(self):
        """Should fall back to str() if no specific attribute."""
        error = Exception("Generic error")
        msg = HTTPClientWrapper._extract_error_message(error)
        assert msg == "Generic error"


class TestMakeResult:
    """Tests for make_result helper function."""

    def test_success_result(self):
        """Should create success tuple."""
        result = make_result(True)
        assert result == (True, '')

    def test_success_with_id(self):
        """Should create success tuple with ID."""
        result = make_result('download-123')
        assert result == ('download-123', '')

    def test_failure_result(self):
        """Should create failure tuple."""
        result = make_result(False, 'Error message')
        assert result == (False, 'Error message')


class TestResultFromException:
    """Tests for result_from_exception helper function."""

    def test_creates_failure_tuple(self):
        """Should create failure tuple from exception."""
        exc = Exception("Something went wrong")
        result = result_from_exception(exc)
        assert result == (False, "Something went wrong")

    def test_includes_context(self):
        """Should include context in error message."""
        exc = Exception("Connection failed")
        result = result_from_exception(exc, "SABnzbd")
        assert result == (False, "SABnzbd: Connection failed")


class TestHTTPExceptions:
    """Tests for HTTP exception classes."""

    def test_http_client_error(self):
        """HTTPClientError should be an Exception."""
        error = HTTPClientError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_http_timeout_error(self):
        """HTTPTimeoutError should be an HTTPClientError."""
        error = HTTPTimeoutError("Timeout")
        assert isinstance(error, HTTPClientError)

    def test_http_connection_error(self):
        """HTTPConnectionError should be an HTTPClientError."""
        error = HTTPConnectionError("Connection failed")
        assert isinstance(error, HTTPClientError)

    def test_http_response_error_with_status(self):
        """HTTPResponseError should store status code and body."""
        error = HTTPResponseError("Bad response", status_code=400, response_body="error body")
        assert error.status_code == 400
        assert error.response_body == "error body"
        assert str(error) == "Bad response"
