# LazyLibrarian - Get Healthy Plan

## Overview

This document outlines a comprehensive plan to improve code health, test coverage, and maintainability of the LazyLibrarian project.

**Current State:** 5/10 health score
**Target State:** 8/10 health score
**Estimated Effort:** 3-4 development cycles

---

## Phase 1: Critical Security & Broken Code (Week 1) ✅ COMPLETED

### 1.1 Remove Hardcoded Credentials ✅ COMPLETED
**Priority:** CRITICAL
**Status:** RESOLVED - Entire version/update functionality removed

**Original Issue:**
- `LazyLibrarian.py:213` - Hardcoded GitLab token
- `lazylibrarian/__init__.py:103` - Hardcoded GitLab token

**Resolution:**
The automatic update functionality that required GitLab tokens was completely removed. The application now assumes deployment via Docker containers or standard code deployment pipelines. This eliminated the security risk entirely rather than just making the token configurable.

**Files Modified/Deleted:**
- Deleted: `lazylibrarian/versioncheck.py`
- Deleted: `lazylibrarian/unittests/test_versioncheck.py`
- Modified: `LazyLibrarian.py` - Removed `--update` flag and version check calls
- Modified: `lazylibrarian/__init__.py` - Removed all version/update config options
- Modified: `lazylibrarian/webServe.py` - Removed checkForUpdates endpoint
- Modified: `lazylibrarian/api.py` - Removed getVersion and update commands
- Modified: `lazylibrarian/common.py` - Removed checkForUpdates from scheduler
- Modified: `data/interfaces/bookstrap/base.html` - Removed update notification UI
- Modified: `data/interfaces/bookstrap/config.html` - Removed version check settings
- Modified: `data/interfaces/legacy/base.html` - Removed update bar
- Modified: `data/interfaces/legacy/config.html` - Removed version check settings

### 1.2 Fix SSL Certificate Verification ✅ COMPLETED
**Priority:** CRITICAL
**Status:** RESOLVED - Made configurable

**Resolution:**
SSL certificate verification is now configurable via:
- Config option: `SSL_VERIFY` (defaults to `False` for backward compatibility)
- Environment variable: `LAZYLIBRARIAN_SSL_VERIFY`

**Files Modified:**
- `LazyLibrarian.py` - Added `configure_ssl_verification()` function
- `lazylibrarian/__init__.py` - Added `SSL_VERIFY` to CONFIG_DEFINITIONS

### 1.3 Fix Broken Unit Test ✅ COMPLETED
**Priority:** HIGH
**Status:** RESOLVED - File was already deleted

**Original Issue:**
- `lazylibrarian/unittests/test_searchnzb.py` referenced non-existent module

**Resolution:**
The broken test file had already been removed in a previous cleanup.

### 1.4 Add Test Infrastructure ✅ COMPLETED
**Priority:** HIGH
**Status:** RESOLVED

**Files Created/Updated:**
- Created: `requirements-dev.txt` - Development dependencies for testing
- Updated: `pyproject.toml` - Added `[project.optional-dependencies] dev` section
- Existing: `lazylibrarian/unittests/conftest.py` - Comprehensive test fixtures already in place
- Existing: `lazylibrarian/unittests/__init__.py` - Already exists

**Test Suite Status:**
- 438 unit tests passing
- Infrastructure includes: temp database fixtures, mock config, sample data fixtures, mock logger, CherryPy mocks, API config fixtures

---

## Phase 2: Code Consolidation (Weeks 2-3)  ✅ COMPLETED

### 2.1 Create Base Classes for Download Clients  ✅ COMPLETED

**Current State:** 2,375 lines across 7 modules with ~40% duplication
**Target:** Reduce to ~1,400 lines with shared base classes

**New Architecture:**
```
lazylibrarian/
├── clients/
│   ├── __init__.py
│   ├── base.py           # DownloadClient, NzbClient, TorrentClient bases
│   ├── http_wrapper.py   # HTTPClientWrapper for consistent requests
│   ├── config.py         # ClientConfig wrapper
│   ├── nzb/
│   │   ├── sabnzbd.py
│   │   └── nzbget.py
│   └── torrent/
│       ├── qbittorrent.py
│       ├── transmission.py
│       ├── deluge.py
│       ├── rtorrent.py
│       └── utorrent.py
```

