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

"""Unit tests for URL builder utility."""

import pytest
from bookbagofholding.utils.url_builder import URLBuilder


class TestNormalizeHost:
    """Tests for URLBuilder.normalize_host()"""

    def test_empty_hostname_returns_empty_string(self):
        """Empty hostname should return empty string"""
        assert URLBuilder.normalize_host('') == ''
        assert URLBuilder.normalize_host(None) == ''

    def test_adds_http_protocol_by_default(self):
        """Should add http:// if no protocol specified"""
        result = URLBuilder.normalize_host('localhost')
        assert result == 'http://localhost'

    def test_adds_https_protocol_when_requested(self):
        """Should add https:// when use_https=True"""
        result = URLBuilder.normalize_host('localhost', use_https=True)
        assert result == 'https://localhost'

    def test_preserves_existing_https(self):
        """Should preserve https:// if already present"""
        result = URLBuilder.normalize_host('https://localhost')
        assert result == 'https://localhost'

    def test_preserves_existing_http(self):
        """Should preserve http:// if already present (even if use_https=True for base)"""
        result = URLBuilder.normalize_host('http://localhost')
        assert result == 'http://localhost'

    def test_removes_trailing_slash(self):
        """Should remove trailing slashes"""
        result = URLBuilder.normalize_host('localhost/')
        assert result == 'http://localhost'
        result = URLBuilder.normalize_host('localhost///')
        assert result == 'http://localhost'

    def test_removes_gui_suffix(self):
        """Should remove /gui suffix (common in torrent clients)"""
        result = URLBuilder.normalize_host('localhost/gui')
        assert result == 'http://localhost'

    def test_appends_port_number(self):
        """Should append port number if provided"""
        result = URLBuilder.normalize_host('localhost', port=8080)
        assert result == 'http://localhost:8080'

    def test_appends_port_as_string(self):
        """Should handle port as string"""
        result = URLBuilder.normalize_host('localhost', port='8080')
        assert result == 'http://localhost:8080'

    def test_ignores_invalid_port(self):
        """Should ignore zero or negative ports"""
        result = URLBuilder.normalize_host('localhost', port=0)
        assert result == 'http://localhost'
        result = URLBuilder.normalize_host('localhost', port=-1)
        assert result == 'http://localhost'

    def test_ignores_non_numeric_port(self):
        """Should ignore non-numeric port values"""
        result = URLBuilder.normalize_host('localhost', port='invalid')
        assert result == 'http://localhost'

    def test_strips_whitespace(self):
        """Should strip whitespace from hostname"""
        result = URLBuilder.normalize_host('  localhost  ')
        assert result == 'http://localhost'

    def test_full_example(self):
        """Test complete URL building"""
        result = URLBuilder.normalize_host('192.168.1.100/', port=9091, use_https=True)
        assert result == 'https://192.168.1.100:9091'


class TestAppendPath:
    """Tests for URLBuilder.append_path()"""

    def test_empty_base_returns_empty(self):
        """Empty base URL should return empty string"""
        assert URLBuilder.append_path('', '/api') == ''

    def test_empty_path_returns_base(self):
        """Empty path should return base URL unchanged"""
        assert URLBuilder.append_path('http://localhost', '') == 'http://localhost'
        assert URLBuilder.append_path('http://localhost', None) == 'http://localhost'

    def test_appends_path_correctly(self):
        """Should append path with single slash"""
        result = URLBuilder.append_path('http://localhost', 'api')
        assert result == 'http://localhost/api'

    def test_handles_leading_slash_in_path(self):
        """Should handle leading slash in path"""
        result = URLBuilder.append_path('http://localhost', '/api')
        assert result == 'http://localhost/api'

    def test_handles_trailing_slash_in_base(self):
        """Should handle trailing slash in base URL"""
        result = URLBuilder.append_path('http://localhost/', 'api')
        assert result == 'http://localhost/api'

    def test_handles_both_slashes(self):
        """Should handle slashes in both base and path"""
        result = URLBuilder.append_path('http://localhost/', '/api/')
        assert result == 'http://localhost/api'


class TestBuildApiUrl:
    """Tests for URLBuilder.build_api_url()"""

    def test_builds_url_without_params(self):
        """Should build URL without query params"""
        result = URLBuilder.build_api_url('http://localhost', 'api')
        assert result == 'http://localhost/api'

    def test_builds_url_with_params(self):
        """Should build URL with query params"""
        result = URLBuilder.build_api_url('http://localhost', 'api', {'key': 'value'})
        assert result == 'http://localhost/api?key=value'

    def test_filters_none_values(self):
        """Should filter out None values from params"""
        result = URLBuilder.build_api_url('http://localhost', 'api',
                                          {'key1': 'value1', 'key2': None})
        assert result == 'http://localhost/api?key1=value1'

    def test_empty_params_no_query_string(self):
        """Empty params dict should not add query string"""
        result = URLBuilder.build_api_url('http://localhost', 'api', {})
        assert result == 'http://localhost/api'


class TestExtractHostPort:
    """Tests for URLBuilder.extract_host_port()"""

    def test_empty_url_returns_none(self):
        """Empty URL should return (None, None)"""
        assert URLBuilder.extract_host_port('') == (None, None)
        assert URLBuilder.extract_host_port(None) == (None, None)

    def test_extracts_host_without_port(self):
        """Should extract host when no port specified"""
        host, port = URLBuilder.extract_host_port('http://localhost')
        assert host == 'localhost'
        assert port is None

    def test_extracts_host_and_port(self):
        """Should extract both host and port"""
        host, port = URLBuilder.extract_host_port('http://localhost:8080')
        assert host == 'localhost'
        assert port == 8080

    def test_handles_missing_protocol(self):
        """Should handle URL without protocol"""
        host, port = URLBuilder.extract_host_port('localhost:8080')
        assert host == 'localhost'
        assert port == 8080


class TestIsHttps:
    """Tests for URLBuilder.is_https()"""

    def test_empty_url_returns_false(self):
        """Empty URL should return False"""
        assert URLBuilder.is_https('') is False
        assert URLBuilder.is_https(None) is False

    def test_http_url_returns_false(self):
        """HTTP URL should return False"""
        assert URLBuilder.is_https('http://localhost') is False

    def test_https_url_returns_true(self):
        """HTTPS URL should return True"""
        assert URLBuilder.is_https('https://localhost') is True

    def test_case_insensitive(self):
        """Should be case insensitive"""
        assert URLBuilder.is_https('HTTPS://localhost') is True
        assert URLBuilder.is_https('Https://localhost') is True
