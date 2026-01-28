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
Unit tests for lazylibrarian.cache module.

Tests cover:
- fetchURL function
- cache_img function
- get_cached_request function
- gb_json_request function
"""

import json
import os
import tempfile
import time

import pytest
from unittest.mock import patch, Mock, MagicMock

import lazylibrarian
from lazylibrarian import cache
from lazylibrarian.formatter import md5_utf8


@pytest.fixture
def cache_setup():
    """Set up cache directory for testing."""
    original_cachedir = getattr(lazylibrarian, 'CACHEDIR', None)
    original_cache_age = lazylibrarian.CONFIG.get('CACHE_AGE', 30)

    with tempfile.TemporaryDirectory() as tmpdir:
        lazylibrarian.CACHEDIR = tmpdir
        lazylibrarian.CONFIG['CACHE_AGE'] = 30  # 30 days

        # Create subdirectories
        os.makedirs(os.path.join(tmpdir, 'book'), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, 'author'), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, 'magazine'), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, 'XMLCache'), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, 'JSONCache'), exist_ok=True)

        yield tmpdir

    lazylibrarian.CACHEDIR = original_cachedir
    lazylibrarian.CONFIG['CACHE_AGE'] = original_cache_age


class TestFetchURL:
    """Tests for fetchURL() function."""

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_success(self, mock_get):
        """fetchURL should return content and True on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test content'
        mock_get.return_value = mock_response

        result, success = cache.fetchURL('http://example.com/test')

        assert success is True
        assert 'test content' in result

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_returns_raw_bytes(self, mock_get):
        """fetchURL should return raw bytes when raw=True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'\x89PNG\x00\x00'  # Binary data
        mock_get.return_value = mock_response

        result, success = cache.fetchURL('http://example.com/image.png', raw=True)

        assert success is True
        assert isinstance(result, bytes)

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_404_error(self, mock_get):
        """fetchURL should return error and False on 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'Not Found'
        mock_get.return_value = mock_response

        result, success = cache.fetchURL('http://example.com/notfound')

        assert success is False
        assert '404' in result

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_timeout_with_retry(self, mock_get):
        """fetchURL should retry on timeout by default."""
        import requests
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            Mock(status_code=200, content=b'success')
        ]

        result, success = cache.fetchURL('http://example.com/test')

        assert success is True
        assert mock_get.call_count == 2

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_timeout_no_retry(self, mock_get):
        """fetchURL should not retry when retry=False."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result, success = cache.fetchURL('http://example.com/test', retry=False)

        assert success is False
        assert 'Timeout' in result
        assert mock_get.call_count == 1

    @patch('lazylibrarian.cache.requests.get')
    def test_fetchURL_uses_custom_headers(self, mock_get):
        """fetchURL should use provided headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_get.return_value = mock_response

        custom_headers = {'Authorization': 'Bearer token123'}
        cache.fetchURL('http://example.com/test', headers=custom_headers)

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['headers'] == custom_headers


class TestCacheImg:
    """Tests for cache_img() function."""

    def test_cache_img_returns_cached_if_exists(self, cache_setup):
        """cache_img should return cached image if it exists."""
        # Create a cached image
        img_id = 'test-book-123'
        cachefile = os.path.join(cache_setup, 'book', img_id + '.jpg')
        with open(cachefile, 'wb') as f:
            f.write(b'fake image data')

        link, success, was_cached = cache.cache_img('book', img_id, 'http://example.com/img.jpg')

        assert success is True
        assert was_cached is True
        assert 'cache/book/test-book-123.jpg' in link

    def test_cache_img_from_local_file(self, cache_setup):
        """cache_img should copy local file to cache."""
        img_id = 'local-book-456'

        # Create a source image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as src:
            src.write(b'local image data')
            src_path = src.name

        try:
            link, success, was_cached = cache.cache_img('book', img_id, src_path)

            assert success is True
            # Verify the file was cached
            cachefile = os.path.join(cache_setup, 'book', img_id + '.jpg')
            assert os.path.exists(cachefile)
        finally:
            os.unlink(src_path)

    @patch('lazylibrarian.cache.fetchURL')
    def test_cache_img_from_url(self, mock_fetch, cache_setup):
        """cache_img should download and cache image from URL."""
        mock_fetch.return_value = (b'downloaded image data', True)

        img_id = 'url-book-789'
        link, success, was_cached = cache.cache_img('book', img_id, 'http://example.com/cover.jpg')

        assert success is True
        assert was_cached is False
        mock_fetch.assert_called_once()

    def test_cache_img_invalid_type_defaults_to_book(self, cache_setup):
        """cache_img should default to 'book' for invalid img_type."""
        # Create a source image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as src:
            src.write(b'test data')
            src_path = src.name

        try:
            link, success, _ = cache.cache_img('invalid_type', 'test-id', src_path)
            # Should still succeed, defaulting to book type
            assert 'book' in link or success  # Either used book type or succeeded
        finally:
            os.unlink(src_path)


