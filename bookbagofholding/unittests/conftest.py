#  This file is part of Bookbag of Holding.
#
#  Bookbag of Holding is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

"""
Pytest configuration and shared fixtures for Bookbag of Holding tests.
"""

import os
import sys
import sqlite3
import tempfile
import shutil

import pytest

# Ensure bookbagofholding package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bookbagofholding


@pytest.fixture(scope='session', autouse=True)
def setup_bookbagofholding_globals():
    """Initialize Bookbag of Holding global variables needed for tests."""
    # Set up minimal configuration for tests
    bookbagofholding.PROG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bookbagofholding.DATADIR = tempfile.mkdtemp(prefix='ll_test_')
    bookbagofholding.SYS_ENCODING = 'utf-8'
    bookbagofholding.LOGLEVEL = 0  # Disable debug logging during tests
    bookbagofholding.CURRENT_BRANCH = 'master'

    # Initialize CONFIG dict if not present
    if not hasattr(bookbagofholding, 'CONFIG') or bookbagofholding.CONFIG is None:
        bookbagofholding.CONFIG = {}

    # Set up default config values used by various modules
    bookbagofholding.CONFIG.setdefault('EBOOK_TYPE', 'epub, mobi, pdf')
    bookbagofholding.CONFIG.setdefault('AUDIOBOOK_TYPE', 'mp3, m4b, m4a')
    bookbagofholding.CONFIG.setdefault('NAME_POSTFIX', 'jr, sr, phd, md, ii, iii, iv')
    bookbagofholding.CONFIG.setdefault('HTTP_TIMEOUT', '30')

    # Additional required CONFIG keys
    bookbagofholding.CONFIG.setdefault('USER_AGENT', '')
    bookbagofholding.CONFIG.setdefault('PROXY_HOST', '')
    bookbagofholding.CONFIG.setdefault('PROXY_TYPE', '')
    bookbagofholding.CONFIG.setdefault('LOGLIMIT', 500)
    bookbagofholding.CONFIG.setdefault('LOGDIR', os.path.join(bookbagofholding.DATADIR, 'Logs'))
    bookbagofholding.CONFIG.setdefault('DIR_PERM', '0o755')
    bookbagofholding.CONFIG.setdefault('FILE_PERM', '0o644')
    bookbagofholding.CONFIG.setdefault('GIT_PROGRAM', '')
    bookbagofholding.CONFIG.setdefault('GIT_HOST', 'github.com')
    bookbagofholding.CONFIG.setdefault('GIT_USER', 'sd0408')
    bookbagofholding.CONFIG.setdefault('GIT_REPO', 'Bookbag of Holding')
    bookbagofholding.CONFIG.setdefault('GIT_BRANCH', 'master')
    bookbagofholding.CONFIG.setdefault('GIT_UPDATED', 0)
    bookbagofholding.CONFIG.setdefault('LOGLEVEL', 0)
    bookbagofholding.CONFIG.setdefault('HTTP_EXT_TIMEOUT', 90)
    bookbagofholding.CONFIG.setdefault('CACHE_AGE', 30)

    # Create log directory
    log_dir = bookbagofholding.CONFIG['LOGDIR']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Initialize a simple mock logger to prevent logging errors
    class MockLogger:
        def debug(self, msg): pass
        def info(self, msg): pass
        def warn(self, msg): pass
        def error(self, msg): pass
        def warning(self, msg): pass

    # Set up mock logger if not properly initialized
    if not hasattr(bookbagofholding, 'logger') or bookbagofholding.logger is None:
        bookbagofholding.logger = MockLogger()

    # Initialize month names (needed by formatter)
    bookbagofholding.MONTHNAMES = {
        1: ['january', 'jan'],
        2: ['february', 'feb'],
        3: ['march', 'mar'],
        4: ['april', 'apr'],
        5: ['may', 'may'],
        6: ['june', 'jun'],
        7: ['july', 'jul'],
        8: ['august', 'aug'],
        9: ['september', 'sep'],
        10: ['october', 'oct'],
        11: ['november', 'nov'],
        12: ['december', 'dec'],
    }

    # Initialize provider lists (needed by formatter.dispName)
    bookbagofholding.NEWZNAB_PROV = []
    bookbagofholding.TORZNAB_PROV = []
    bookbagofholding.RSS_PROV = []

    yield

    # Cleanup temp directory after all tests
    if os.path.exists(bookbagofholding.DATADIR):
        shutil.rmtree(bookbagofholding.DATADIR, ignore_errors=True)


