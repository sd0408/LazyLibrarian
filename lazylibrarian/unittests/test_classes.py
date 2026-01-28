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
Unit tests for lazylibrarian.classes module.

Tests cover:
- SearchResult class
- NZBSearchResult class
- NZBDataSearchResult class
- TorrentSearchResult class
"""

import pytest

from lazylibrarian.classes import SearchResult, NZBSearchResult, NZBDataSearchResult, TorrentSearchResult


class TestSearchResult:
    """Tests for SearchResult base class."""

    def test_searchresult_initialization(self):
        """SearchResult should initialize with default attributes."""
        result = SearchResult()
        assert hasattr(result, 'name')
        assert hasattr(result, 'url')

    def test_searchresult_name_attribute(self):
        """SearchResult should allow setting name."""
        result = SearchResult()
        result.name = 'Test Result'
        assert result.name == 'Test Result'

    def test_searchresult_url_attribute(self):
        """SearchResult should allow setting url."""
        result = SearchResult()
        result.url = 'http://example.com/download'
        assert result.url == 'http://example.com/download'


class TestNZBSearchResult:
    """Tests for NZBSearchResult class."""

    def test_nzbsearchresult_initialization(self):
        """NZBSearchResult should initialize correctly."""
        result = NZBSearchResult()
        assert result is not None

    def test_nzbsearchresult_resultType(self):
        """NZBSearchResult should have resultType 'nzb'."""
        result = NZBSearchResult()
        assert result.resultType == 'nzb'

    def test_nzbsearchresult_inherits_searchresult(self):
        """NZBSearchResult should inherit from SearchResult."""
        result = NZBSearchResult()
        assert isinstance(result, SearchResult)


class TestNZBDataSearchResult:
    """Tests for NZBDataSearchResult class."""

    def test_nzbdatasearchresult_initialization(self):
        """NZBDataSearchResult should initialize correctly."""
        result = NZBDataSearchResult()
        assert result is not None

    def test_nzbdatasearchresult_resultType(self):
        """NZBDataSearchResult should have resultType 'nzbdata'."""
        result = NZBDataSearchResult()
        assert result.resultType == 'nzbdata'

    def test_nzbdatasearchresult_inherits_searchresult(self):
        """NZBDataSearchResult should inherit from SearchResult."""
        result = NZBDataSearchResult()
        assert isinstance(result, SearchResult)


class TestTorrentSearchResult:
    """Tests for TorrentSearchResult class."""

    def test_torsearchresult_initialization(self):
        """TorrentSearchResult should initialize correctly."""
        result = TorrentSearchResult()
        assert result is not None

    def test_torsearchresult_resultType(self):
        """TorrentSearchResult should have resultType 'torrent'."""
        result = TorrentSearchResult()
        assert result.resultType == 'torrent'

    def test_torsearchresult_inherits_searchresult(self):
        """TorrentSearchResult should inherit from SearchResult."""
        result = TorrentSearchResult()
        assert isinstance(result, SearchResult)


class TestSearchResultAttributes:
    """Tests for common SearchResult attributes."""

    def test_all_result_types_have_extraInfo(self):
        """All result types should have extraInfo attribute."""
        for cls in [NZBSearchResult, NZBDataSearchResult, TorrentSearchResult]:
            result = cls()
            assert hasattr(result, 'extraInfo')

    def test_all_result_types_have_url(self):
        """All result types should have url attribute."""
        for cls in [NZBSearchResult, NZBDataSearchResult, TorrentSearchResult]:
            result = cls()
            assert hasattr(result, 'url')

    def test_all_result_types_have_provider(self):
        """All result types should have provider attribute."""
        for cls in [NZBSearchResult, NZBDataSearchResult, TorrentSearchResult]:
            result = cls()
            assert hasattr(result, 'provider')

    def test_extraInfo_is_list(self):
        """extraInfo should be initialized as empty list."""
        result = SearchResult()
        assert isinstance(result.extraInfo, list)
        assert len(result.extraInfo) == 0

    def test_extraInfo_can_store_data(self):
        """extraInfo should be able to store data."""
        result = NZBDataSearchResult()
        result.extraInfo.append(b'nzb content data')
        assert len(result.extraInfo) == 1
        assert result.extraInfo[0] == b'nzb content data'
