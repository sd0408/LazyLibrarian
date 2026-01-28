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

"""Unit tests for download client base classes."""

import pytest
from unittest.mock import Mock, patch

import lazylibrarian
from lazylibrarian.clients.base import DownloadClient, NzbClient, TorrentClient


# Concrete implementations for testing abstract classes
class ConcreteDownloadClient(DownloadClient):
    """Concrete implementation for testing DownloadClient."""
    CLIENT_NAME = "TestClient"
    CONFIG_PREFIX = "TEST"

    def check_link(self):
        return "Test connection successful"


class ConcreteNzbClient(NzbClient):
    """Concrete implementation for testing NzbClient."""
    CLIENT_NAME = "TestNzbClient"
    CONFIG_PREFIX = "TESTNZB"

    def check_link(self):
        return "NZB connection successful"

    def send_nzb(self, title, nzb_url):
        return True, ''


class ConcreteTorrentClient(TorrentClient):
    """Concrete implementation for testing TorrentClient."""
    CLIENT_NAME = "TestTorrentClient"
    CONFIG_PREFIX = "TESTTOR"

    def check_link(self):
        return "Torrent connection successful"

    def add_torrent(self, link, hashid):
        return True, ''

    def get_progress(self, hashid):
        return 50, 'downloading'

    def remove_torrent(self, hashid, remove_data=False):
        return True


@pytest.fixture
def setup_test_config():
    """Setup test config values."""
    original_config = lazylibrarian.CONFIG.copy()
    lazylibrarian.CONFIG['TEST_HOST'] = 'localhost'
    lazylibrarian.CONFIG['TEST_PORT'] = '8080'
    lazylibrarian.CONFIG['TEST_USER'] = 'testuser'
    lazylibrarian.CONFIG['TEST_PASS'] = 'testpass'
    lazylibrarian.CONFIG['TEST_HTTPS'] = False
    lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
    yield
    # Restore original config
    lazylibrarian.CONFIG.clear()
    lazylibrarian.CONFIG.update(original_config)


@pytest.fixture
def setup_nzb_config():
    """Setup NZB client test config."""
    original_config = lazylibrarian.CONFIG.copy()
    lazylibrarian.CONFIG['TESTNZB_HOST'] = 'localhost'
    lazylibrarian.CONFIG['TESTNZB_PORT'] = '8080'
    lazylibrarian.CONFIG['TESTNZB_CAT'] = 'books'
    lazylibrarian.CONFIG['TESTNZB_API'] = 'abc123'
    lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
    yield
    lazylibrarian.CONFIG.clear()
    lazylibrarian.CONFIG.update(original_config)


@pytest.fixture
def setup_torrent_config():
    """Setup torrent client test config."""
    original_config = lazylibrarian.CONFIG.copy()
    lazylibrarian.CONFIG['TESTTOR_HOST'] = 'localhost'
    lazylibrarian.CONFIG['TESTTOR_PORT'] = '9091'
    lazylibrarian.CONFIG['TESTTOR_LABEL'] = 'books'
    lazylibrarian.CONFIG['TESTTOR_DIR'] = '/downloads/books'
    lazylibrarian.CONFIG['SEED_WAIT'] = True
    lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
    yield
    lazylibrarian.CONFIG.clear()
    lazylibrarian.CONFIG.update(original_config)


class TestDownloadClient:
    """Tests for DownloadClient base class."""

    def test_client_name_required(self):
        """Should raise error if CLIENT_NAME not set."""

        class NoNameClient(DownloadClient):
            CONFIG_PREFIX = "TEST"

            def check_link(self):
                pass

        with pytest.raises(NotImplementedError) as exc_info:
            NoNameClient()
        assert 'CLIENT_NAME' in str(exc_info.value)

    def test_config_prefix_required(self):
        """Should raise error if CONFIG_PREFIX not set."""

        class NoPrefixClient(DownloadClient):
            CLIENT_NAME = "Test"

            def check_link(self):
                pass

        with pytest.raises(NotImplementedError) as exc_info:
            NoPrefixClient()
        assert 'CONFIG_PREFIX' in str(exc_info.value)

    def test_get_config(self, setup_test_config):
        """Should get config value with prefix."""
        client = ConcreteDownloadClient()
        assert client.get_config('HOST') == 'localhost'
        assert client.get_config('PORT') == '8080'

    def test_get_config_default(self, setup_test_config):
        """Should return default if config key not found."""
        client = ConcreteDownloadClient()
        assert client.get_config('NONEXISTENT', 'default') == 'default'

    def test_get_config_int(self, setup_test_config):
        """Should convert config value to int."""
        client = ConcreteDownloadClient()
        assert client.get_config_int('PORT', 0) == 8080

    def test_get_config_int_invalid(self):
        """Should return default for invalid int."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TEST_HOST'] = 'localhost'
        lazylibrarian.CONFIG['TEST_PORT'] = 'invalid'
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteDownloadClient()
            assert client.get_config_int('PORT', 9999) == 9999
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_host_property(self, setup_test_config):
        """Should return configured host."""
        client = ConcreteDownloadClient()
        assert client.host == 'localhost'

    def test_port_property(self, setup_test_config):
        """Should return configured port as int."""
        client = ConcreteDownloadClient()
        assert client.port == 8080

    def test_username_property(self, setup_test_config):
        """Should return configured username."""
        client = ConcreteDownloadClient()
        assert client.username == 'testuser'

    def test_password_property(self, setup_test_config):
        """Should return configured password."""
        client = ConcreteDownloadClient()
        assert client.password == 'testpass'

    def test_base_url_property(self, setup_test_config):
        """Should build base URL from host and port."""
        client = ConcreteDownloadClient()
        assert client.base_url == 'http://localhost:8080'

    def test_base_url_with_https(self):
        """Should use https when configured."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TEST_HOST'] = 'localhost'
        lazylibrarian.CONFIG['TEST_PORT'] = '8080'
        lazylibrarian.CONFIG['TEST_HTTPS'] = True
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteDownloadClient()
            assert client.base_url == 'https://localhost:8080'
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_validate_config_success(self, setup_test_config):
        """Should validate config successfully."""
        client = ConcreteDownloadClient()
        is_valid, error = client.validate_config()
        assert is_valid is True
        assert error == ''

    def test_validate_config_missing_host(self):
        """Should fail validation without host."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TEST_HOST'] = ''
        lazylibrarian.CONFIG['TEST_PORT'] = '8080'
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteDownloadClient()
            is_valid, error = client.validate_config()
            assert is_valid is False
            assert 'host' in error.lower()
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_validate_config_missing_port(self):
        """Should fail validation without port."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TEST_HOST'] = 'localhost'
        lazylibrarian.CONFIG['TEST_PORT'] = '0'
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteDownloadClient()
            is_valid, error = client.validate_config()
            assert is_valid is False
            assert 'port' in error.lower()
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_check_link_abstract(self, setup_test_config):
        """check_link should be implemented in subclass."""
        client = ConcreteDownloadClient()
        assert client.check_link() == "Test connection successful"