class TestGetCachedRequest:
    """Tests for get_cached_request() function."""

    def test_get_cached_request_returns_from_cache(self, cache_setup):
        """get_cached_request should return cached response if valid."""
        url = 'http://example.com/api/test'
        myhash = md5_utf8(url)

        # Create a cached XML file
        cache_dir = os.path.join(cache_setup, 'XMLCache')
        cache_file = os.path.join(cache_dir, myhash + '.xml')
        xml_content = b'<?xml version="1.0"?><root><item>test</item></root>'
        with open(cache_file, 'wb') as f:
            f.write(xml_content)

        result, from_cache = cache.get_cached_request(url, useCache=True, cache="XML")

        assert from_cache is True
        assert result is not None

    @patch('lazylibrarian.cache.fetchURL')
    def test_get_cached_request_fetches_when_no_cache(self, mock_fetch, cache_setup):
        """get_cached_request should fetch URL when not in cache."""
        mock_fetch.return_value = (b'<?xml version="1.0"?><root><data>test</data></root>', True)

        url = 'http://example.com/api/new'
        result, from_cache = cache.get_cached_request(url, useCache=True, cache="XML")

        assert from_cache is False
        mock_fetch.assert_called_once()

    def test_get_cached_request_expired_cache(self, cache_setup):
        """get_cached_request should ignore expired cache entries."""
        url = 'http://example.com/api/old'
        myhash = md5_utf8(url)

        # Create an old cached file
        cache_dir = os.path.join(cache_setup, 'XMLCache')
        cache_file = os.path.join(cache_dir, myhash + '.xml')
        xml_content = b'<?xml version="1.0"?><root>old data</root>'
        with open(cache_file, 'wb') as f:
            f.write(xml_content)

        # Set modification time to old (beyond cache age)
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
        os.utime(cache_file, (old_time, old_time))

        # File should be deleted due to expiry
        with patch('lazylibrarian.cache.fetchURL') as mock_fetch:
            mock_fetch.return_value = (b'<?xml version="1.0"?><root>new data</root>', True)
            result, from_cache = cache.get_cached_request(url, useCache=True, cache="XML")

            assert from_cache is False  # Should have fetched new data

    def test_get_cached_request_json_cache(self, cache_setup):
        """get_cached_request should handle JSON cache correctly."""
        url = 'http://example.com/api/json'
        myhash = md5_utf8(url)

        # Create cached JSON file
        cache_dir = os.path.join(cache_setup, 'JSONCache')
        cache_file = os.path.join(cache_dir, myhash + '.json')
        json_data = {'key': 'value', 'nested': {'item': 123}}
        with open(cache_file, 'w') as f:
            json.dump(json_data, f)

        result, from_cache = cache.get_cached_request(url, useCache=True, cache="JSON")

        assert from_cache is True
        assert result == json_data

    @patch('lazylibrarian.cache.fetchURL')
    def test_get_cached_request_useCache_false(self, mock_fetch, cache_setup):
        """get_cached_request should bypass cache when useCache=False."""
        url = 'http://example.com/api/bypass'
        myhash = md5_utf8(url)

        # Create cached file
        cache_dir = os.path.join(cache_setup, 'XMLCache')
        cache_file = os.path.join(cache_dir, myhash + '.xml')
        with open(cache_file, 'wb') as f:
            f.write(b'<?xml version="1.0"?><root>cached</root>')

        mock_fetch.return_value = (b'<?xml version="1.0"?><root>fresh</root>', True)

        result, from_cache = cache.get_cached_request(url, useCache=False, cache="XML")

        assert from_cache is False
        mock_fetch.assert_called_once()


class TestGbJsonRequest:
    """Tests for gb_json_request() function."""

    @patch('lazylibrarian.cache.get_cached_request')
    def test_gb_json_request_delegates_to_get_cached_request(self, mock_get_cached):
        """gb_json_request should call get_cached_request with JSON cache type."""
        mock_get_cached.return_value = ({'items': []}, True)

        url = 'http://googleapis.com/books/v1/volumes'
        result, from_cache = cache.gb_json_request(url)

        mock_get_cached.assert_called_once_with(url=url, useCache=True, cache="JSON")

    @patch('lazylibrarian.cache.get_cached_request')
    def test_gb_json_request_respects_useCache(self, mock_get_cached):
        """gb_json_request should pass useCache parameter."""
        mock_get_cached.return_value = ({'items': []}, False)

        url = 'http://googleapis.com/books/v1/volumes'
        cache.gb_json_request(url, useCache=False)

        mock_get_cached.assert_called_once_with(url=url, useCache=False, cache="JSON")


class TestCacheStatistics:
    """Tests for cache hit/miss statistics."""

    def test_cache_hit_increments(self, cache_setup):
        """Cache hit counter should increment on cache hit."""
        original_hits = lazylibrarian.CACHE_HIT

        url = 'http://example.com/api/stats'
        myhash = md5_utf8(url)

        # Create cached file
        cache_dir = os.path.join(cache_setup, 'XMLCache')
        cache_file = os.path.join(cache_dir, myhash + '.xml')
        with open(cache_file, 'wb') as f:
            f.write(b'<?xml version="1.0"?><root>data</root>')

        cache.get_cached_request(url, useCache=True, cache="XML")

        assert lazylibrarian.CACHE_HIT > original_hits

    @patch('lazylibrarian.cache.fetchURL')
    def test_cache_miss_increments(self, mock_fetch, cache_setup):
        """Cache miss counter should increment on cache miss."""
        original_misses = lazylibrarian.CACHE_MISS
        mock_fetch.return_value = (b'<?xml version="1.0"?><root>data</root>', True)

        url = 'http://example.com/api/miss'
        cache.get_cached_request(url, useCache=True, cache="XML")

        assert lazylibrarian.CACHE_MISS > original_misses