@pytest.fixture
def temp_db():
    """
    Create a temporary SQLite database for testing.

    Yields a tuple of (db_path, connection) that can be used for testing.
    The database is automatically cleaned up after the test.
    """
    # Create temp file for database
    fd, db_path = tempfile.mkstemp(suffix='.db', prefix='ll_test_')
    os.close(fd)

    # Store original DBFILE and set to temp
    original_dbfile = getattr(bookbagofholding, 'DBFILE', None)
    bookbagofholding.DBFILE = db_path

    # Create the database with basic schema
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Create core tables for testing
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS authors (
            AuthorID TEXT UNIQUE PRIMARY KEY,
            AuthorName TEXT,
            AuthorImg TEXT,
            AuthorLink TEXT,
            LastBookImg TEXT,
            Status TEXT DEFAULT 'Active',
            HaveBooks INTEGER DEFAULT 0,
            TotalBooks INTEGER DEFAULT 0,
            UnignoredBooks INTEGER DEFAULT 0,
            Manual INTEGER DEFAULT 0,
            GRfollow INTEGER DEFAULT 0,
            LastBookID TEXT,
            LastBook TEXT,
            LastDate TEXT,
            LastLink TEXT
        );

        CREATE TABLE IF NOT EXISTS books (
            BookID TEXT UNIQUE PRIMARY KEY,
            AuthorID TEXT,
            BookName TEXT,
            BookSub TEXT,
            BookDesc TEXT,
            BookGenre TEXT,
            BookIsbn TEXT,
            BookPub TEXT,
            BookRate TEXT,
            BookPages INTEGER,
            BookImg TEXT,
            BookFile TEXT,
            BookDate TEXT,
            BookLang TEXT,
            BookLink TEXT,
            BookAdded TEXT,
            Status TEXT DEFAULT 'Skipped',
            Manual INTEGER DEFAULT 0,
            SeriesDisplay TEXT,
            BookLibrary TEXT,
            AudioFile TEXT,
            AudioStatus TEXT,
            WorkPage TEXT,
            WorkID TEXT,
            Requester TEXT,
            FOREIGN KEY(AuthorID) REFERENCES authors(AuthorID) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS magazines (
            Title TEXT UNIQUE PRIMARY KEY,
            Regex TEXT,
            Status TEXT DEFAULT 'Active',
            IssueStatus TEXT DEFAULT 'Wanted',
            MagazineAdded TEXT,
            LastAcquired TEXT,
            IssueDate TEXT,
            LatestCover TEXT,
            DateType TEXT,
            CoverPage INTEGER DEFAULT 1,
            Reject TEXT
        );

        CREATE TABLE IF NOT EXISTS issues (
            IssueID TEXT UNIQUE PRIMARY KEY,
            Title TEXT,
            IssueDate TEXT,
            IssueAcquired TEXT,
            IssueFile TEXT,
            FOREIGN KEY(Title) REFERENCES magazines(Title) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS wanted (
            BookID TEXT,
            NZBurl TEXT,
            NZBtitle TEXT,
            NZBdate TEXT,
            NZBprov TEXT,
            NZBsize TEXT,
            Status TEXT,
            Source TEXT,
            DownloadID TEXT,
            DLResult TEXT
        );

        CREATE TABLE IF NOT EXISTS series (
            SeriesID INTEGER UNIQUE PRIMARY KEY,
            SeriesName TEXT,
            Status TEXT DEFAULT 'Active',
            Have INTEGER DEFAULT 0,
            Total INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS member (
            SeriesID INTEGER,
            BookID TEXT,
            WorkID TEXT,
            SeriesNum TEXT,
            FOREIGN KEY(SeriesID) REFERENCES series(SeriesID) ON DELETE CASCADE,
            FOREIGN KEY(BookID) REFERENCES books(BookID) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS users (
            UserID TEXT UNIQUE PRIMARY KEY,
            UserName TEXT UNIQUE,
            Password TEXT,
            Email TEXT,
            Perms INTEGER DEFAULT 0,
            HaveRead TEXT,
            ToRead TEXT,
            BookType TEXT,
            SendTo TEXT,
            Name TEXT,
            CalibreRead TEXT,
            CalibreToRead TEXT,
            Role TEXT DEFAULT 'guest',
            ApiKey TEXT,
            LastLogin TEXT,
            CreatedAt TEXT,
            PasswordChangedAt TEXT,
            PasswordAlgorithm TEXT DEFAULT 'md5'
        );

        CREATE TABLE IF NOT EXISTS sessions (
            SessionID TEXT PRIMARY KEY,
            UserID TEXT REFERENCES users(UserID) ON DELETE CASCADE,
            CreatedAt TEXT,
            ExpiresAt TEXT,
            IPAddress TEXT,
            UserAgent TEXT
        );
    ''')
    conn.commit()

    yield db_path, conn

    # Cleanup
    conn.close()
    bookbagofholding.DBFILE = original_dbfile
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_config():
    """
    Provide a mock configuration dictionary for testing.

    This fixture provides commonly used config values without
    affecting the global bookbagofholding.CONFIG.
    """
    return {
        'HTTP_PORT': 5299,
        'HTTP_HOST': '0.0.0.0',
        'HTTP_ROOT': '/',
        'HTTP_TIMEOUT': 30,
        'EBOOK_TYPE': 'epub, mobi, pdf',
        'AUDIOBOOK_TYPE': 'mp3, m4b, m4a',
        'NAME_POSTFIX': 'jr, sr, phd, md, ii, iii, iv',
        'MATCH_RATIO': 80,
        'DLOAD_RATIO': 90,
        'SAB_HOST': 'localhost',
        'SAB_PORT': 8080,
        'SAB_APIKEY': 'test-api-key',
        'SAB_USER': '',
        'SAB_PASS': '',
    }


@pytest.fixture
def sample_author_data():
    """Provide sample author data for testing."""
    return {
        'AuthorID': 'test-author-001',
        'AuthorName': 'Test Author',
        'AuthorImg': 'http://example.com/author.jpg',
        'AuthorLink': 'http://example.com/author',
        'Status': 'Active',
        'HaveBooks': 5,
        'TotalBooks': 10,
    }


@pytest.fixture
def sample_book_data():
    """Provide sample book data for testing."""
    return {
        'BookID': 'test-book-001',
        'AuthorID': 'test-author-001',
        'BookName': 'Test Book Title',
        'BookSub': 'A Subtitle',
        'BookDesc': 'This is a test book description.',
        'BookGenre': 'Fiction',
        'BookIsbn': '9781234567890',
        'BookPub': 'Test Publisher',
        'BookRate': '4.5',
        'BookPages': 300,
        'BookDate': '2023-01-15',
        'BookLang': 'en',
        'Status': 'Wanted',
    }


class MockLogger:
    """Mock logger for testing that captures log messages."""

    def __init__(self):
        self.debug_messages = []
        self.info_messages = []
        self.warn_messages = []
        self.error_messages = []

    def debug(self, msg):
        self.debug_messages.append(msg)

    def info(self, msg):
        self.info_messages.append(msg)

    def warn(self, msg):
        self.warn_messages.append(msg)

    def error(self, msg):
        self.error_messages.append(msg)

    def clear(self):
        self.debug_messages.clear()
        self.info_messages.clear()
        self.warn_messages.clear()
        self.error_messages.clear()


@pytest.fixture
def mock_logger(monkeypatch):
    """
    Replace the bookbagofholding logger with a mock for testing.

    Returns the mock logger instance so tests can inspect logged messages.
    """
    mock = MockLogger()
    monkeypatch.setattr(bookbagofholding, 'logger', mock)
    # Also patch the logger module reference if it exists
    if hasattr(bookbagofholding, 'logger'):
        monkeypatch.setattr('bookbagofholding.logger', mock)
    return mock


# ============================================================================
# CherryPy and API Testing Fixtures
# ============================================================================

@pytest.fixture
def cherrypy_request_mock():
    """Mock CherryPy request object for testing web handlers."""
    from unittest.mock import Mock
    mock_request = Mock()
    mock_request.cookie = {}
    mock_request.headers = {
        'X-Forwarded-For': None,
        'X-Host': None,
        'Remote-Addr': '127.0.0.1',
        'Host': 'localhost:5299'
    }
    mock_request.remote = Mock(ip='127.0.0.1')
    return mock_request


@pytest.fixture
def cherrypy_response_mock():
    """Mock CherryPy response object for testing."""
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.cookie = {}
    return mock_response


@pytest.fixture
def api_config():
    """Configure API-specific settings for testing."""
    original_config = dict(bookbagofholding.CONFIG)

    # Set up API config
    bookbagofholding.CONFIG['API_ENABLED'] = True
    bookbagofholding.CONFIG['API_KEY'] = 'a' * 32  # Valid 32-char key

    # Initialize other required settings
    bookbagofholding.CONFIG.setdefault('HTTP_PORT', 5299)
    bookbagofholding.CONFIG.setdefault('HTTP_HOST', '0.0.0.0')
    bookbagofholding.CONFIG.setdefault('HTTP_ROOT', '/')
    bookbagofholding.CONFIG.setdefault('USER_ACCOUNTS', False)
    bookbagofholding.CONFIG.setdefault('SORT_SURNAME', False)
    bookbagofholding.CONFIG.setdefault('SORT_DEFINITE', False)
    bookbagofholding.CONFIG.setdefault('DISPLAYLENGTH', 100)

    # Initialize LOGLIST if needed
    if not hasattr(bookbagofholding, 'LOGLIST'):
        bookbagofholding.LOGLIST = []

    yield bookbagofholding.CONFIG

    # Restore original config
    bookbagofholding.CONFIG.clear()
    bookbagofholding.CONFIG.update(original_config)


@pytest.fixture
def authenticated_user(temp_db):
    """Create an authenticated test user with admin permissions."""
    import hashlib
    from bookbagofholding.database import DBConnection

    db = DBConnection()
    user_id = 'test-admin-user'
    username = 'testadmin'
    password_hash = hashlib.md5('testpass'.encode()).hexdigest()

    db.action(
        "INSERT INTO users (UserID, UserName, Password, PasswordAlgorithm, Perms, Role) VALUES (?, ?, ?, ?, ?, ?)",
        [user_id, username, password_hash, 'md5', 65535, 'admin']  # 65535 = perm_admin (all permissions)
    )

    return {
        'UserID': user_id,
        'UserName': username,
        'Password': 'testpass',
        'PasswordHash': password_hash,
        'PasswordAlgorithm': 'md5',
        'Perms': 65535,
        'Role': 'admin'
    }


@pytest.fixture
def sample_wanted_data():
    """Provide sample wanted entry data for testing."""
    return {
        'BookID': 'test-book-001',
        'NZBurl': 'http://example.com/nzb/12345',
        'NZBtitle': 'Test Book Title',
        'NZBdate': '2023-01-15',
        'NZBprov': 'TestProvider',
        'NZBsize': '1.5 MB',
        'Status': 'Snatched',
        'Source': 'TestSource',
        'DownloadID': 'dl-12345'
    }