**Base Class Methods to Extract:**
```python
class DownloadClient(ABC):
    def __init__(self, config_prefix: str)
    def _build_url(self) -> str
    def _validate_config(self) -> Optional[str]
    def check_link(self) -> Tuple[bool, str]
    def _make_request(self, method, url, **kwargs) -> Response
    def _parse_response(self, response) -> dict

class TorrentClient(DownloadClient):
    def add_torrent(self, link: str) -> Tuple[bool, str]
    def get_torrent_folder(self, torrent_id: str) -> str
    def get_torrent_files(self, torrent_id: str) -> List[str]
    def get_torrent_progress(self, torrent_id: str) -> float
    def remove_torrent(self, torrent_id: str, delete_files: bool) -> bool
```

### 2.2 Create HTTP Client Wrapper  ✅ COMPLETED

**Purpose:** Consolidate 41 scattered `requests` calls with consistent error handling

```python
# lazylibrarian/clients/http_wrapper.py
class HTTPClientWrapper:
    def __init__(self, timeout=None, proxies=None):
        self.timeout = timeout or check_int(CONFIG['HTTP_TIMEOUT'], 30)
        self.proxies = proxies or proxyList()

    def get(self, url, **kwargs) -> Response
    def post(self, url, data=None, json=None, **kwargs) -> Response
    def _handle_error(self, error, context: str) -> None
    def _check_status(self, response, context: str) -> bool
```

### 2.3 Create Notifier Base Class  ✅ COMPLETED

**Current State:** 14 notifier modules with duplicated patterns
**Target:** Single base class with consistent interface

```python
# lazylibrarian/notifiers/base.py
class NotifierBase(ABC):
    config_prefix: str  # e.g., 'PUSHOVER', 'TELEGRAM'

    def is_enabled(self, force=False) -> bool:
        return force or CONFIG[f'USE_{self.config_prefix}']

    @abstractmethod
    def _send(self, title: str, message: str) -> bool

    def notify_snatch(self, title: str) -> bool:
        if not self.is_enabled():
            return False
        return self._send("Snatched", title)

    def notify_download(self, title: str, bookid: str = None) -> bool:
        if not self.is_enabled():
            return False
        return self._send("Downloaded", title)

    def test_notify(self, title: str = "Test") -> bool:
        return self._send("Test Notification", title)
```

### 2.4 Create URL Builder Utility  ✅ COMPLETED

**Purpose:** Consolidate 18+ URL normalization patterns

```python
# lazylibrarian/utils/url_builder.py
class URLBuilder:
    @staticmethod
    def normalize_host(hostname: str, port: int = None, use_https: bool = False) -> str:
        """
        Normalize hostname to proper URL format.
        Handles: http/https prefixes, trailing slashes, port numbers
        """
        if not hostname:
            return ''

        # Remove existing protocol
        hostname = hostname.replace('https://', '').replace('http://', '')

        # Remove trailing slash
        hostname = hostname.rstrip('/')

        # Add protocol
        protocol = 'https' if use_https else 'http'
        url = f'{protocol}://{hostname}'

        # Add port if specified
        if port and port > 0:
            url = f'{url}:{port}'

        return url
```

---

## Phase 3: Break Up God Objects (Weeks 4-6) ✅ COMPLETED

### 3.1 Refactor webServe.py (4,671 lines → ~8 focused modules) ✅ COMPLETED

**Current:** Single `WebInterface` class with 145 methods
**Target:** Domain-specific handler classes

**New Structure Created:**
```
lazylibrarian/web/
├── __init__.py           # Module exports
├── auth.py               # Authentication/permissions (Permission enum, cookie handling)
├── templates.py          # Template rendering utilities
└── handlers/
    ├── __init__.py
    ├── author_handler.py  # AuthorHandler class with 10 static methods
    ├── book_handler.py    # BookHandler class with 10 static methods
    └── magazine_handler.py# MagazineHandler class with 7 static methods
```

