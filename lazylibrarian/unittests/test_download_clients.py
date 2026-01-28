#  This file is part of Lazylibrarian.
#
#  Lazylibrarian is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

"""
Unit tests for download client modules (sabnzbd, nzbget).

Tests cover:
- Connection testing (checkLink)
- NZB sending functions
- Error handling
- Configuration validation
"""

import pytest
from unittest.mock import patch, Mock, MagicMock

import lazylibrarian
from lazylibrarian import sabnzbd, nzbget
from lazylibrarian.classes import NZBSearchResult, NZBDataSearchResult


@pytest.fixture
def sab_config():
    """Set up SABnzbd configuration for testing."""
    original_config = dict(lazylibrarian.CONFIG)

    lazylibrarian.CONFIG['SAB_HOST'] = 'localhost'
    lazylibrarian.CONFIG['SAB_PORT'] = '8080'
    lazylibrarian.CONFIG['SAB_API'] = 'test-api-key-12345'
    lazylibrarian.CONFIG['SAB_USER'] = ''
    lazylibrarian.CONFIG['SAB_PASS'] = ''
    lazylibrarian.CONFIG['SAB_CAT'] = 'books'
    lazylibrarian.CONFIG['SAB_SUBDIR'] = ''
    lazylibrarian.CONFIG['HTTP_TIMEOUT'] = '30'
    lazylibrarian.CONFIG['USENET_RETENTION'] = ''
    lazylibrarian.LOGLEVEL = 0

    yield

    lazylibrarian.CONFIG.update(original_config)


@pytest.fixture
def nzbget_config():
    """Set up NZBget configuration for testing."""
    original_config = dict(lazylibrarian.CONFIG)

    lazylibrarian.CONFIG['NZBGET_HOST'] = 'localhost'
    lazylibrarian.CONFIG['NZBGET_PORT'] = '6789'
    lazylibrarian.CONFIG['NZBGET_USER'] = 'nzbget'
    lazylibrarian.CONFIG['NZBGET_PASS'] = 'tegbzn6789'
    lazylibrarian.CONFIG['NZBGET_CATEGORY'] = 'books'
    lazylibrarian.CONFIG['NZBGET_PRIORITY'] = '0'
    lazylibrarian.LOGLEVEL = 0

    yield

    lazylibrarian.CONFIG.update(original_config)


class TestSABnzbdCheckLink:
    """Tests for SABnzbd checkLink() function."""

    @patch('lazylibrarian.sabnzbd.SABnzbd')
    def test_checkLink_success(self, mock_sab, sab_config):
        """checkLink should return success message when connection works."""
        # First call for auth check
        mock_sab.side_effect = [
            ({'auth': 'apikey'}, ''),  # auth check
            ({'categories': ['books', 'movies']}, ''),  # get_cats check
        ]

        result = sabnzbd.checkLink()
        assert 'successful' in result.lower()

    @patch('lazylibrarian.sabnzbd.SABnzbd')
    def test_checkLink_auth_failure(self, mock_sab, sab_config):
        """checkLink should return error when auth fails."""
        mock_sab.return_value = (False, 'Connection refused')

        result = sabnzbd.checkLink()
        assert 'HOST' in result or 'PORT' in result or 'Unable' in result

    @patch('lazylibrarian.sabnzbd.SABnzbd')
    def test_checkLink_api_failure(self, mock_sab, sab_config):
        """checkLink should return error when API key is invalid."""
        mock_sab.side_effect = [
            ({'auth': 'apikey'}, ''),  # auth OK
            (False, 'Invalid API key'),  # get_cats fails
        ]

        result = sabnzbd.checkLink()
        assert 'APIKEY' in result or 'Unable' in result

    @patch('lazylibrarian.sabnzbd.SABnzbd')
    def test_checkLink_invalid_category(self, mock_sab, sab_config):
        """checkLink should return error for unknown category."""
        lazylibrarian.CONFIG['SAB_CAT'] = 'nonexistent'
        mock_sab.side_effect = [
            ({'auth': 'apikey'}, ''),
            ({'categories': ['books', 'movies']}, ''),
        ]

        result = sabnzbd.checkLink()
        assert 'Unknown category' in result or 'nonexistent' in result


