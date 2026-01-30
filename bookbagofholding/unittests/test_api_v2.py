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
Unit tests for bookbagofholding.api_v2 module.

Tests cover:
- ApiBase class and utility methods
- api_endpoint and require_param decorators
- AuthorApi endpoints
- BookApi endpoints
- SystemApi endpoints
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestApiEndpointDecorator:
    """Tests for the api_endpoint decorator."""

    def test_api_endpoint_sets_metadata(self):
        """api_endpoint should set metadata on decorated function."""
        from bookbagofholding.api_v2.base import api_endpoint

        @api_endpoint("Test description", ["&id= test ID"])
        def test_func():
            pass

        assert test_func._api_endpoint is True
        assert test_func._api_description == "Test description"
        assert test_func._api_params == ["&id= test ID"]

    def test_api_endpoint_default_params(self):
        """api_endpoint should use empty list when no params specified."""
        from bookbagofholding.api_v2.base import api_endpoint

        @api_endpoint("Test description")
        def test_func():
            pass

        assert test_func._api_params == []


class TestRequireParamDecorator:
    """Tests for the require_param decorator."""

    def test_require_param_passes_when_present(self):
        """require_param should allow call when params are present."""
        from bookbagofholding.api_v2.base import require_param, ApiBase

        class TestApi(ApiBase):
            @require_param('id')
            def test_method(self, **kwargs):
                return self.success(data=kwargs['id'])

        api = TestApi()
        result = api.test_method(id='test123')
        assert result['success'] is True
        assert result['data'] == 'test123'

    def test_require_param_rejects_missing_param(self):
        """require_param should return error when param is missing."""
        from bookbagofholding.api_v2.base import require_param, ApiBase

        class TestApi(ApiBase):
            @require_param('id')
            def test_method(self, **kwargs):
                return self.success()

        api = TestApi()
        result = api.test_method()
        assert result['success'] is False
        assert 'id' in result['error']

    def test_require_param_rejects_empty_param(self):
        """require_param should reject empty string values."""
        from bookbagofholding.api_v2.base import require_param, ApiBase

        class TestApi(ApiBase):
            @require_param('id')
            def test_method(self, **kwargs):
                return self.success()

        api = TestApi()
        result = api.test_method(id='')
        assert result['success'] is False

    def test_require_param_multiple_params(self):
        """require_param should validate multiple params."""
        from bookbagofholding.api_v2.base import require_param, ApiBase

        class TestApi(ApiBase):
            @require_param('id', 'name')
            def test_method(self, **kwargs):
                return self.success()

        api = TestApi()
        result = api.test_method(id='123')
        assert result['success'] is False
        assert 'name' in result['error']

    def test_require_param_preserves_function_name(self):
        """require_param should preserve original function name."""
        from bookbagofholding.api_v2.base import require_param, ApiBase

        class TestApi(ApiBase):
            @require_param('id')
            def test_method(self, **kwargs):
                return self.success()

        api = TestApi()
        assert api.test_method.__name__ == 'test_method'


class TestApiBaseClass:
    """Tests for the ApiBase class."""

    def test_success_returns_correct_format(self):
        """success() should return properly formatted response."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.success(data={'test': 'value'}, message="Custom message")
        assert result['success'] is True
        assert result['message'] == "Custom message"
        assert result['data'] == {'test': 'value'}

    def test_success_without_data(self):
        """success() should work without data."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.success()
        assert result['success'] is True
        assert 'data' not in result

    def test_error_returns_correct_format(self):
        """error() should return properly formatted response."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.error("Test error", code=404)
        assert result['success'] is False
        assert result['error'] == "Test error"
        assert result['code'] == 404

    def test_error_default_code(self):
        """error() should use 400 as default code."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.error("Test error")
        assert result['code'] == 400

    def test_rows_to_dicts_converts_rows(self):
        """rows_to_dicts should convert row objects to dictionaries."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()

        # Use a mock that behaves like a sqlite Row (supports dict() conversion)
        class MockRow(dict):
            def __init__(self, data):
                super().__init__(data)

            def keys(self):
                return super().keys()

        rows = [MockRow({'id': 1, 'name': 'test'}), MockRow({'id': 2, 'name': 'test2'})]
        result = api.rows_to_dicts(rows)
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['name'] == 'test2'

    def test_rows_to_dicts_empty_list(self):
        """rows_to_dicts should return empty list for empty input."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.rows_to_dicts([])
        assert result == []

    def test_rows_to_dicts_none_input(self):
        """rows_to_dicts should return empty list for None input."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.rows_to_dicts(None)
        assert result == []

    def test_row_to_dict_converts_single_row(self):
        """row_to_dict should convert a single row to dictionary."""
        from bookbagofholding.api_v2.base import ApiBase

        # Use a mock that behaves like a sqlite Row (supports dict() conversion)
        class MockRow(dict):
            def __init__(self, data):
                super().__init__(data)

        api = ApiBase()
        row = MockRow({'id': 1, 'name': 'test'})
        result = api.row_to_dict(row)
        assert result['id'] == 1
        assert result['name'] == 'test'

    def test_row_to_dict_none_input(self):
        """row_to_dict should return None for None input."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        result = api.row_to_dict(None)
        assert result is None