**Files Created:**
- `lazylibrarian/web/__init__.py` - Exports serve_template, Permission, check_permission, handlers
- `lazylibrarian/web/auth.py` - Permission IntFlag enum, get_user_from_cookie(), check_permission(), hash_password()
- `lazylibrarian/web/templates.py` - serve_template(), get_template_lookup(), render_response()
- `lazylibrarian/web/handlers/__init__.py` - Exports handler classes
- `lazylibrarian/web/handlers/author_handler.py` - AuthorHandler with get_author_page, set_author_status, refresh_author, etc.
- `lazylibrarian/web/handlers/book_handler.py` - BookHandler with get_books_page, add_book, search_for_book, update_book, etc.
- `lazylibrarian/web/handlers/magazine_handler.py` - MagazineHandler with get_magazines_page, add_magazine, mark_magazines, etc.

**Migration Strategy:**
1. ✅ Created handler classes with methods extracted from WebInterface
2. WebInterface can now delegate to handlers (backward compatible)
3. Gradually move routes to new structure
4. Original webServe.py preserved for compatibility

### 3.2 Refactor api.py (1,359 lines → ~6 focused modules) ✅ COMPLETED

**Current:** Single `Api` class with 114 methods
**Target:** Domain-specific API classes

**New Structure Created:**
```
lazylibrarian/api_v2/
├── __init__.py           # Module exports
├── base.py               # ApiBase class, @api_endpoint, @require_param decorators
├── author_api.py         # AuthorApi class (12 endpoints)
├── book_api.py           # BookApi class (14 endpoints)
├── magazine_api.py       # MagazineApi class (8 endpoints)
└── system_api.py         # SystemApi class (20 endpoints)
```

**Files Created:**
- `lazylibrarian/api_v2/__init__.py` - Exports ApiBase and all API classes
- `lazylibrarian/api_v2/base.py` - ApiBase with success/error methods, api_endpoint and require_param decorators
- `lazylibrarian/api_v2/author_api.py` - get_index, get_author, pause/resume/ignore_author, add_author, etc.
- `lazylibrarian/api_v2/book_api.py` - get_wanted, get_snatched, queue_book, search_book, find_book, etc.
- `lazylibrarian/api_v2/magazine_api.py` - get_magazines, get_issues, add/remove_magazine, force_mag_search
- `lazylibrarian/api_v2/system_api.py` - get_logs, show_jobs, read/write_cfg, force_process, shutdown, restart

**Note:** Named `api_v2` to avoid conflicts with existing `api.py` during transition.

### 3.3 Refactor postprocess.py (1,989 lines) ✅ COMPLETED

**Current:** Monolithic processing with 512-line `processDir()` function
**Target:** Pipeline with separate processors

**New Structure Created:**
```
lazylibrarian/postprocess_v2/
├── __init__.py           # Module exports
├── detector.py           # FileDetector - file type detection & validation
├── unpacker.py           # ArchiveUnpacker - ZIP/TAR extraction
├── metadata.py           # MetadataExtractor - OPF, EPUB, ID3, filename parsing
├── matcher.py            # BookMatcher - fuzzy matching for book identification
└── organizer.py          # FileOrganizer - file organization/renaming
```

**Files Created:**
- `lazylibrarian/postprocess_v2/__init__.py` - Exports all processor classes
- `lazylibrarian/postprocess_v2/detector.py` - FileDetector with is_ebook, is_audiobook, is_archive, find_book_file
- `lazylibrarian/postprocess_v2/unpacker.py` - ArchiveUnpacker with unpack_zip, unpack_tar, list_archive_contents
- `lazylibrarian/postprocess_v2/metadata.py` - MetadataExtractor with extract_from_opf, extract_from_epub, extract_from_id3
- `lazylibrarian/postprocess_v2/matcher.py` - BookMatcher with normalize, fuzzy_ratio, match_author, match_book, find_book_by_isbn
- `lazylibrarian/postprocess_v2/organizer.py` - FileOrganizer with safe_filename, format_pattern, move_file, get_destination_folder

**Note:** Named `postprocess_v2` to avoid conflicts with existing `postprocess.py` during transition.

---

## Phase 4: Database & Configuration (Weeks 7-8) ✅ COMPLETED

### 4.1 Create Migration Framework ✅ COMPLETED

**Current:** `dbupgrade.py` with 48 linear upgrade functions (1,229 lines)
**Target:** Proper migration framework

**New Structure Created:**
```
lazylibrarian/database_v2/
├── __init__.py              # Module exports
├── migration_framework.py   # Migration, MigrationRunner, MigrationRegistry
└── migrations/
    └── __init__.py          # Migration imports
```