class TestNzbClient:
    """Tests for NzbClient base class."""

    def test_category_property(self, setup_nzb_config):
        """Should return configured category."""
        client = ConcreteNzbClient()
        assert client.category == 'books'

    def test_api_key_property(self, setup_nzb_config):
        """Should return configured API key."""
        client = ConcreteNzbClient()
        assert client.api_key == 'abc123'

    def test_api_key_fallback(self):
        """Should fall back to APIKEY if API not found."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TESTNZB_HOST'] = 'localhost'
        lazylibrarian.CONFIG['TESTNZB_PORT'] = '8080'
        lazylibrarian.CONFIG['TESTNZB_APIKEY'] = 'fallback123'
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteNzbClient()
            assert client.api_key == 'fallback123'
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_get_queue_default(self, setup_nzb_config):
        """get_queue should return None by default."""
        client = ConcreteNzbClient()
        assert client.get_queue() is None

    def test_get_history_default(self, setup_nzb_config):
        """get_history should return None by default."""
        client = ConcreteNzbClient()
        assert client.get_history() is None

    def test_delete_download_default(self, setup_nzb_config):
        """delete_download should return failure by default."""
        client = ConcreteNzbClient()
        success, msg = client.delete_download('id123')
        assert success is False
        assert 'not supported' in msg.lower()


class TestTorrentClient:
    """Tests for TorrentClient base class."""

    def test_label_property(self, setup_torrent_config):
        """Should return configured label."""
        client = ConcreteTorrentClient()
        assert client.label == 'books'

    def test_label_fallback_to_cat(self):
        """Should fall back to CAT if LABEL not found."""
        original = lazylibrarian.CONFIG.copy()
        lazylibrarian.CONFIG['TESTTOR_HOST'] = 'localhost'
        lazylibrarian.CONFIG['TESTTOR_PORT'] = '9091'
        lazylibrarian.CONFIG['TESTTOR_CAT'] = 'category'
        lazylibrarian.CONFIG['HTTP_TIMEOUT'] = 30
        try:
            client = ConcreteTorrentClient()
            assert client.label == 'category'
        finally:
            lazylibrarian.CONFIG.clear()
            lazylibrarian.CONFIG.update(original)

    def test_download_dir_property(self, setup_torrent_config):
        """Should return configured download directory."""
        client = ConcreteTorrentClient()
        assert client.download_dir == '/downloads/books'

    def test_add_torrent_file_default(self, setup_torrent_config):
        """add_torrent_file should return failure by default."""
        client = ConcreteTorrentClient()
        success, msg = client.add_torrent_file(b'data', 'hash', 'title')
        assert success is False
        assert 'not supported' in msg.lower()

    def test_get_name_default(self, setup_torrent_config):
        """get_name should return empty string by default."""
        client = ConcreteTorrentClient()
        assert client.get_name('hash') == ''

    def test_get_folder_default(self, setup_torrent_config):
        """get_folder should return None by default."""
        client = ConcreteTorrentClient()
        assert client.get_folder('hash') is None

    def test_get_files_default(self, setup_torrent_config):
        """get_files should return empty string by default."""
        client = ConcreteTorrentClient()
        assert client.get_files('hash') == ''

    def test_should_wait_for_seeding(self, setup_torrent_config):
        """should_wait_for_seeding should check SEED_WAIT config."""
        client = ConcreteTorrentClient()
        assert client.should_wait_for_seeding() is True

    def test_is_seeding_uploading(self, setup_torrent_config):
        """is_seeding should detect uploading state."""
        client = ConcreteTorrentClient()
        assert client.is_seeding('uploading') is True
        assert client.is_seeding('Uploading') is True

    def test_is_seeding_stalledup(self, setup_torrent_config):
        """is_seeding should detect stalledUP state."""
        client = ConcreteTorrentClient()
        assert client.is_seeding('stalledUP') is True
        assert client.is_seeding('stalledup') is True

    def test_is_seeding_seeding(self, setup_torrent_config):
        """is_seeding should detect seeding state."""
        client = ConcreteTorrentClient()
        assert client.is_seeding('seeding') is True
        assert client.is_seeding('Seeding') is True

    def test_is_seeding_downloading(self, setup_torrent_config):
        """is_seeding should return False for downloading."""
        client = ConcreteTorrentClient()
        assert client.is_seeding('downloading') is False
        assert client.is_seeding('paused') is False
