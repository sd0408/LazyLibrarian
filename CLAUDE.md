# LazyLibrarian - System Architecture Documentation

## Overview

LazyLibrarian is an open-source book/magazine metadata aggregation and download automation system. It monitors authors and retrieves metadata for digital reading materials (ebooks, audiobooks, magazines, comics) by integrating with multiple book databases and download sources.

**License:** GNU GPL v3
**Source Repository:** [GitLab](https://gitlab.com/LazyLibrarian/LazyLibrarian)
**Public Documentation:** https://lazylibrarian.gitlab.io/

---

## Quick Reference

| Item | Details |
|------|---------|
| **Entry Point** | `LazyLibrarian.py` |
| **Config File** | `config.ini` (INI format) |
| **Database** | SQLite 3 with WAL mode (schema version 44) |
| **Web Framework** | CherryPy + Mako templates |
| **Scheduler** | APScheduler |
| **Python Version** | Python 2.7+ / Python 3.6+ |
| **Default Port** | 5299 |

---

## Workflow Requirements

**IMPORTANT:** After completing each task that modifies code, you MUST run the unit tests to verify nothing is broken:

```bash
source .venv/bin/activate && python -m pytest lazylibrarian/unittests/
```

Do not consider a task complete until tests pass. If tests fail, fix the issues before moving on.

---

## Project Structure

```
LazyLibrarian/
├── LazyLibrarian.py              # Main entry point (292 lines)
├── lazylibrarian/                # Core application package (47 modules)
│   ├── __init__.py               # Global config, constants, initialization (68KB)
│   ├── webStart.py               # CherryPy server initialization
│   ├── webServe.py               # Web interface routes (226KB, 154+ handlers)
│   ├── api.py                    # REST API endpoints (100+ commands)
│   ├── database.py               # SQLite abstraction layer
│   ├── dbupgrade.py              # Schema versioning (v1-v44)
│   ├── common.py                 # Utilities & scheduler management
│   ├── logger.py                 # Rotating log system
│   ├── cache.py                  # HTTP caching & requests
│   ├── formatter.py              # Text/data formatting utilities
│   ├── classes.py                # Data model classes (NZB, torrent results)
│   │
│   ├── # Metadata Sources
│   ├── gr.py                     # Goodreads API integration
│   ├── gb.py                     # Google Books API integration
│   ├── grsync.py                 # Goodreads sync
│   │
│   ├── # Search & Providers
│   ├── searchbook.py             # Book search logic
│   ├── searchmag.py              # Magazine search logic
│   ├── searchrss.py              # RSS/Wishlist search
│   ├── providers.py              # Provider adapter interface
│   ├── torrentparser.py          # TPB, KAT, WWT, ZOO, LIME, TDL parsers
│   ├── directparser.py           # LibGen direct parsing
│   │
│   ├── # Download Clients
│   ├── downloadmethods.py        # NZB & torrent download dispatch
│   ├── sabnzbd.py                # SABnzbd integration
│   ├── nzbget.py                 # NZBGet integration
│   ├── qbittorrent.py            # qBittorrent integration
│   ├── rtorrent.py               # rTorrent integration
│   ├── utorrent.py               # uTorrent integration
│   ├── transmission.py           # Transmission integration
│   ├── deluge.py                 # Deluge integration
│   ├── synology.py               # Synology DownloadStation
│   │
│   ├── # Library Management
│   ├── librarysync.py            # Library scanning & import
│   ├── postprocess.py            # Download post-processing (104KB)
│   ├── bookwork.py               # Book metadata & series management
│   ├── bookrename.py             # File renaming utilities
│   ├── magazinescan.py           # Magazine management
│   ├── importer.py               # CSV & book import
│   ├── calibre.py                # Calibre integration
│   ├── images.py                 # Image download & caching
│   │
│   ├── # Services
│   ├── opds.py                   # OPDS catalog service
│   ├── rssfeed.py                # RSS feed generation
│   ├── notifiers/                # Notification backends (14 services)
│   │
│   ├── # Utilities
│   ├── version.py                # Version info
│   ├── versioncheck.py           # Update checker
│   ├── csvfile.py                # CSV handling
│   ├── resultlist.py             # Search result processing
│   ├── magnet2torrent.py         # Magnet link conversion
│   └── unittests/                # Unit tests
│
├── cherrypy/                     # Bundled CherryPy framework
├── mako/                         # Bundled Mako template engine
├── lib/                          # Bundled Python 2 libraries
│   ├── apscheduler/              # Job scheduler
│   ├── requests/                 # HTTP library
│   ├── fuzzywuzzy/               # Fuzzy string matching
│   ├── bencode/                  # Torrent encoding
│   ├── deluge_client/            # Deluge RPC
│   ├── cherrypy_cors.py          # CORS support
│   └── six/                      # Python 2/3 compatibility
├── lib3/                         # Bundled Python 3 libraries
│
├── data/
│   ├── interfaces/
│   │   ├── bookstrap/            # Modern Bootstrap UI (Mako templates)
│   │   └── legacy/               # Legacy UI template
│   ├── css/                      # Stylesheets
│   ├── js/                       # JavaScript assets
│   └── images/                   # UI images
│
├── init/                         # OS-specific init scripts
│   ├── lazylibrarian.service     # systemd service file
│   ├── lazylibrarian.init        # init.d script
│   └── ...
│
└── # Example Files
    ├── example_custom_notification.py
    ├── example_ebook_convert.py
    ├── example_preprocessor.py
    └── example.monthnames.json
```

---

## Tech Stack

### Core Framework
| Component | Technology | Version/Notes |
|-----------|------------|---------------|
| Web Server | CherryPy | v18+ bundled |
| Templates | Mako | Bundled |
| Database | SQLite 3 | WAL mode, FK enforced |
| Scheduler | APScheduler | Bundled in lib/ |
| HTTP Client | Requests | Bundled in lib/ |

### Python Compatibility
- Python 2.7+ and Python 3.6+
- Uses `lib.six` for compatibility layer
- Separate `lib/` (Py2) and `lib3/` (Py3) directories

### Key Libraries
- **FuzzyWuzzy** - Fuzzy string matching for book/author verification
- **BeautifulSoup4** - HTML parsing for web scraping
- **FeedParser** - RSS/Atom feed parsing
- **Bencode** - Torrent file encoding/decoding

---

## Architecture

### Startup Flow

```
LazyLibrarian.py
    │
    ├── Parse command-line arguments (optparse)
    ├── Set paths (PROG_DIR, DATADIR, CONFIGFILE)
    ├── Detect system encoding
    │
    └── lazylibrarian.initialize()
        ├── Create/verify data directories
        ├── Initialize logging system
        ├── Load config.ini → CONFIG dict
        ├── Connect to SQLite database
        ├── Check/upgrade database schema
        └── Initialize cache directories
            │
            └── webStart.initialize()
                ├── Configure CherryPy
                ├── Set up static file serving
                ├── Register URL routes
                └── Start CherryPy engine
                    │
                    └── lazylibrarian.start()
                        ├── Start APScheduler
                        ├── Schedule background jobs
                        └── Enter main event loop
```

### Command-Line Options

```
-d, --daemon      Run as daemon (non-Windows)
-q, --quiet       Don't log to console
--debug           Show debug log messages
--nolaunch        Don't open browser
--update          Force update check
--port PORT       Override HTTP port
--datadir DIR     Override data directory
--config FILE     Override config file
-p, --pidfile     Write PID to file
--loglevel LEVEL  Set debug log level
```

### Threading Model

| Thread Name | Purpose |
|-------------|---------|
| MAIN | Main event loop, signal handling |
| WEBSERVER | CherryPy HTTP server |
| search_book | Book search background task |
| search_magazine | Magazine search task |
| PostProcessor | Download post-processing |
| checkForUpdates | Version checking |
| sync_to_gr | Goodreads sync |

---

## Database Schema

**Database Version:** 44 (stored as `PRAGMA user_version`)

### Core Tables

#### authors
```sql
AuthorID        TEXT UNIQUE PRIMARY KEY
AuthorName      TEXT UNIQUE
AuthorImg       TEXT          -- Author image URL
AuthorLink      TEXT          -- Goodreads link
LastBookImg     TEXT          -- Most recent book cover
Status          TEXT          -- Active/Paused/Ignored
HaveBooks       INTEGER       -- Count of owned books
TotalBooks      INTEGER       -- Total known books
UnignoredBooks  INTEGER       -- Non-ignored count
Manual          INTEGER       -- User edited flag
GRfollow        INTEGER       -- Goodreads follow status
LastBookID      TEXT          -- Most recent book ID
```

#### books
```sql
BookID          TEXT UNIQUE PRIMARY KEY
AuthorID        TEXT FK → authors (CASCADE DELETE)
BookName        TEXT
BookSub         TEXT          -- Subtitle
BookDesc        TEXT          -- Description
BookGenre       TEXT
BookIsbn        TEXT
BookPub         TEXT          -- Publisher
BookRate        TEXT          -- Rating
BookPages       INTEGER
BookImg         TEXT          -- Cover image
BookFile        TEXT          -- File path
BookDate        TEXT          -- Publication date
BookLang        TEXT          -- Language code
Status          TEXT          -- Open/Wanted/Have/Skipped
Manual          INTEGER       -- User edited
SeriesDisplay   TEXT          -- Formatted series info
BookLibrary     TEXT          -- Import date
AudioFile       TEXT          -- Audiobook path
AudioStatus     TEXT          -- Audio status
WorkPage        TEXT          -- Goodreads work URL
WorkID          TEXT          -- Goodreads work ID
Requester       TEXT          -- User who requested
```

#### wanted
```sql
BookID          TEXT FK → books
NZBurl          TEXT          -- Download URL
NZBtitle        TEXT          -- Search result title
NZBdate         TEXT          -- Posted date
NZBprov         TEXT          -- Provider name
NZBsize         TEXT          -- File size
Status          TEXT          -- Snatched/Processed/Failed
Source          TEXT          -- Download client name
DownloadID      TEXT          -- Client tracking ID
DLResult        TEXT          -- Download result code
```

#### magazines
```sql
Title           TEXT UNIQUE PRIMARY KEY
Regex           TEXT          -- Match pattern
Status          TEXT          -- Active/Paused
IssueStatus     TEXT          -- Default issue status
MagazineAdded   TEXT
LastAcquired    TEXT
IssueDate       TEXT
LatestCover     TEXT          -- Cached cover path
DateType        TEXT          -- Date format type
CoverPage       INTEGER       -- Cover page number
```

#### series
```sql
SeriesID        INTEGER UNIQUE PRIMARY KEY
SeriesName      TEXT
Status          TEXT          -- Active/Ignored
Have            INTEGER       -- Owned count
Total           INTEGER       -- Total books
```

#### member (series membership)
```sql
SeriesID        INTEGER FK → series (CASCADE)
BookID          TEXT FK → books (CASCADE)
WorkID          TEXT
SeriesNum       TEXT          -- Position in series
```

#### users
```sql
UserID          TEXT UNIQUE PRIMARY KEY
UserName        TEXT UNIQUE
Password        TEXT          -- MD5 hashed
Email           TEXT
Perms           INTEGER       -- Permission bitmask
HaveRead        TEXT          -- Goodreads read list
ToRead          TEXT          -- Goodreads to-read list
BookType        TEXT          -- Preferred format
SendTo          TEXT          -- Email destination
```

### Other Tables
- **issues** - Magazine issues (FK → magazines)
- **seriesauthors** - Series-author relationships
- **sync** - Goodreads/Calibre sync state
- **isbn** - ISBN word index for searching
- **failedsearch** - Failed search tracking with retry
- **languages** - ISBN-language mapping
- **stats** - Metadata statistics
- **downloads** - Provider download counts
- **pastissues** - Historical magazine issues

---

## Configuration System

### Config File Format
INI format via `configparser`, stored in `config.ini`

### Key Configuration Sections

```ini
[General]
HTTP_PORT = 5299
HTTP_HOST = 0.0.0.0
HTTP_ROOT = /
HTTPS_ENABLED = 0
HTTP_LOOK = bookstrap          # UI theme: bookstrap/legacy
LAUNCH_BROWSER = 1
API_ENABLED = 1
USER_ACCOUNTS = 0
EBOOK_DIR = /path/to/ebooks
AUDIO_DIR = /path/to/audiobooks
DOWNLOAD_DIR = /path/to/downloads

[SearchScan]
SEARCH_BOOKINTERVAL = 360      # Hours between book searches
SEARCH_MAGINTERVAL = 360       # Hours between magazine searches
SCAN_INTERVAL = 10             # Hours between post-processing
SEARCHRSS_INTERVAL = 20        # Hours between RSS searches
WISHLIST_INTERVAL = 24         # Hours between wishlist checks
VERSIONCHECK_INTERVAL = 24     # Hours between update checks

[Quality]
MATCH_RATIO = 80               # Fuzzy matching threshold
DLOAD_RATIO = 90               # Download decision threshold
REJECT_WORDS = sample,xxx      # Words to reject
REJECT_MAXSIZE = 0             # Max file size (MB, 0=unlimited)
EBOOK_TYPE = epub,mobi,pdf     # Accepted ebook formats
AUDIOBOOK_TYPE = mp3,m4b       # Accepted audiobook formats

[API Keys]
GR_API =                       # Goodreads API key
GB_API =                       # Google Books API key
LT_DEVKEY =                    # LibraryThing developer key
```

### Configuration Categories

1. **CONFIG_GIT** - Git/update related settings
2. **CONFIG_NONWEB** - Internal settings not exposed in web UI
3. **CONFIG_NONDEFAULT** - Advanced features (OPDS, audiobooks, etc.)
4. **CONFIG_DEFINITIONS** - Main settings with type, section, default

### Configuration Access
```python
import lazylibrarian

# Read config value
value = lazylibrarian.CONFIG['HTTP_PORT']

# Write config value
lazylibrarian.CONFIG['HTTP_PORT'] = 8080
lazylibrarian.config_write('General')
```

---

## Web Interface

### URL Routes (WebInterface class in webServe.py)

| Route | Handler | Purpose |
|-------|---------|---------|
| `/` | index() | Dashboard |
| `/config` | config() | Settings page |
| `/authors` | authors() | Author list |
| `/author/<id>` | authorPage() | Author details |
| `/books` | books() | Book list |
| `/book/<id>` | bookPage() | Book details |
| `/magazines` | magazines() | Magazine list |
| `/issues/<title>` | issues() | Magazine issues |
| `/series` | series() | Series list |
| `/members/<id>` | members() | Series members |
| `/audio` | audio() | Audiobooks |
| `/logs` | logs() | Log viewer |
| `/history` | history() | Download history |
| `/search/<type>` | search() | Manual search |
| `/api` | api() | REST API endpoint |
| `/opds/*` | OPDS class | OPDS catalog |

### Template System
- **Engine:** Mako
- **Location:** `data/interfaces/bookstrap/` (modern) or `data/interfaces/legacy/`
- **Selection:** `HTTP_LOOK` config parameter
- **Features:** Permission checking, caching, auto-reload in debug mode

### Authentication
- HTTP Basic Auth (HTTP_USER, HTTP_PASS)
- User accounts with granular permissions
- Cookie-based sessions (ll_uid cookie)

### Permission System

```python
perm_config     = 1      # Access config page
perm_logs       = 2      # Access logs
perm_history    = 4      # Access history
perm_managebooks = 8     # Access manage page
perm_magazines  = 16     # Access magazines
perm_audio      = 32     # Access audiobooks
perm_ebook      = 64     # Access ebooks
perm_series     = 128    # Access series
perm_edit       = 256    # Edit book/author details
perm_search     = 512    # Search Goodreads/Google
perm_status     = 1024   # Change book status
perm_force      = 2048   # Run background tasks
perm_download   = 4096   # Download files

perm_guest  = 4320       # Basic read access
perm_friend = 5856       # Guest + search/status
perm_admin  = 65535      # Full access
```

---

## REST API

### Endpoint
`/api?cmd=<command>&<parameters>`

### Authentication
- API key via `apikey` parameter or HTTP Basic Auth

### Common Commands

#### Authors
| Command | Parameters | Description |
|---------|------------|-------------|
| getIndex | | List all authors |
| getAuthor | id | Author details |
| pauseAuthor | id | Pause author |
| resumeAuthor | id | Resume author |
| ignoreAuthor | id | Ignore author |
| refreshAuthor | id | Refresh metadata |

#### Books
| Command | Parameters | Description |
|---------|------------|-------------|
| getWanted | | List wanted books |
| getSnatched | | List snatched books |
| getRead | | List read books |
| forceBookSearch | | Trigger book search |
| queueBook | id | Queue book download |

#### Magazines
| Command | Parameters | Description |
|---------|------------|-------------|
| getMagazines | | List magazines |
| getIssues | name | List issues |
| forceMagSearch | | Trigger magazine search |

#### System
| Command | Parameters | Description |
|---------|------------|-------------|
| getLogs | | Get log entries |
| clearLogs | | Clear logs |
| getDebug | | Debug info |
| forceLibraryScan | | Scan library |
| forceProcess | | Run post-processor |
| shutdown | | Shutdown server |
| restart | | Restart server |

---

## External Integrations

### Metadata Sources

| Source | Module | Purpose |
|--------|--------|---------|
| Goodreads | gr.py | Primary author/book/series data |
| Google Books | gb.py | Secondary book data |
| LibraryThing | (in common.py) | Language detection |
| Open Library | (fallback) | Fallback metadata |

### Download Providers

#### Torrent Trackers
- **TPB** (The Pirate Bay) - torrentparser.py
- **KAT** (KickAss Torrents) - torrentparser.py
- **WWT** (WorldWideTorrents) - torrentparser.py
- **ZOO** (Zooqle) - torrentparser.py
- **LIME** (LimeTorrents) - torrentparser.py
- **TDL** (TorrentDownloads) - torrentparser.py

#### Direct Sources
- **LibGen** (GEN, GEN2) - directparser.py

#### NZB Indexers
- Newznab/Torznab protocol (configurable)
- Custom RSS feeds

### Download Clients

#### Usenet
| Client | Module | Config Prefix |
|--------|--------|---------------|
| SABnzbd | sabnzbd.py | SAB_ |
| NZBGet | nzbget.py | NZBGET_ |
| Synology | synology.py | SYNOLOGY_NZB_ |

#### Torrent
| Client | Module | Config Prefix |
|--------|--------|---------------|
| qBittorrent | qbittorrent.py | QBITTORRENT_ |
| rTorrent | rtorrent.py | RTORRENT_ |
| uTorrent | utorrent.py | UTORRENT_ |
| Transmission | transmission.py | TRANSMISSION_ |
| Deluge | deluge.py | DELUGE_ |
| Synology | synology.py | SYNOLOGY_TOR_ |

#### Blackhole
Drop files to filesystem folder (fallback method)

### Library Integration
- **Calibre** - calibre.py - Format conversion, metadata sync

### Notification Services (notifiers/)

| Service | Module | Config Prefix |
|---------|--------|---------------|
| Email | email_notify.py | EMAIL_ |
| Twitter | tweet.py | TWITTER_ |
| Pushbullet | pushbullet.py | PUSHBULLET_ |
| Pushover | pushover.py | PUSHOVER_ |
| Telegram | telegram.py | TELEGRAM_ |
| Slack | slack.py | SLACK_ |
| Boxcar | boxcar.py | BOXCAR_ |
| Prowl | prowl.py | PROWL_ |
| Growl | growl.py | GROWL_ |
| NMA | nma.py | NMA_ |
| AndroidPN | androidpn.py | ANDROIDPN_ |
| Custom | custom_notify.py | CUSTOM_ |

---

## Background Tasks

### Scheduled Jobs (APScheduler)

| Job Name | Function | Default Interval | Module |
|----------|----------|------------------|--------|
| search_book | Search for wanted books | 360 hours | searchbook.py |
| search_magazine | Search for magazines | 360 hours | searchmag.py |
| search_rss_book | Search RSS feeds | 20 hours | searchrss.py |
| search_wishlist | Search Goodreads wishlists | 24 hours | searchrss.py |
| PostProcessor | Post-process downloads | 10 hours | postprocess.py |
| checkForUpdates | Check for updates | 24 hours | versioncheck.py |
| sync_to_gr | Sync to Goodreads | 48 hours | grsync.py |

### Job Management
```python
from lazylibrarian.common import scheduleJob

# Schedule or restart a job
scheduleJob(action='Start', target='search_book')
scheduleJob(action='Restart', target='PostProcessor')
```

---

## Post-Processing Pipeline

Located in [postprocess.py](lazylibrarian/postprocess.py)

### Process Flow

```
Download Complete
    │
    ├── File format detection (EBOOK_TYPE, AUDIOBOOK_TYPE)
    ├── Metadata extraction
    │   ├── OPF files
    │   ├── ID3 tags (audio)
    │   └── Filename parsing
    │
    ├── Book identification
    │   ├── ISBN lookup
    │   ├── Title/author matching
    │   └── Fuzzy matching (FuzzyWuzzy)
    │
    ├── File organization
    │   ├── Apply EBOOK_DEST_FOLDER template
    │   ├── Rename files per EBOOK_DEST_FILE
    │   └── Set permissions (DIR_PERM, FILE_PERM)
    │
    ├── Cover extraction
    │   └── Cache to CACHEDIR
    │
    ├── Database update
    │   ├── Set BookFile/AudioFile path
    │   ├── Update Status → 'Open'
    │   └── Update BookLibrary date
    │
    ├── Optional Calibre sync
    │
    └── Notification dispatch
```

### Filename Templates

```
$Author     → Author name
$Title      → Book title
$Series     → Series name
$SeriesNum  → Series number
$Year       → Publication year
$ISBN       → ISBN number
```

---

## OPDS Catalog

Located in [opds.py](lazylibrarian/opds.py)

### Endpoints
| Path | Description |
|------|-------------|
| `/opds` | Root catalog |
| `/opds/Authors` | Browse by author |
| `/opds/Magazines` | Browse magazines |
| `/opds/Series` | Browse by series |
| `/opds/search` | Search interface |

### Features
- OPDS 1.2 compatible
- Optional authentication (OPDS_AUTHENTICATION)
- Direct file downloads
- Search functionality

---

## Logging System

Located in [logger.py](lazylibrarian/logger.py)

### Configuration
```ini
LOGDIR = /path/to/logs
LOGSIZE = 204800           # Max size in bytes (default 200KB)
LOGFILES = 10              # Number of backup files
LOGLEVEL = 1               # 1=INFO, 2=DEBUG
```

### Extended Debug Flags (bitwise)
```python
log_magdates    = 4        # Magazine date matching
log_searchmag   = 8        # Search logging
log_dlcomms     = 16       # Download communication
log_dbcomms     = 32       # Database operations
log_postprocess = 64       # Post-processing details
log_fuzz        = 128      # Fuzzy matching
log_serverside  = 256      # Server processing
log_fileperms   = 512      # File permissions
log_grsync      = 1024     # Goodreads sync
log_cache       = 2048     # Cache operations
log_libsync     = 4096     # Library sync
log_admin       = 8192     # Admin operations
```

---

## Key Design Patterns

1. **Global Configuration Pattern** - Centralized `lazylibrarian.CONFIG` dictionary
2. **Database Abstraction** - `DBConnection` class with thread-safe locking
3. **Adapter/Provider Pattern** - Pluggable search providers in providers.py
4. **Factory Pattern** - `NZBDownloadMethod()`, `TORDownloadMethod()` dispatch
5. **Scheduler/Job Pattern** - APScheduler for cron-like execution
6. **Template Method** - Post-processing pipeline with format detection
7. **Observer Pattern** - Notification system with multiple backends
8. **State Machine** - Book/author status transitions

---

## Development Guidelines

### Running the Application
```bash
# Standard run
python LazyLibrarian.py

# With debug logging
python LazyLibrarian.py --debug

# As daemon (Linux/Mac)
python LazyLibrarian.py -d

# Custom port and data directory
python LazyLibrarian.py --port 8080 --datadir /custom/path
```

### Database Access
```python
from lazylibrarian import database

myDB = database.DBConnection()

# Single row query
result = myDB.match('SELECT * FROM authors WHERE AuthorID=?', [author_id])

# Multiple rows
results = myDB.select('SELECT * FROM books WHERE Status=?', ['Wanted'])

# Insert/Update
myDB.action('UPDATE books SET Status=? WHERE BookID=?', ['Open', book_id])

# Upsert (INSERT OR REPLACE)
myDB.upsert('authors', {'AuthorName': name}, {'AuthorID': id})
```

### Adding a New Provider
1. Create parser in `torrentparser.py` or `directparser.py`
2. Add provider config in `__init__.py` CONFIG_DEFINITIONS
3. Add toggle in `providers.py` test_provider()
4. Add UI controls in `data/interfaces/bookstrap/config.html`

### Adding a Notification Service
1. Create module in `lazylibrarian/notifiers/`
2. Implement `notify_snatch()` and `notify_download()`
3. Add config parameters to `__init__.py`
4. Register in `notifiers/__init__.py`

---

## Testing

Unit tests are located in `lazylibrarian/unittests/`

```bash
# Run tests (from project root)
python -m pytest lazylibrarian/unittests/
```

See [UNITTESTING.md](UNITTESTING.md) for details.

---

## Version History

- **Database Schema:** v44 (current)
- **Branch:** master
- Auto-updates from GitLab repository

---

## Resources

- **Source Code:** https://gitlab.com/LazyLibrarian/LazyLibrarian
- **Documentation:** https://lazylibrarian.gitlab.io/
- **Community:** Reddit r/LazyLibrarian
- **Issues:** GitLab Issues