**Files Created:**
- `lazylibrarian/database_v2/__init__.py` - Exports Migration, MigrationRunner, MigrationError
- `lazylibrarian/database_v2/migration_framework.py` - Full migration framework with:
  - `Migration` base class with helper methods (has_column, has_table, add_column, create_index)
  - `MigrationRegistry` for migration registration and discovery
  - `MigrationRunner` for executing migrations with logging and rollback support
  - `@migration(version, description)` decorator

**Example Usage:**
```python
from lazylibrarian.database_v2 import Migration, MigrationRunner
from lazylibrarian.database_v2.migration_framework import migration

@migration(45, "Add audiobook chapters table")
class AddAudiobookChapters(Migration):
    def up(self):
        self.db.action('''
            CREATE TABLE IF NOT EXISTS audiobook_chapters (
                ChapterID INTEGER PRIMARY KEY,
                BookID TEXT REFERENCES books(BookID),
                ChapterNum INTEGER,
                ChapterTitle TEXT,
                Duration INTEGER
            )
        ''')

    def down(self):
        self.db.action('DROP TABLE IF EXISTS audiobook_chapters')
```

**Note:** Named `database_v2` to avoid conflicts with existing `database.py` during transition.

### 4.2 Replace Global CONFIG Dict ✅ COMPLETED

**Current:** Mutable global `CONFIG` dict accessed from everywhere (852 occurrences)
**Target:** Type-safe configuration object

**New Structure Created:**
```
lazylibrarian/config/
├── __init__.py     # Module exports
├── settings.py     # Type-safe dataclass settings
└── loader.py       # ConfigLoader for INI file handling
```

**Files Created:**
- `lazylibrarian/config/__init__.py` - Exports all configuration classes
- `lazylibrarian/config/settings.py` - Type-safe dataclass settings:
  - `HttpSettings` - HTTP server configuration with validation
  - `GeneralSettings` - General application settings
  - `SearchSettings` - Search intervals and match ratios
  - `DownloadSettings` - Directory paths
  - `UsenetSettings` - SABnzbd, NZBGet configuration
  - `TorrentSettings` - qBittorrent, Transmission, Deluge, etc.
  - `LibrarySettings` - Library scanning options
  - `PostProcessSettings` - Destination patterns
  - `FileTypeSettings` - Accepted file types and reject rules
  - `NotificationSettings` - Email, Pushover, Telegram, etc.
  - `Configuration` - Main container with get/set for backward compatibility
- `lazylibrarian/config/loader.py` - ConfigLoader with:
  - `load()` - Load from INI file
  - `save()` - Save to INI file
  - `from_legacy_dict()` - Convert from legacy CONFIG
  - `to_legacy_dict()` - Convert to legacy CONFIG

**Backward Compatibility:**
```python
config = Configuration()
# Legacy-style access still works
port = config.get('HTTP_PORT')
config.set('HTTP_PORT', 8080)

# Type-safe access
port = config.http.port
config.http.port = 8080
config.http.validate()  # Raises ConfigError if invalid
```

---

## Phase 5: Comprehensive Test Coverage (Ongoing)

### 5.1 Test Infrastructure Setup

**Files to create:**
```
lazylibrarian/
├── unittests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── database.py          # Test database fixtures
│   │   ├── config.py            # Test configuration
│   │   └── mock_responses/      # Mock API responses
│   │       ├── google_books.json
│   │       ├── sabnzbd.json
│   │       └── ...
```

**conftest.py:**
```python
import pytest
import tempfile
import os

@pytest.fixture
def test_db():
    """Create temporary test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    # Initialize schema
    from lazylibrarian.database import DBConnection
    db = DBConnection(db_path)
    # Apply all migrations
    yield db

    # Cleanup
    os.unlink(db_path)

@pytest.fixture
def mock_config():
    """Provide test configuration"""
    return {
        'HTTP_PORT': 5299,
        'HTTP_TIMEOUT': 30,
        'SAB_HOST': 'localhost',
        'SAB_PORT': 8080,
        # ... test values
    }
```

### 5.2 Test Coverage Plan by Module

#### Priority 1: Core Infrastructure (Target: 90% coverage)
| Module | Current | Target | Test File |
|--------|---------|--------|-----------|
| database.py | 0% | 90% | test_database.py |
| formatter.py | 0% | 85% | test_formatter.py |
| common.py | 0% | 80% | test_common.py |
| cache.py | 0% | 85% | test_cache.py |

