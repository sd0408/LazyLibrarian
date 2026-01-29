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
Integration tests for LazyLibrarian.

These tests verify end-to-end workflows and component interaction.
Marked with @pytest.mark.integration for selective execution.
"""

import json
import pytest
from unittest.mock import Mock, patch

import lazylibrarian
from lazylibrarian.database import DBConnection
from lazylibrarian.api import Api


# ============================================================================
# Author Workflow Integration Tests
# ============================================================================

@pytest.mark.integration
class TestAuthorWorkflow:
    """Integration tests for complete author workflow."""

    @patch('cherrypy.request')
    def test_add_and_retrieve_author_via_api(self, mock_request, api_config, temp_db, sample_author_data):
        """Adding an author should make them retrievable via API."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        # Directly insert author (simulating addAuthor result)
        db = DBConnection()
        db.action(
            "INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
            [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active']
        )

        # Retrieve via API
        api = Api()
        api.checkParams(apikey='a' * 32, cmd='getIndex')
        result = json.loads(api.fetchData)

        assert len(result) >= 1
        assert any(a['AuthorName'] == sample_author_data['AuthorName'] for a in result)

    @patch('cherrypy.request')
    def test_pause_and_resume_author_cycle(self, mock_request, api_config, temp_db, sample_author_data):
        """Author status should cycle correctly through pause/resume."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        # Insert active author
        db = DBConnection()
        db.action(
            "INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
            [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active']
        )

        # Pause
        api1 = Api()
        api1.checkParams(apikey='a' * 32, cmd='pauseAuthor', id=sample_author_data['AuthorID'])
        api1.fetchData

        status = db.match("SELECT Status FROM authors WHERE AuthorID=?",
                          (sample_author_data['AuthorID'],))
        assert status['Status'] == 'Paused'

        # Resume
        api2 = Api()
        api2.checkParams(apikey='a' * 32, cmd='resumeAuthor', id=sample_author_data['AuthorID'])
        api2.fetchData

        status = db.match("SELECT Status FROM authors WHERE AuthorID=?",
                          (sample_author_data['AuthorID'],))
        assert status['Status'] == 'Active'


# ============================================================================
# Book Status Workflow Integration Tests
# ============================================================================

@pytest.mark.integration
class TestBookStatusWorkflow:
    """Integration tests for book status changes."""

    @patch('cherrypy.request')
    def test_queue_unqueue_book_workflow(self, mock_request, api_config, temp_db,
                                          sample_author_data, sample_book_data):
        """Queueing and unqueueing a book should change its status correctly."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()
        db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName']])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Skipped'])

        # Queue the book
        api1 = Api()
        api1.checkParams(apikey='a' * 32, cmd='queueBook', id=sample_book_data['BookID'])
        api1.fetchData

        status = db.match("SELECT Status FROM books WHERE BookID=?",
                          (sample_book_data['BookID'],))
        assert status['Status'] == 'Wanted'

        # Verify it appears in getWanted
        api2 = Api()
        api2.checkParams(apikey='a' * 32, cmd='getWanted')
        wanted = json.loads(api2.fetchData)
        assert any(b['BookID'] == sample_book_data['BookID'] for b in wanted)

        # Unqueue the book
        api3 = Api()
        api3.checkParams(apikey='a' * 32, cmd='unqueueBook', id=sample_book_data['BookID'])
        api3.fetchData

        status = db.match("SELECT Status FROM books WHERE BookID=?",
                          (sample_book_data['BookID'],))
        assert status['Status'] == 'Skipped'

        # Verify it no longer appears in getWanted
        api4 = Api()
        api4.checkParams(apikey='a' * 32, cmd='getWanted')
        wanted = json.loads(api4.fetchData)
        assert not any(b['BookID'] == sample_book_data['BookID'] for b in wanted)


# ============================================================================
# Magazine Workflow Integration Tests
# ============================================================================
# User Authentication Workflow Integration Tests
# ============================================================================

@pytest.mark.integration
class TestUserAuthenticationWorkflow:
    """Integration tests for user authentication."""

    @patch('cherrypy.request')
    @patch('cherrypy.response')
    def test_login_logout_workflow(self, mock_response, mock_request, api_config, temp_db):
        """User should be able to login and logout."""
        import hashlib
        from unittest.mock import MagicMock
        from lazylibrarian.webServe import WebInterface

        mock_request.cookie = {}
        mock_request.remote = Mock(ip='127.0.0.1')
        mock_response.cookie = MagicMock()

        lazylibrarian.USER_BLOCKLIST = []
        lazylibrarian.SHOWLOGOUT = 0

        db = DBConnection()
        pwd_hash = hashlib.md5('integrationpass'.encode()).hexdigest()
        db.action("INSERT INTO users (UserID, UserName, Password, Perms) VALUES (?, ?, ?, ?)",
                  ['integration-user', 'integrationuser', pwd_hash, 65535])

        wi = WebInterface()

        # Login
        result = wi.user_login(username='integrationuser', password='integrationpass')
        assert result == ''  # Empty string = success
        assert lazylibrarian.SHOWLOGOUT == 1

        # Logout (should raise HTTPRedirect)
        import cherrypy
        with pytest.raises(cherrypy.HTTPRedirect):
            wi.logout()

        lazylibrarian.USER_BLOCKLIST = []
        lazylibrarian.SHOWLOGOUT = 0


# ============================================================================
# API and Database Integration Tests
# ============================================================================

@pytest.mark.integration
class TestApiDatabaseIntegration:
    """Integration tests for API commands that modify database."""

    @patch('cherrypy.request')
    def test_api_commands_persist_changes(self, mock_request, api_config, temp_db,
                                           sample_author_data, sample_book_data):
        """API commands should properly persist changes to database."""
        mock_request.headers = {'X-Forwarded-For': None}
        mock_request.remote = Mock(ip='127.0.0.1')

        db = DBConnection()

        # Insert initial data
        db.action("INSERT INTO authors (AuthorID, AuthorName, Status) VALUES (?, ?, ?)",
                  [sample_author_data['AuthorID'], sample_author_data['AuthorName'], 'Active'])
        db.action("INSERT INTO books (BookID, AuthorID, BookName, Status) VALUES (?, ?, ?, ?)",
                  [sample_book_data['BookID'], sample_author_data['AuthorID'],
                   sample_book_data['BookName'], 'Skipped'])

        # Make changes via API
        api = Api()
        api.checkParams(apikey='a' * 32, cmd='ignoreAuthor', id=sample_author_data['AuthorID'])
        api.fetchData

        # Verify changes persisted (use new connection)
        db2 = DBConnection()
        author = db2.match("SELECT Status FROM authors WHERE AuthorID=?",
                           (sample_author_data['AuthorID'],))
        assert author['Status'] == 'Ignored'