class TestSABnzbdFunction:
    """Tests for SABnzbd() main function."""

    def test_SABnzbd_invalid_host(self, sab_config):
        """SABnzbd should return error for invalid host configuration."""
        lazylibrarian.CONFIG['SAB_HOST'] = ''

        result, msg = sabnzbd.SABnzbd(title='Test', nzburl='http://example.com/test.nzb')

        assert result is False
        assert 'Invalid' in msg

    def test_SABnzbd_invalid_port(self, sab_config):
        """SABnzbd should return error for invalid port configuration."""
        lazylibrarian.CONFIG['SAB_PORT'] = 'notaport'

        result, msg = sabnzbd.SABnzbd(title='Test', nzburl='http://example.com/test.nzb')

        assert result is False
        assert 'Invalid' in msg

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_add_nzb_success(self, mock_get, sab_config):
        """SABnzbd should successfully add NZB to queue."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': True,
            'nzo_ids': ['SABnzbd_nzo_abc123']
        }
        mock_get.return_value = mock_response

        result, msg = sabnzbd.SABnzbd(
            title='Test Book',
            nzburl='http://example.com/test.nzb'
        )

        assert result == 'SABnzbd_nzo_abc123'
        assert msg == ''

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_add_nzb_error(self, mock_get, sab_config):
        """SABnzbd should handle error response from SAB."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': False,
            'error': 'NZB could not be added'
        }
        mock_get.return_value = mock_response

        result, msg = sabnzbd.SABnzbd(
            title='Test Book',
            nzburl='http://example.com/test.nzb'
        )

        assert result is False
        assert 'Error' in msg

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_timeout(self, mock_get, sab_config):
        """SABnzbd should handle connection timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result, msg = sabnzbd.SABnzbd(
            title='Test Book',
            nzburl='http://example.com/test.nzb'
        )

        assert result is False
        assert 'Timeout' in msg

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_queue_request(self, mock_get, sab_config):
        """SABnzbd should handle queue status request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'queue': {'slots': [], 'status': 'Idle'}
        }
        mock_get.return_value = mock_response

        result, msg = sabnzbd.SABnzbd(nzburl='queue')

        assert result is not None
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert 'mode=queue' in call_url

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_history_request(self, mock_get, sab_config):
        """SABnzbd should handle history status request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'history': {'slots': []}
        }
        mock_get.return_value = mock_response

        result, msg = sabnzbd.SABnzbd(nzburl='history')

        assert result is not None
        call_url = mock_get.call_args[0][0]
        assert 'mode=history' in call_url

    def test_SABnzbd_delete_unknown_id(self, sab_config):
        """SABnzbd should reject delete with unknown ID."""
        result, msg = sabnzbd.SABnzbd(title='unknown', nzburl='delete')

        assert result is False
        assert 'unavailable' in msg.lower()

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_url_construction(self, mock_get, sab_config):
        """SABnzbd should construct URL correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': True, 'nzo_ids': ['id123']}
        mock_get.return_value = mock_response

        sabnzbd.SABnzbd(title='Test', nzburl='http://test.nzb')

        call_url = mock_get.call_args[0][0]
        assert 'localhost:8080' in call_url
        assert 'apikey=' in call_url
        assert 'mode=addurl' in call_url

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_with_subdir(self, mock_get, sab_config):
        """SABnzbd should include subdir in URL when configured."""
        lazylibrarian.CONFIG['SAB_SUBDIR'] = 'sabnzbd'
        mock_response = Mock()
        mock_response.json.return_value = {'status': True, 'nzo_ids': ['id123']}
        mock_get.return_value = mock_response

        sabnzbd.SABnzbd(title='Test', nzburl='http://test.nzb')

        call_url = mock_get.call_args[0][0]
        assert '/sabnzbd/' in call_url

    @patch('lazylibrarian.sabnzbd.requests.get')
    def test_SABnzbd_with_https(self, mock_get, sab_config):
        """SABnzbd should handle HTTPS host."""
        lazylibrarian.CONFIG['SAB_HOST'] = 'https://localhost'
        mock_response = Mock()
        mock_response.json.return_value = {'status': True, 'nzo_ids': ['id123']}
        mock_get.return_value = mock_response

        sabnzbd.SABnzbd(title='Test', nzburl='http://test.nzb')

        call_url = mock_get.call_args[0][0]
        assert call_url.startswith('https://')


class TestNZBgetCheckLink:
    """Tests for NZBget checkLink() function."""

    @patch('lazylibrarian.nzbget.sendNZB')
    def test_checkLink_success(self, mock_send, nzbget_config):
        """checkLink should return success when connection works."""
        mock_send.return_value = True

        result = nzbget.checkLink()
        assert 'successful' in result.lower()

    @patch('lazylibrarian.nzbget.sendNZB')
    def test_checkLink_failure(self, mock_send, nzbget_config):
        """checkLink should return failure message on connection error."""
        mock_send.return_value = False

        result = nzbget.checkLink()
        assert 'FAILED' in result