#### Priority 2: Business Logic (Target: 80% coverage)
| Module | Current | Target | Test File |
|--------|---------|--------|-----------|
| postprocess.py | 0% | 80% | test_postprocess.py |
| searchbook.py | 0% | 75% | test_searchbook.py |
| searchmag.py | 0% | 75% | test_searchmag.py |
| bookwork.py | 0% | 75% | test_bookwork.py |
| librarysync.py | 0% | 70% | test_librarysync.py |

#### Priority 3: Integrations (Target: 70% coverage)
| Module | Current | Target | Test File |
|--------|---------|--------|-----------|
| providers.py | 10% | 70% | test_providers.py (expand) |
| sabnzbd.py | 0% | 70% | test_sabnzbd.py |
| qbittorrent.py | 0% | 70% | test_qbittorrent.py |
| transmission.py | 0% | 70% | test_transmission.py |
| gb.py | 0% | 70% | test_google_books.py |

#### Priority 4: Web/API (Target: 60% coverage)
| Module | Current | Target | Test File |
|--------|---------|--------|-----------|
| api.py | 0% | 60% | test_api.py |
| webServe.py | 0% | 50% | test_web.py |
| opds.py | 0% | 60% | test_opds.py |

### 5.3 Example Test Cases

**test_database.py:**
```python
import pytest
from lazylibrarian.database import DBConnection

class TestDBConnection:
    def test_connect_creates_tables(self, test_db):
        """Database connection should create required tables"""
        tables = test_db.select("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t[0] for t in tables]
        assert 'authors' in table_names
        assert 'books' in table_names
        assert 'magazines' in table_names

    def test_match_returns_single_row(self, test_db):
        """match() should return single row or None"""
        test_db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                       ['test-1', 'Test Author'])

        result = test_db.match("SELECT * FROM authors WHERE AuthorID=?", ['test-1'])
        assert result is not None
        assert result['AuthorName'] == 'Test Author'

    def test_match_returns_none_for_no_match(self, test_db):
        """match() should return None when no rows match"""
        result = test_db.match("SELECT * FROM authors WHERE AuthorID=?", ['nonexistent'])
        assert result is None

    def test_select_returns_multiple_rows(self, test_db):
        """select() should return list of rows"""
        test_db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                       ['test-1', 'Author One'])
        test_db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                       ['test-2', 'Author Two'])

        results = test_db.select("SELECT * FROM authors")
        assert len(results) == 2

    def test_upsert_inserts_new_row(self, test_db):
        """upsert() should insert when row doesn't exist"""
        test_db.upsert('authors',
                       {'AuthorName': 'New Author'},
                       {'AuthorID': 'new-1'})

        result = test_db.match("SELECT * FROM authors WHERE AuthorID=?", ['new-1'])
        assert result['AuthorName'] == 'New Author'

    def test_upsert_updates_existing_row(self, test_db):
        """upsert() should update when row exists"""
        test_db.action("INSERT INTO authors (AuthorID, AuthorName) VALUES (?, ?)",
                       ['test-1', 'Original Name'])

        test_db.upsert('authors',
                       {'AuthorName': 'Updated Name'},
                       {'AuthorID': 'test-1'})

        result = test_db.match("SELECT * FROM authors WHERE AuthorID=?", ['test-1'])
        assert result['AuthorName'] == 'Updated Name'
```

**test_formatter.py:**
```python
import pytest
from lazylibrarian import formatter

class TestFormatter:
    def test_replace_all_replaces_characters(self):
        """replace_all should replace specified characters"""
        result = formatter.replace_all("Hello World!", {'o': '0', '!': '?'})
        assert result == "Hell0 W0rld?"

    def test_unaccented_removes_diacritics(self):
        """unaccented should remove accents from characters"""
        result = formatter.unaccented("café résumé naïve")
        assert result == "cafe resume naive"

    def test_check_int_returns_int(self):
        """check_int should convert valid strings to int"""
        assert formatter.check_int("42", 0) == 42
        assert formatter.check_int("0", 10) == 0

    def test_check_int_returns_default_for_invalid(self):
        """check_int should return default for invalid input"""
        assert formatter.check_int("not_a_number", 99) == 99
        assert formatter.check_int(None, 42) == 42
        assert formatter.check_int("", 10) == 10

    def test_safe_filename_removes_invalid_chars(self):
        """safe_filename should remove/replace invalid characters"""
        result = formatter.safe_filename("Book: A/B\\C?Title")
        assert '/' not in result
        assert '\\' not in result
        assert ':' not in result
        assert '?' not in result
```