class TestApiBaseDatabaseMethods:
    """Tests for ApiBase database access methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def api_with_mock_db(self, mock_db):
        """Create ApiBase with mocked database."""
        from bookbagofholding.api_v2.base import ApiBase

        api = ApiBase()
        api._db = mock_db
        return api

    def test_db_property_lazy_initialization(self):
        """db property should lazily initialize database connection."""
        from bookbagofholding.api_v2.base import ApiBase
        from bookbagofholding import database

        with patch.object(database, 'DBConnection') as mock_db_class:
            mock_conn = MagicMock()
            mock_db_class.return_value = mock_conn

            api = ApiBase()
            api._db = None  # Reset

            # Access db property
            db = api.db
            assert db is mock_conn
            mock_db_class.assert_called_once()

    def test_get_author_by_id_returns_author(self, api_with_mock_db, mock_db):
        """get_author_by_id should query and return author data."""
        mock_row = MagicMock()
        mock_row.keys.return_value = ['AuthorID', 'AuthorName']
        mock_row.__iter__ = Mock(return_value=iter([('AuthorID', 'A123'), ('AuthorName', 'Test Author')]))
        mock_db.match.return_value = mock_row

        result = api_with_mock_db.get_author_by_id('A123')
        mock_db.match.assert_called_once()
        assert 'AuthorID' in str(mock_db.match.call_args)

    def test_get_author_by_id_returns_none_when_not_found(self, api_with_mock_db, mock_db):
        """get_author_by_id should return None when author not found."""
        mock_db.match.return_value = None

        result = api_with_mock_db.get_author_by_id('NONEXISTENT')
        assert result is None

    def test_get_book_by_id_returns_book(self, api_with_mock_db, mock_db):
        """get_book_by_id should query and return book data."""
        mock_row = MagicMock()
        mock_db.match.return_value = mock_row

        api_with_mock_db.get_book_by_id('B123')
        mock_db.match.assert_called_once()
        assert 'BookID' in str(mock_db.match.call_args)

    def test_check_author_exists_returns_true(self, api_with_mock_db, mock_db):
        """check_author_exists should return True when author exists."""
        mock_db.match.return_value = {'AuthorID': 'A123'}

        result = api_with_mock_db.check_author_exists('A123')
        assert result is True

    def test_check_author_exists_returns_false(self, api_with_mock_db, mock_db):
        """check_author_exists should return False when author not found."""
        mock_db.match.return_value = None

        result = api_with_mock_db.check_author_exists('NONEXISTENT')
        assert result is False

    def test_get_books_by_status(self, api_with_mock_db, mock_db):
        """get_books_by_status should query books with specified status."""
        mock_db.select.return_value = []

        api_with_mock_db.get_books_by_status('Wanted')
        mock_db.select.assert_called_once()
        call_args = str(mock_db.select.call_args)
        assert 'Status' in call_args


class TestApiV2ModuleImports:
    """Tests for api_v2 module imports."""

    def test_module_imports_successfully(self):
        """api_v2 module should import without errors."""
        from bookbagofholding import api_v2
        assert api_v2 is not None

    def test_all_exports_available(self):
        """All __all__ exports should be available."""
        from bookbagofholding.api_v2 import (
            ApiBase,
            api_endpoint,
            require_param,
            AuthorApi,
            BookApi,
            SystemApi
        )

        assert ApiBase is not None
        assert api_endpoint is not None
        assert require_param is not None
        assert AuthorApi is not None
        assert BookApi is not None
        assert SystemApi is not None


class TestAuthorApi:
    """Tests for AuthorApi class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def author_api(self, mock_db):
        """Create AuthorApi with mocked database."""
        from bookbagofholding.api_v2.author_api import AuthorApi

        api = AuthorApi()
        api._db = mock_db
        return api

    def test_get_index_returns_authors(self, author_api, mock_db):
        """get_index should return list of authors."""
        mock_db.select.return_value = []

        result = author_api.get_index()
        assert isinstance(result, list)

    def test_get_author_returns_author_data(self, author_api, mock_db):
        """get_author should return author data with books."""
        # Mock author lookup
        mock_author_row = MagicMock()
        mock_author_row.keys.return_value = ['AuthorID', 'AuthorName']
        mock_author_row.__iter__ = Mock(return_value=iter([
            ('AuthorID', 'A123'),
            ('AuthorName', 'Test Author')
        ]))
        mock_db.match.return_value = mock_author_row
        mock_db.select.return_value = []

        result = author_api.get_author(id='A123')
        assert result is not None

    def test_get_author_missing_id_returns_error(self, author_api):
        """get_author should return error when id is missing."""
        result = author_api.get_author()
        assert result['success'] is False
        assert 'id' in result['error'].lower()