class TestNZBgetSendNZB:
    """Tests for NZBget sendNZB() function."""

    def test_sendNZB_invalid_host(self, nzbget_config):
        """sendNZB should return error for invalid host."""
        lazylibrarian.CONFIG['NZBGET_HOST'] = ''

        result, msg = nzbget.sendNZB(cmd='test')

        assert result is False
        assert 'Invalid' in msg

    def test_sendNZB_invalid_port(self, nzbget_config):
        """sendNZB should return error for invalid port."""
        lazylibrarian.CONFIG['NZBGET_PORT'] = 'notaport'

        result, msg = nzbget.sendNZB(cmd='test')

        assert result is False
        assert 'Invalid' in msg

    @patch('lazylibrarian.nzbget.xmlrpc_client.ServerProxy')
    def test_sendNZB_test_command(self, mock_proxy_class, nzbget_config):
        """sendNZB should handle test command."""
        mock_proxy = MagicMock()
        mock_proxy.writelog.return_value = True
        mock_proxy_class.return_value = mock_proxy

        result, msg = nzbget.sendNZB(cmd='test')

        assert result is True
        mock_proxy.writelog.assert_called_once()

    @patch('lazylibrarian.nzbget.xmlrpc_client.ServerProxy')
    def test_sendNZB_connection_error(self, mock_proxy_class, nzbget_config):
        """sendNZB should handle connection errors."""
        mock_proxy_class.side_effect = Exception("Connection refused")

        result, msg = nzbget.sendNZB(cmd='test')

        assert result is False
        assert 'failed' in msg.lower()

    @patch('lazylibrarian.nzbget.xmlrpc_client.ServerProxy')
    def test_sendNZB_unauthorized(self, mock_proxy_class, nzbget_config):
        """sendNZB should handle unauthorized error."""
        import xmlrpc.client as xmlrpc_client

        mock_proxy = MagicMock()
        mock_proxy.writelog.side_effect = xmlrpc_client.ProtocolError(
            'localhost', 401, 'Unauthorized', {}
        )
        mock_proxy_class.return_value = mock_proxy

        result, msg = nzbget.sendNZB(cmd='test')

        assert result is False
        assert 'password' in msg.lower() or 'Unauthorized' in msg

    @patch('lazylibrarian.nzbget.xmlrpc_client.ServerProxy')
    def test_sendNZB_add_nzb_v13(self, mock_proxy_class, nzbget_config):
        """sendNZB should send NZB using v13+ API."""
        mock_proxy = MagicMock()
        mock_proxy.writelog.return_value = True
        mock_proxy.version.return_value = "21.0"
        mock_proxy.append.return_value = 12345  # NZBID
        mock_proxy_class.return_value = mock_proxy

        nzb = NZBSearchResult()
        nzb.name = 'Test Book'
        nzb.url = 'http://example.com/test.nzb'
        nzb.resultType = 'nzb'

        result, msg = nzbget.sendNZB(nzb=nzb)

        assert result == 12345
        mock_proxy.append.assert_called_once()

    @patch('lazylibrarian.nzbget.xmlrpc_client.ServerProxy')
    def test_sendNZB_add_nzb_with_data(self, mock_proxy_class, nzbget_config):
        """sendNZB should send NZB data content."""
        mock_proxy = MagicMock()
        mock_proxy.writelog.return_value = True
        mock_proxy.version.return_value = "21.0"
        mock_proxy.append.return_value = 12345
        mock_proxy_class.return_value = mock_proxy

        nzb = NZBDataSearchResult()
        nzb.name = 'Test Book'
        nzb.extraInfo = [b'<?xml version="1.0"?><nzb>...</nzb>']
        nzb.resultType = 'nzbdata'

        result, msg = nzbget.sendNZB(nzb=nzb)

        assert result == 12345


class TestNZBgetDeleteNZB:
    """Tests for NZBget deleteNZB() function."""

    @patch('lazylibrarian.nzbget.sendNZB')
    def test_deleteNZB_without_data(self, mock_send, nzbget_config):
        """deleteNZB should call delete commands without removing data."""
        mock_send.return_value = (True, '')

        nzbget.deleteNZB('12345', remove_data=False)

        # Should be called twice: GroupDelete and HistoryDelete
        assert mock_send.call_count == 2

        calls = mock_send.call_args_list
        commands = [call[1]['cmd'] for call in calls]
        assert 'GroupDelete' in commands
        assert 'HistoryDelete' in commands

    @patch('lazylibrarian.nzbget.sendNZB')
    def test_deleteNZB_with_data(self, mock_send, nzbget_config):
        """deleteNZB should call final delete commands to remove data."""
        mock_send.return_value = (True, '')

        nzbget.deleteNZB('12345', remove_data=True)

        calls = mock_send.call_args_list
        commands = [call[1]['cmd'] for call in calls]
        assert 'GroupFinalDelete' in commands
        assert 'HistoryFinalDelete' in commands


class TestSearchResultClasses:
    """Tests for SearchResult classes."""

    def test_NZBSearchResult_has_correct_type(self):
        """NZBSearchResult should have resultType 'nzb'."""
        result = NZBSearchResult()
        assert result.resultType == 'nzb'

    def test_NZBDataSearchResult_has_correct_type(self):
        """NZBDataSearchResult should have resultType 'nzbdata'."""
        result = NZBDataSearchResult()
        assert result.resultType == 'nzbdata'

    def test_SearchResult_initialization(self):
        """SearchResult should initialize with empty values."""
        result = NZBSearchResult()
        assert result.provider == ""
        assert result.url == ""
        assert result.name == ""
        assert result.extraInfo == []

    def test_SearchResult_can_store_data(self):
        """SearchResult should store data correctly."""
        result = NZBSearchResult()
        result.name = "Test Book"
        result.url = "http://example.com/test.nzb"
        result.extraInfo = ['extra1', 'extra2']

        assert result.name == "Test Book"
        assert result.url == "http://example.com/test.nzb"
        assert len(result.extraInfo) == 2