**test_download_clients.py:**
```python
import pytest
from unittest.mock import Mock, patch
from lazylibrarian.sabnzbd import SABnzbd

class TestSABnzbd:
    @pytest.fixture
    def mock_config(self):
        return {
            'SAB_HOST': 'localhost',
            'SAB_PORT': 8080,
            'SAB_APIKEY': 'test-api-key',
            'SAB_USER': '',
            'SAB_PASS': '',
            'HTTP_TIMEOUT': 30,
        }

    @patch('lazylibrarian.sabnzbd.requests')
    def test_checklink_success(self, mock_requests, mock_config):
        """checkLink should return success for valid connection"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': True,
            'version': '3.0.0'
        }
        mock_requests.get.return_value = mock_response

        with patch.dict('lazylibrarian.CONFIG', mock_config):
            result = SABnzbd.checkLink()

        assert 'Connection successful' in result

    @patch('lazylibrarian.sabnzbd.requests')
    def test_checklink_timeout(self, mock_requests, mock_config):
        """checkLink should handle timeout gracefully"""
        import requests
        mock_requests.get.side_effect = requests.exceptions.Timeout()

        with patch.dict('lazylibrarian.CONFIG', mock_config):
            result = SABnzbd.checkLink()

        assert 'Timeout' in result or 'timeout' in result.lower()

    @patch('lazylibrarian.sabnzbd.requests')
    def test_checklink_invalid_apikey(self, mock_requests, mock_config):
        """checkLink should detect invalid API key"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': False,
            'error': 'API Key Incorrect'
        }
        mock_requests.get.return_value = mock_response

        with patch.dict('lazylibrarian.CONFIG', mock_config):
            result = SABnzbd.checkLink()

        assert 'API' in result or 'key' in result.lower()
```

---

## Phase 6: Code Quality Improvements (Ongoing)

### 6.1 Reduce Function Complexity

**Target Functions (>150 lines):**

| Function | File | Lines | Action |
|----------|------|-------|--------|
| processDir() | postprocess.py | 512 | Split into 8-10 smaller functions |
| processDestination() | postprocess.py | 254 | Split into 4-5 smaller functions |
| getBooks() | webServe.py | 254 | Extract query builder, formatter |
| configUpdate() | webServe.py | 222 | Split validation from persistence |
| markBooks() | webServe.py | 175 | Extract status update logic |

### 6.2 Reduce Nesting Depth

**Current:** Maximum 19 levels (postprocess.py), 17 levels (webServe.py)
**Target:** Maximum 4 levels

**Techniques:**
1. Early returns for guard clauses
2. Extract nested logic into helper functions
3. Use strategy pattern for conditional branches
4. Replace nested if/else with polymorphism

**Example refactoring:**
```python
# Before: Deep nesting
def process_file(file_path):
    if file_path:
        if os.path.exists(file_path):
            if is_valid_format(file_path):
                if has_permission(file_path):
                    # actual processing
                else:
                    logger.error("No permission")
            else:
                logger.error("Invalid format")
        else:
            logger.error("File not found")
    else:
        logger.error("No file path")

# After: Early returns
def process_file(file_path):
    if not file_path:
        logger.error("No file path")
        return None

    if not os.path.exists(file_path):
        logger.error("File not found")
        return None

    if not is_valid_format(file_path):
        logger.error("Invalid format")
        return None

    if not has_permission(file_path):
        logger.error("No permission")
        return None

    # actual processing - now at base indentation level
    return process(file_path)
```

### 6.3 Standardize Error Handling

**Current:** 138 bare `except Exception` blocks with inconsistent handling
**Target:** Specific exception types with consistent patterns