class TestBookApi:
    """Tests for BookApi class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def book_api(self, mock_db):
        """Create BookApi with mocked database."""
        from bookbagofholding.api_v2.book_api import BookApi

        api = BookApi()
        api._db = mock_db
        return api

    def test_get_wanted_returns_wanted_books(self, book_api, mock_db):
        """get_wanted should return books with Wanted status."""
        mock_db.select.return_value = []

        result = book_api.get_wanted()
        mock_db.select.assert_called()
        # Verify Wanted status was queried
        call_args = str(mock_db.select.call_args)
        assert 'Wanted' in call_args or 'Status' in call_args

    def test_get_snatched_returns_snatched_books(self, book_api, mock_db):
        """get_snatched should return books with Snatched status."""
        mock_db.select.return_value = []

        result = book_api.get_snatched()
        mock_db.select.assert_called()

    def test_get_book_returns_book_data(self, book_api, mock_db):
        """get_book should return book data."""
        mock_book_row = MagicMock()
        mock_book_row.keys.return_value = ['BookID', 'BookName']
        mock_book_row.__iter__ = Mock(return_value=iter([
            ('BookID', 'B123'),
            ('BookName', 'Test Book')
        ]))
        mock_db.match.return_value = mock_book_row

        result = book_api.get_book(id='B123')
        assert result is not None

    def test_get_book_missing_id_returns_error(self, book_api):
        """get_book should return error when id is missing."""
        result = book_api.get_book()
        assert result['success'] is False


class TestSystemApi:
    """Tests for SystemApi class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def system_api(self, mock_db):
        """Create SystemApi with mocked database."""
        from bookbagofholding.api_v2.system_api import SystemApi

        api = SystemApi()
        api._db = mock_db
        return api

    def test_get_logs_returns_log_contents(self, system_api):
        """get_logs should return log contents."""
        import tempfile
        import os

        # Create a temp log file
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = os.path.join(tmpdir, 'bookbagofholding.log')
            with open(logfile, 'w') as f:
                f.write('test log content')

            with patch('bookbagofholding.api_v2.system_api.bookbagofholding') as mock_bb:
                mock_bb.CONFIG = {'LOGDIR': tmpdir}

                result = system_api.get_logs()
                assert result['success'] is True
                assert 'data' in result
                assert 'test log content' in result['data']

    def test_show_threads_returns_thread_names(self, system_api):
        """show_threads should return list of thread names."""
        result = system_api.show_threads()
        # show_threads returns a list directly, not a success dict
        assert isinstance(result, list)
        # Should return at least one thread name (could be any name)
        assert len(result) >= 1
        # All items should be strings
        assert all(isinstance(t, str) for t in result)

    def test_show_jobs_returns_job_status(self, system_api):
        """show_jobs should return job status."""
        with patch('bookbagofholding.api_v2.system_api.showJobs') as mock_show_jobs:
            mock_show_jobs.return_value = 'job status info'

            result = system_api.show_jobs()
            assert result['success'] is True
            assert 'data' in result


class TestDecoratorChaining:
    """Tests for chaining decorators."""

    def test_api_endpoint_and_require_param_together(self):
        """api_endpoint and require_param should work together."""
        from bookbagofholding.api_v2.base import api_endpoint, require_param, ApiBase

        class TestApi(ApiBase):
            @api_endpoint("Test endpoint", ["&id= author ID"])
            @require_param('id')
            def test_method(self, **kwargs):
                return self.success(data=kwargs['id'])

        api = TestApi()

        # Should have metadata from api_endpoint
        assert hasattr(api.test_method, '_api_endpoint')

        # Should validate params from require_param
        error_result = api.test_method()
        assert error_result['success'] is False

        # Should work with valid params
        success_result = api.test_method(id='test123')
        assert success_result['success'] is True
