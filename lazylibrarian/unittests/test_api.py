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
Unit tests for lazylibrarian.api module.

Tests cover:
- Api class initialization
- checkParams() validation
- fetchData property
- API commands for authors, books, magazines, system
"""

import json
import pytest
from unittest.mock import Mock, patch

import lazylibrarian
from lazylibrarian.api import Api, cmd_dict
from lazylibrarian.database import DBConnection


# ============================================================================
# Test checkParams Validation
# ============================================================================

@pytest.mark.api
class TestApiCheckParams:
    """Tests for Api.checkParams() validation."""

    def test_checkParams_rejects_disabled_api(self, api_config):
        """checkParams should reject when API is disabled."""
        lazylibrarian.CONFIG['API_ENABLED'] = False

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='help')

        assert 'not enabled' in api.data

    def test_checkParams_rejects_empty_api_key_config(self, api_config):
        """checkParams should reject when API key is not configured."""
        lazylibrarian.CONFIG['API_KEY'] = ''

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='help')

        assert 'not generated' in api.data

    def test_checkParams_rejects_invalid_length_api_key_config(self, api_config):
        """checkParams should reject when API key is not 32 chars."""
        lazylibrarian.CONFIG['API_KEY'] = 'short'

        api = Api()
        api.checkParams(apikey='short', cmd='help')

        assert 'invalid' in api.data

    def test_checkParams_rejects_missing_apikey_param(self, api_config):
        """checkParams should reject missing API key parameter."""
        api = Api()
        api.checkParams(cmd='help')

        assert 'Missing api key' in api.data

    def test_checkParams_rejects_incorrect_apikey(self, api_config):
        """checkParams should reject incorrect API key."""
        api = Api()
        api.checkParams(apikey='wrong' * 8, cmd='help')

        assert 'Incorrect API key' in api.data

    def test_checkParams_rejects_missing_cmd(self, api_config):
        """checkParams should reject missing command parameter."""
        api = Api()
        api.checkParams(apikey='a' * 32)

        assert 'Missing parameter: cmd' in api.data

    def test_checkParams_rejects_unknown_cmd(self, api_config):
        """checkParams should reject unknown command."""
        api = Api()
        api.checkParams(apikey='a' * 32, cmd='nonexistent_command')

        assert 'Unknown command' in api.data

    def test_checkParams_accepts_valid_request(self, api_config):
        """checkParams should accept valid API key and command."""
        api = Api()
        api.checkParams(apikey='a' * 32, cmd='help')

        assert api.data == 'OK'
        assert api.cmd == 'help'
        assert api.apikey == 'a' * 32


# ============================================================================
# Test Help Command
# ============================================================================

@pytest.mark.api
class TestApiHelp:
    """Tests for Api._help() command."""

    @patch('cherrypy.request')
    def test_help_returns_cmd_dict(self, mock_request, api_config):
        """_help should return command dictionary."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='help')
        result = api.fetchData

        parsed = json.loads(result)
        assert 'getIndex' in parsed
        assert 'help' in parsed
        assert 'getWanted' in parsed

    @patch('cherrypy.request')
    def test_help_contains_all_commands(self, mock_request, api_config):
        """_help should return all commands from cmd_dict."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='help')
        result = api.fetchData

        parsed = json.loads(result)
        for cmd in cmd_dict:
            assert cmd in parsed


# ============================================================================
# Test Author Commands
# ============================================================================

@pytest.mark.api
class TestApiAuthors:
    """Tests for author-related API commands."""

    @patch('cherrypy.request')
    def test_getIndex_returns_authors(self, mock_request, api_config, temp_db, sample_author_data):
        """getIndex should return list of authors."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        # Insert test author
        db = DBConnection()
        db.action(
            "INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
            [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active']
        )

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getIndex')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert parsed[0]['AuthorName'] == sample_author_data['AuthorName']

    @patch('cherrypy.request')
    def test_getIndex_empty_database(self, mock_request, api_config, temp_db):
        """getIndex should return empty list when no authors."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getIndex')
        result = api.fetchData

        parsed = json.loads(result)
        assert parsed == []

    @patch('cherrypy.request')
    def test_getAuthor_returns_author_and_books(self, mock_request, api_config, temp_db,
                                                 sample_author_data, sample_book_data):
        """getAuthor should return author details and their books."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        # Insert author and book
        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName) VALUES (?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'], sample_book_data['BookName']])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getAuthor', id=sample_author_data['AuthorID'])
        result = api.fetchData

        parsed = json.loads(result)
        assert 'author' in parsed
        assert 'books' in parsed
        assert len(parsed['author']) == 1
        assert len(parsed['books']) == 1

    @patch('cherrypy.request')
    def test_getAuthor_missing_id(self, mock_request, api_config, temp_db):
        """getAuthor should return error when id is missing."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getAuthor')
        result = api.fetchData

        assert 'Missing parameter: id' in result

    @patch('cherrypy.request')
    def test_getAuthor_invalid_id(self, mock_request, api_config, temp_db):
        """getAuthor should return empty results for invalid id."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getAuthor', id='nonexistent-id')
        result = api.fetchData

        parsed = json.loads(result)
        assert parsed['author'] == []
        assert parsed['books'] == []

    @patch('cherrypy.request')
    def test_pauseAuthor_sets_status(self, mock_request, api_config, temp_db, sample_author_data):
        """pauseAuthor should set author status to Paused."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='pauseAuthor', id=sample_author_data['AuthorID'])
        api.fetchData

        result = db.match("SELECT Status FROM authors WHERE AuthorID=?",
                          (sample_author_data['AuthorID'],))
        assert result['Status'] == 'Paused'

    @patch('cherrypy.request')
    def test_pauseAuthor_missing_id(self, mock_request, api_config, temp_db):
        """pauseAuthor should return error when id is missing."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='pauseAuthor')
        result = api.fetchData

        assert 'Missing parameter: id' in result

    @patch('cherrypy.request')
    def test_pauseAuthor_invalid_id(self, mock_request, api_config, temp_db):
        """pauseAuthor should return error for invalid id."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='pauseAuthor', id='nonexistent-id')
        result = api.fetchData

        assert 'Invalid id' in result

    @patch('cherrypy.request')
    def test_resumeAuthor_sets_status(self, mock_request, api_config, temp_db, sample_author_data):
        """resumeAuthor should set author status to Active."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Paused'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='resumeAuthor', id=sample_author_data['AuthorID'])
        api.fetchData

        result = db.match("SELECT Status FROM authors WHERE AuthorID=?",
                          (sample_author_data['AuthorID'],))
        assert result['Status'] == 'Active'

    @patch('cherrypy.request')
    def test_ignoreAuthor_sets_status(self, mock_request, api_config, temp_db, sample_author_data):
        """ignoreAuthor should set author status to Ignored."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='ignoreAuthor', id=sample_author_data['AuthorID'])
        api.fetchData

        result = db.match("SELECT Status FROM authors WHERE AuthorID=?",
                          (sample_author_data['AuthorID'],))
        assert result['Status'] == 'Ignored'


# ============================================================================
# Test Book Commands
# ============================================================================

@pytest.mark.api
class TestApiBooks:
    """Tests for book-related API commands."""

    @patch('cherrypy.request')
    def test_getWanted_returns_wanted_books(self, mock_request, api_config, temp_db,
                                             sample_author_data, sample_book_data):
        """getWanted should return books with Wanted status."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Wanted'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getWanted')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert parsed[0]['Status'] == 'Wanted'

    @patch('cherrypy.request')
    def test_getWanted_excludes_non_wanted(self, mock_request, api_config, temp_db,
                                            sample_author_data, sample_book_data):
        """getWanted should not return books that aren't Wanted."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Skipped'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getWanted')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) == 0

    @patch('cherrypy.request')
    def test_getSnatched_returns_snatched_books(self, mock_request, api_config, temp_db,
                                                 sample_author_data, sample_book_data):
        """getSnatched should return books with Snatched status."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Snatched'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getSnatched')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert parsed[0]['Status'] == 'Snatched'

    @patch('cherrypy.request')
    def test_queueBook_sets_wanted_status(self, mock_request, api_config, temp_db,
                                           sample_author_data, sample_book_data):
        """queueBook should set book status to Wanted."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Skipped'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='queueBook', id=sample_book_data['BookID'])
        result = api.fetchData

        assert result == 'OK'
        db_result = db.match("SELECT Status FROM books WHERE BookID=?", (sample_book_data['BookID'],))
        assert db_result['Status'] == 'Wanted'

    @patch('cherrypy.request')
    def test_queueBook_audiobook_type(self, mock_request, api_config, temp_db,
                                       sample_author_data, sample_book_data):
        """queueBook with type=AudioBook should set AudioStatus to Wanted."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status, AudioStatus) VALUES (?, ?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Skipped', 'Skipped'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='queueBook', id=sample_book_data['BookID'], type='AudioBook')
        result = api.fetchData

        assert result == 'OK'
        db_result = db.match("SELECT AudioStatus FROM books WHERE BookID=?", (sample_book_data['BookID'],))
        assert db_result['AudioStatus'] == 'Wanted'

    @patch('cherrypy.request')
    def test_queueBook_missing_id(self, mock_request, api_config, temp_db):
        """queueBook should return error when id is missing."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='queueBook')
        result = api.fetchData

        assert 'Missing parameter: id' in result

    @patch('cherrypy.request')
    def test_queueBook_invalid_id(self, mock_request, api_config, temp_db):
        """queueBook should return error for invalid id."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='queueBook', id='nonexistent-id')
        result = api.fetchData

        assert 'Invalid id' in result

    @patch('cherrypy.request')
    def test_unqueueBook_sets_skipped_status(self, mock_request, api_config, temp_db,
                                              sample_author_data, sample_book_data):
        """unqueueBook should set book status to Skipped."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Wanted'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='unqueueBook', id=sample_book_data['BookID'])
        result = api.fetchData

        assert result == 'OK'
        db_result = db.match("SELECT Status FROM books WHERE BookID=?", (sample_book_data['BookID'],))
        assert db_result['Status'] == 'Skipped'


# ============================================================================
# Test Magazine Commands
# ============================================================================

@pytest.mark.api
class TestApiMagazines:
    """Tests for magazine-related API commands."""

    @patch('cherrypy.request')
    def test_getMagazines_returns_magazines(self, mock_request, api_config, temp_db, sample_magazine_data):
        """getMagazines should return list of magazines."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO magazines (Title, Status) VALUES (?, ?)",
                  [sample_magazine_data['Title'], 'Active'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getMagazines')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert parsed[0]['Title'] == sample_magazine_data['Title']

    @patch('cherrypy.request')
    def test_getMagazines_empty_database(self, mock_request, api_config, temp_db):
        """getMagazines should return empty list when no magazines."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getMagazines')
        result = api.fetchData

        parsed = json.loads(result)
        assert parsed == []

    @patch('cherrypy.request')
    def test_addMagazine_creates_magazine(self, mock_request, api_config, temp_db):
        """addMagazine should create new magazine entry."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='addMagazine', name='Test API Magazine')
        api.fetchData

        db = DBConnection()
        result = db.match("SELECT * FROM magazines WHERE Title=?", ('Test API Magazine',))
        assert result is not None
        assert result['Status'] == 'Active'
        assert result['IssueStatus'] == 'Wanted'

    @patch('cherrypy.request')
    def test_addMagazine_missing_name(self, mock_request, api_config, temp_db):
        """addMagazine should return error when name is missing."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='addMagazine')
        result = api.fetchData

        assert 'Missing parameter: name' in result

    @patch('cherrypy.request')
    def test_removeMagazine_deletes_magazine(self, mock_request, api_config, temp_db):
        """removeMagazine should delete magazine entry."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO magazines (Title, Status) VALUES (?, ?)", ('Delete Me', 'Active'))

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='removeMagazine', name='Delete Me')
        api.fetchData

        result = db.match("SELECT * FROM magazines WHERE Title=?", ('Delete Me',))
        assert result is None or result == []

    @patch('cherrypy.request')
    def test_removeMagazine_missing_name(self, mock_request, api_config, temp_db):
        """removeMagazine should return error when name is missing."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='removeMagazine')
        result = api.fetchData

        assert 'Missing parameter: name' in result

    @patch('cherrypy.request')
    def test_getIssues_returns_magazine_and_issues(self, mock_request, api_config, temp_db, sample_magazine_data):
        """getIssues should return magazine details and issues."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO magazines (Title, Status) VALUES (?, ?)",
                  [sample_magazine_data['Title'], 'Active'])
        db.action("INSERT INTO issues (IssueID, Title, IssueDate) VALUES (?, ?, ?)",
                  ['issue-001', sample_magazine_data['Title'], '2023-01'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getIssues', name=sample_magazine_data['Title'])
        result = api.fetchData

        parsed = json.loads(result)
        assert 'magazine' in parsed
        assert 'issues' in parsed
        assert len(parsed['issues']) == 1


# ============================================================================
# Test System Commands
# ============================================================================

@pytest.mark.api
class TestApiSystem:
    """Tests for system-related API commands."""

    @patch('cherrypy.request')
    def test_getLogs_returns_loglist(self, mock_request, api_config):
        """getLogs should return current log list."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        lazylibrarian.LOGLIST = ['Test log entry 1', 'Test log entry 2']

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getLogs')
        result = api.fetchData

        parsed = json.loads(result)
        assert 'Test log entry 1' in parsed

    @patch('cherrypy.request')
    def test_showThreads_returns_thread_names(self, mock_request, api_config):
        """showThreads should return list of thread names."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='showThreads')
        result = api.fetchData

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        # At least one thread should be running
        assert len(parsed) >= 1

    @patch('cherrypy.request')
    def test_showMonths_returns_monthnames(self, mock_request, api_config):
        """showMonths should return month names dictionary."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='showMonths')
        result = api.fetchData

        parsed = json.loads(result)
        assert '1' in parsed or 1 in parsed  # January

    @patch('cherrypy.request')
    def test_shutdown_sets_signal(self, mock_request, api_config):
        """shutdown should set SIGNAL to 'shutdown'."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        lazylibrarian.SIGNAL = None

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='shutdown')
        api.fetchData

        assert lazylibrarian.SIGNAL == 'shutdown'
        lazylibrarian.SIGNAL = None  # Reset

    @patch('cherrypy.request')
    def test_restart_sets_signal(self, mock_request, api_config):
        """restart should set SIGNAL to 'restart'."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        lazylibrarian.SIGNAL = None

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='restart')
        api.fetchData

        assert lazylibrarian.SIGNAL == 'restart'
        lazylibrarian.SIGNAL = None  # Reset


# ============================================================================
# Test Missing Parameters (Parametrized)
# ============================================================================

@pytest.mark.api
class TestApiMissingParams:
    """Tests for API commands with missing required parameters."""

    @pytest.mark.parametrize("cmd,missing_param", [
        ('getAuthor', 'id'),
        ('pauseAuthor', 'id'),
        ('resumeAuthor', 'id'),
        ('ignoreAuthor', 'id'),
        ('queueBook', 'id'),
        ('unqueueBook', 'id'),
        ('addMagazine', 'name'),
        ('removeMagazine', 'name'),
        ('getIssues', 'name'),
        ('refreshAuthor', 'name'),
        ('findAuthor', 'name'),
        ('findBook', 'name'),
        ('addAuthor', 'name'),
        ('addAuthorID', 'id'),
        ('addBook', 'id'),
        ('searchBook', 'id'),
        ('removeAuthor', 'id'),
        ('readCFG', 'name'),
        ('writeCFG', 'name'),
        ('getWorkSeries', 'id'),
        ('getWorkPage', 'id'),
        ('getBookCover', 'id'),
        ('getAuthorImage', 'id'),
        ('getSeriesMembers', 'id'),
        ('getBookAuthors', 'id'),
    ])
    @patch('cherrypy.request')
    def test_command_requires_parameter(self, mock_request, api_config, cmd, missing_param):
        """API commands should report missing required parameters."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        api = Api()
        api.checkParams(apikey='a' * 32, cmd=cmd)
        result = api.fetchData

        assert f'Missing parameter: {missing_param}' in result


# ============================================================================
# Test getAllBooks Command
# ============================================================================

@pytest.mark.api
class TestApiGetAllBooks:
    """Tests for getAllBooks command."""

    @patch('cherrypy.request')
    def test_getAllBooks_returns_all_books(self, mock_request, api_config, temp_db,
                                           sample_author_data, sample_book_data):
        """getAllBooks should return all books with author info."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Wanted'])

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getAllBooks')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert 'AuthorName' in parsed[0]
        assert 'BookName' in parsed[0]


# ============================================================================
# Test History Command
# ============================================================================

@pytest.mark.api
class TestApiHistory:
    """Tests for getHistory command."""

    @patch('cherrypy.request')
    def test_getHistory_returns_wanted_entries(self, mock_request, api_config, temp_db,
                                                sample_wanted_data):
        """getHistory should return wanted entries excluding Skipped/Ignored."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action(
            "INSERT INTO wanted (BookID, NZBtitle, Status) VALUES (?, ?, ?)",
            [sample_wanted_data['BookID'], sample_wanted_data['NZBtitle'], 'Snatched']
        )

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getHistory')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) >= 1
        assert parsed[0]['Status'] == 'Snatched'

    @patch('cherrypy.request')
    def test_getHistory_excludes_skipped(self, mock_request, api_config, temp_db):
        """getHistory should exclude entries with Skipped status."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action(
            "INSERT INTO wanted (BookID, NZBtitle, Status) VALUES (?, ?, ?)",
            ['book-skipped', 'Skipped Book', 'Skipped']
        )

        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getHistory')
        result = api.fetchData

        parsed = json.loads(result)
        assert len(parsed) == 0