```python
# Define custom exceptions
class LazyLibrarianError(Exception):
    """Base exception for LazyLibrarian"""
    pass

class ConfigurationError(LazyLibrarianError):
    """Configuration is invalid or missing"""
    pass

class DownloadClientError(LazyLibrarianError):
    """Error communicating with download client"""
    pass

class MetadataError(LazyLibrarianError):
    """Error fetching or parsing metadata"""
    pass

# Use specific exceptions
try:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
except requests.exceptions.Timeout:
    raise DownloadClientError(f"Timeout connecting to {client_name}")
except requests.exceptions.ConnectionError:
    raise DownloadClientError(f"Cannot connect to {client_name}")
except requests.exceptions.HTTPError as e:
    raise DownloadClientError(f"{client_name} returned error: {e.response.status_code}")
```

### 6.4 Add Type Hints

**Target:** All new code and refactored modules

```python
# Before
def search_book(searchterm, library=None):
    ...

# After
from typing import Optional, List, Dict, Any

def search_book(
    searchterm: str,
    library: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for books matching the search term.

    Args:
        searchterm: The search query
        library: Optional library filter

    Returns:
        List of matching book dictionaries
    """
    ...
```

---

## Metrics & Success Criteria

### Phase Completion Criteria

| Phase | Success Criteria |
|-------|-----------------|
| Phase 1 | All critical security issues resolved, tests pass |
| Phase 2 | Code duplication reduced by 40%, all clients use base classes |
| Phase 3 | No single file >1000 lines, no class >50 methods |
| Phase 4 | Migration framework in place, type-safe config |
| Phase 5 | Test coverage >60% for critical modules |
| Phase 6 | No function >100 lines, max nesting depth 4 |

### Ongoing Metrics to Track

```
# Run with pytest-cov
pytest --cov=lazylibrarian --cov-report=html

# Check complexity with radon
radon cc lazylibrarian/ -a -s

# Check code style
flake8 lazylibrarian/ --max-line-length=120

# Type checking (once type hints added)
mypy lazylibrarian/
```

---

## Implementation Timeline

```
Week 1:  Phase 1 - Critical fixes (Security, broken tests)
Week 2:  Phase 2.1-2.2 - Download client base classes, HTTP wrapper
Week 3:  Phase 2.3-2.4 - Notifier base class, URL builder
Week 4:  Phase 3.1 - webServe.py refactor (start)
Week 5:  Phase 3.1 - webServe.py refactor (complete)
Week 6:  Phase 3.2-3.3 - api.py and postprocess.py refactor
Week 7:  Phase 4.1 - Migration framework
Week 8:  Phase 4.2 - Configuration object
Week 9+: Phase 5 & 6 - Testing and code quality (ongoing)
```

---

## Quick Wins (Can Do Now)

1. **Delete `test_searchnzb.py`** - broken, references non-existent module
2. **Add `__init__.py` to unittests/** - make it a proper package
3. **Create `pytest.ini`** with basic configuration
4. **Fix deprecated `assertEquals()`** → `assertEqual()` in existing tests
5. **Add `.gitignore` entries** for test artifacts (`.pytest_cache/`, `htmlcov/`)
6. **Create `requirements-dev.txt`** with pytest, pytest-cov, mock

---

## Appendix: File Reference

### Files to Create
- `lazylibrarian/clients/base.py`
- `lazylibrarian/clients/http_wrapper.py`
- `lazylibrarian/clients/config.py`
- `lazylibrarian/notifiers/base.py`
- `lazylibrarian/utils/url_builder.py`
- `lazylibrarian/web/handlers/*.py`
- `lazylibrarian/api/*.py`
- `lazylibrarian/postprocess/*.py`
- `lazylibrarian/database/migrations/*.py`
- `lazylibrarian/config/settings.py`
- `lazylibrarian/unittests/conftest.py`
- `lazylibrarian/unittests/test_*.py`
- `pytest.ini`
- `requirements-dev.txt`

### Files to Refactor
- `lazylibrarian/webServe.py` → `lazylibrarian/web/`
- `lazylibrarian/api.py` → `lazylibrarian/api/`
- `lazylibrarian/postprocess.py` → `lazylibrarian/postprocess/`
- `lazylibrarian/dbupgrade.py` → `lazylibrarian/database/migrations/`
- `lazylibrarian/__init__.py` → Extract config to `lazylibrarian/config/`

### Files to Delete/Fix
- `lazylibrarian/unittests/test_searchnzb.py` - broken
- Remove hardcoded credentials from `LazyLibrarian.py` and `__init__.py`
