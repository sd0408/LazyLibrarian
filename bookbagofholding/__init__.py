#  This file is part of Bookbag of Holding.
#  Bookbag of Holding is free software':'you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

import calendar
import json
import locale
import os
import platform
import subprocess
import sys
import threading
import time
import webbrowser
import sqlite3

import cherrypy
from bookbagofholding import logger, database, postprocess, searchbook, searchrss, \
    importer, webServe
from bookbagofholding.cache import fetchURL
from bookbagofholding.common import restartJobs, logHeader, scheduleJob
from bookbagofholding.formatter import getList, plural, unaccented, check_int, unaccented_str, makeUnicode
from bookbagofholding.dbupgrade import check_db
from apscheduler.schedulers.background import BackgroundScheduler
import configparser

# Transient globals NOT stored in config
# These are used/modified by Bookbag of Holding.py before config.ini is read
FULL_PATH = None
PROG_DIR = None
ARGS = None
DAEMON = False
SIGNAL = None
PIDFILE = ''
DATADIR = ''
CONFIGFILE = ''
SYS_ENCODING = ''
LOGLEVEL = 1
CONFIG = {}
CFG = ''
DBFILE = None
COMMIT_LIST = None
SHOWLOGOUT = 1
CHERRYPYLOG = 0

# These are only used in startup
SCHED = None
INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
started = False

# Transients used by logger process
LOGLIST = []
LOGTOGGLE = 2  # normal debug

# These are globals
UPDATE_MSG = ''
NO_TOR_MSG = 0
NO_RSS_MSG = 0
NO_NZB_MSG = 0
NO_DIRECT_MSG = 0
IGNORED_AUTHORS = 0
CURRENT_TAB = '1'
CACHE_HIT = 0
CACHE_MISS = 0
LAST_LIBRARYTHING = 0
LT_SLEEP = 0.0
GB_CALLS = 0
MONTHNAMES = []
CACHEDIR = ''
NEWZNAB_PROV = []
TORZNAB_PROV = []
NABAPICOUNT = ''
RSS_PROV = []
BOOKSTRAP_THEMELIST = []
PROVIDER_BLOCKLIST = []
USER_BLOCKLIST = []
SHOW_AUDIO = 0
EBOOK_UPDATE = 0
AUDIO_UPDATE = 0
AUTHORS_UPDATE = 0
POSTPROCESS_UPDATE = 0
LOGIN_MSG = ''
GROUP_CONCAT = 0
HIST_REFRESH = 1000

# extended loglevels
log_dlcomms = 1 << 4  # 16 detailed downloader communication
log_dbcomms = 1 << 5  # 32 database comms
log_postprocess = 1 << 6  # 64 detailed postprocessing
log_fuzz = 1 << 7  # 128 fuzzy logic
log_serverside = 1 << 8  # 256 serverside processing
log_fileperms = 1 << 9  # 512 changes to file permissions
# log_grsync = 1 << 10  # 1024 (removed - goodreads sync deprecated)
log_cache = 1 << 11  # 2048 cache results
log_libsync = 1 << 12  # 4096 librarysync details
log_admin = 1 << 13  # 8192 admin logging

# user permissions
perm_config = 1 << 0  # 1 access to config page
perm_logs = 1 << 1  # 2 access to logs
perm_history = 1 << 2  # 4 access to history
perm_managebooks = 1 << 3  # 8 access to manage page
perm_audio = 1 << 5  # 32 access to audiobooks page
perm_ebook = 1 << 6  # 64 can access ebooks page
perm_edit = 1 << 8  # 256 can edit book or author details
perm_search = 1 << 9  # 512 can search goodreads/googlebooks for books/authors
perm_status = 1 << 10  # 1024 can change book status (wanted/skipped etc)
perm_force = 1 << 11  # 2048 can use background tasks (refresh authors/libraryscan/postprocess/searchtasks)
perm_download = 1 << 12  # 4096 can download existing books/mags

perm_authorbooks = perm_audio + perm_ebook
perm_guest = perm_download + perm_authorbooks
perm_friend = perm_guest + perm_search + perm_status
perm_admin = 65535

# Shared dictionaries
isbn_979_dict = {
    "10": "fre",
    "11": "kor",
    "12": "ita"
}
isbn_978_dict = {
    "0": "eng",
    "1": "eng",
    "2": "fre",
    "3": "ger",
    "4": "jap",
    "5": "rus",
    "7": "chi",
    "80": "cze",
    "82": "pol",
    "83": "nor",
    "84": "spa",
    "85": "bra",
    "87": "den",
    "88": "ita",
    "89": "kor",
    "91": "swe",
    "93": "ind"
}
# These are the items in config.ini
# Not all are accessible from the web ui
# Any undefined on startup will be set to the default value
# Any _NOT_ in the web ui will remain unchanged on config save
# CONFIG_GIT was used for version checking - now empty since auto-update was removed
CONFIG_GIT = []
CONFIG_NONWEB = ['NAME_POSTFIX', 'DIR_PERM', 'FILE_PERM', 'BLOCKLIST_TIMER', 'DISPLAYLENGTH', 'ISBN_LOOKUP',
                 'WALL_COLUMNS', 'ADMIN_EMAIL', 'HTTP_TIMEOUT', 'PROXY_LOCAL', 'SKIPPED_EXT', 'CHERRYPYLOG',
                 'SYS_ENCODING', 'HIST_REFRESH', 'HTTP_EXT_TIMEOUT', 'CALIBRE_RENAME',
                 'NAME_RATIO', 'NAME_PARTIAL', 'NAME_PARTNAME', 'USER_AGENT']
# default interface does not know about these items, so leaves them unchanged
CONFIG_NONDEFAULT = ['BOOKSTRAP_THEME', 'AUDIOBOOK_TYPE', 'AUDIO_DIR', 'AUDIO_TAB', 'REJECT_AUDIO',
                     'REJECT_MAXAUDIO', 'REJECT_MINAUDIO', 'NEWAUDIO_STATUS', 'TOGGLES', 'FOUND_STATUS',
                     'AUTH_METHOD', 'AUTH_USERNAME', 'AUTH_PASSWORD', 'AUTH_HEADER', 'AUDIOBOOK_DEST_FILE',
                     'TRANSMISSION_DIR', 'DELUGE_DIR', 'QBITTORRENT_DIR',
                     'BANNED_EXT', 'LOGFILES', 'LOGSIZE', 'DATE_FORMAT',
                     'NO_ISBN', 'NO_SETS', 'NO_LANG', 'NO_PUBDATE', 'IMP_IGNORE', 'IMP_GOOGLEIMAGE', 'DELETE_CSV',
                     'BLACKLIST_FAILED', 'BLACKLIST_PROCESSED', 'WISHLIST_INTERVAL', 'IMP_PREPROCESS',
                     'OPDS_ENABLED', 'OPDS_AUTHENTICATION', 'OPDS_USERNAME', 'OPDS_PASSWORD', 'OPDS_METAINFO',
                     'OPDS_PAGE', 'DELAYSEARCH', 'SEED_WAIT']

CONFIG_DEFINITIONS = {
    # Name      Type   Section   Default
    # Authentication - Radarr-style simple auth
    # AUTH_METHOD: None (disabled), Forms (login page), Basic (HTTP Basic), External (proxy headers)
    'AUTH_METHOD': ('str', 'General', 'None'),
    'AUTH_USERNAME': ('str', 'General', ''),
    'AUTH_PASSWORD': ('str', 'General', ''),  # Hashed password
    'AUTH_HEADER': ('str', 'General', 'X-Forwarded-User'),  # Header for external auth
    'ADMIN_EMAIL': ('str', 'General', ''),
    'USER_ACCOUNTS': ('bool', 'General', 0),  # Enable multi-user accounts
    'SYS_ENCODING': ('str', 'General', ''),
    'LOGDIR': ('str', 'General', ''),
    'LOGLIMIT': ('int', 'General', 500),
    'LOGFILES': ('int', 'General', 10),
    'LOGSIZE': ('int', 'General', 204800),
    'LOGLEVEL': ('int', 'General', 1),
    'WALL_COLUMNS': ('int', 'General', 6),
    'FILE_PERM': ('str', 'General', '0o644'),
    'DIR_PERM': ('str', 'General', '0o755'),
    'BLOCKLIST_TIMER': ('int', 'General', 3600),
    'MAX_PAGES': ('int', 'General', 0),
    'MAX_BOOKPAGES': ('int', 'General', 0),
    'MAX_WALL': ('int', 'General', 0),
    'MATCH_RATIO': ('int', 'General', 80),
    'DLOAD_RATIO': ('int', 'General', 90),
    'NAME_RATIO': ('int', 'General', 90),
    'NAME_PARTIAL': ('int', 'General', 95),
    'NAME_PARTNAME': ('int', 'General', 95),
    'DISPLAYLENGTH': ('int', 'General', 10),
    'HIST_REFRESH': ('int', 'General', 1000),
    'HTTP_PORT': ('int', 'General', 5299),
    'HTTP_HOST': ('str', 'General', '0.0.0.0'),
    'HTTP_USER': ('str', 'General', ''),
    'HTTP_PASS': ('str', 'General', ''),
    'HTTP_PROXY': ('bool', 'General', 0),
    'HTTP_ROOT': ('str', 'General', ''),
    'HTTPS_ENABLED': ('bool', 'General', 0),
    'HTTPS_CERT': ('str', 'General', ''),
    'HTTPS_KEY': ('str', 'General', ''),
    'SSL_VERIFY': ('bool', 'General', 0),
    'HTTP_TIMEOUT': ('int', 'General', 30),
    'HTTP_EXT_TIMEOUT': ('int', 'General', 90),
    'AUTHOR_IMG': ('bool', 'General', 1),
    'BOOK_IMG': ('bool', 'General', 1),
    'AUDIO_TAB': ('bool', 'General', 1),
    'TOGGLES': ('bool', 'General', 1),
    'SORT_DEFINITE': ('bool', 'General', 0),
    'SORT_SURNAME': ('bool', 'General', 0),
    'LAUNCH_BROWSER': ('bool', 'General', 1),
    'API_ENABLED': ('bool', 'General', 0),
    'API_KEY': ('str', 'General', ''),
    'PROXY_HOST': ('str', 'General', ''),
    'PROXY_TYPE': ('str', 'General', ''),
    'PROXY_LOCAL': ('str', 'General', ''),
    'NAME_POSTFIX': ('str', 'General', 'snr, jnr, jr, sr, phd'),
    'SKIPPED_EXT': ('str', 'General', 'fail, part, bts, !ut, torrent, magnet, nzb, unpack'),
    'BANNED_EXT': ('str', 'General', 'avi, mp4, mov, iso, m4v'),
    'IMP_PREFLANG': ('str', 'General', 'en, eng, en-US, en-GB'),
    'DATE_FORMAT': ('str', 'General', '$Y-$m-$d'),
    'IMP_MONTHLANG': ('str', 'General', ''),
    'IMP_AUTOADD': ('str', 'General', ''),
    'IMP_AUTOADD_COPY': ('bool', 'General', 1),
    'IMP_AUTOADD_BOOKONLY': ('bool', 'General', 0),
    'IMP_AUTOSEARCH': ('bool', 'General', 0),
    'IMP_CALIBREDB': ('str', 'General', ''),
    'BLACKLIST_FAILED': ('bool', 'General', 1),
    'BLACKLIST_PROCESSED': ('bool', 'General', 0),
    'CALIBRE_USE_SERVER': ('bool', 'General', 0),
    'CALIBRE_SERVER': ('str', 'General', ''),
    'CALIBRE_USER': ('str', 'General', ''),
    'CALIBRE_PASS': ('str', 'General', ''),
    'CALIBRE_RENAME': ('bool', 'General', 0),
    'IMP_SINGLEBOOK': ('bool', 'General', 0),
    'IMP_RENAME': ('bool', 'General', 0),
    'IMP_CONVERT': ('str', 'General', ''),
    'IMP_PREPROCESS': ('str', 'General', ''),
    'CACHE_AGE': ('int', 'General', 30),
    'TASK_AGE': ('int', 'General', 2),
    'OPF_TAGS': ('bool', 'General', 1),
    'WISHLIST_TAGS': ('bool', 'General', 1),
    'SAB_HOST': ('str', 'SABnzbd', ''),
    'SAB_PORT': ('int', 'SABnzbd', 0),
    'SAB_SUBDIR': ('str', 'SABnzbd', ''),
    'SAB_USER': ('str', 'SABnzbd', ''),
    'SAB_PASS': ('str', 'SABnzbd', ''),
    'SAB_API': ('str', 'SABnzbd', ''),
    'SAB_CAT': ('str', 'SABnzbd', ''),
    'NZBGET_HOST': ('str', 'NZBGet', ''),
    'NZBGET_PORT': ('int', 'NZBGet', '0'),
    'NZBGET_USER': ('str', 'NZBGet', ''),
    'NZBGET_PASS': ('str', 'NZBGet', ''),
    'NZBGET_CATEGORY': ('str', 'NZBGet', ''),
    'NZBGET_PRIORITY': ('int', 'NZBGet', '0'),
    'DESTINATION_COPY': ('bool', 'General', 0),
    'EBOOK_DIR': ('str', 'General', ''),
    'AUDIO_DIR': ('str', 'General', ''),
    'ALTERNATE_DIR': ('str', 'General', ''),
    'DELETE_CSV': ('bool', 'General', 0),
    'DOWNLOAD_DIR': ('str', 'General', ''),
    'NZB_DOWNLOADER_SABNZBD': ('bool', 'USENET', 0),
    'NZB_DOWNLOADER_NZBGET': ('bool', 'USENET', 0),
    'NZB_DOWNLOADER_SYNOLOGY': ('bool', 'USENET', 0),
    'NZB_DOWNLOADER_BLACKHOLE': ('bool', 'USENET', 0),
    'NZB_BLACKHOLEDIR': ('str', 'USENET', ''),
    'USENET_RETENTION': ('int', 'USENET', 0),
    'NZBMATRIX_USER': ('str', 'NZBMatrix', ''),
    'NZBMATRIX_API': ('str', 'NZBMatrix', ''),
    'NZBMATRIX': ('bool', 'NZBMatrix', 0),
    'TOR_DOWNLOADER_BLACKHOLE': ('bool', 'TORRENT', 0),
    'TOR_CONVERT_MAGNET': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_UTORRENT': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_RTORRENT': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_QBITTORRENT': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_TRANSMISSION': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_SYNOLOGY': ('bool', 'TORRENT', 0),
    'TOR_DOWNLOADER_DELUGE': ('bool', 'TORRENT', 0),
    'NUMBEROFSEEDERS': ('int', 'TORRENT', 10),
    'KEEP_SEEDING': ('bool', 'TORRENT', 1),
    'SEED_WAIT': ('bool', 'TORRENT', 1),
    'PREFER_MAGNET': ('bool', 'TORRENT', 1),
    'TORRENT_DIR': ('str', 'TORRENT', ''),
    'RTORRENT_HOST': ('str', 'RTORRENT', ''),
    'RTORRENT_USER': ('str', 'RTORRENT', ''),
    'RTORRENT_PASS': ('str', 'RTORRENT', ''),
    'RTORRENT_LABEL': ('str', 'RTORRENT', ''),
    'RTORRENT_DIR': ('str', 'RTORRENT', ''),
    'UTORRENT_HOST': ('str', 'UTORRENT', ''),
    'UTORRENT_PORT': ('int', 'UTORRENT', 0),
    'UTORRENT_USER': ('str', 'UTORRENT', ''),
    'UTORRENT_PASS': ('str', 'UTORRENT', ''),
    'UTORRENT_LABEL': ('str', 'UTORRENT', ''),
    'QBITTORRENT_HOST': ('str', 'QBITTORRENT', ''),
    'QBITTORRENT_PORT': ('int', 'QBITTORRENT', 0),
    'QBITTORRENT_USER': ('str', 'QBITTORRENT', ''),
    'QBITTORRENT_PASS': ('str', 'QBITTORRENT', ''),
    'QBITTORRENT_LABEL': ('str', 'QBITTORRENT', ''),
    'QBITTORRENT_DIR': ('str', 'QBITTORRENT', ''),
    'TRANSMISSION_HOST': ('str', 'TRANSMISSION', ''),
    'TRANSMISSION_BASE': ('str', 'TRANSMISSION', ''),
    'TRANSMISSION_PORT': ('int', 'TRANSMISSION', 0),
    'TRANSMISSION_USER': ('str', 'TRANSMISSION', ''),
    'TRANSMISSION_PASS': ('str', 'TRANSMISSION', ''),
    'TRANSMISSION_DIR': ('str', 'TRANSMISSION', ''),
    'DELUGE_CERT': ('str', 'DELUGE', ''),
    'DELUGE_HOST': ('str', 'DELUGE', ''),
    'DELUGE_BASE': ('str', 'DELUGE', ''),
    'DELUGE_PORT': ('int', 'DELUGE', 0),
    'DELUGE_USER': ('str', 'DELUGE', ''),
    'DELUGE_PASS': ('str', 'DELUGE', ''),
    'DELUGE_LABEL': ('str', 'DELUGE', ''),
    'DELUGE_DIR': ('str', 'DELUGE', ''),
    'SYNOLOGY_HOST': ('str', 'SYNOLOGY', ''),
    'SYNOLOGY_PORT': ('int', 'SYNOLOGY', 0),
    'SYNOLOGY_USER': ('str', 'SYNOLOGY', ''),
    'SYNOLOGY_PASS': ('str', 'SYNOLOGY', ''),
    'SYNOLOGY_DIR': ('str', 'SYNOLOGY', 'Multimedia/Download'),
    'USE_SYNOLOGY': ('bool', 'SYNOLOGY', 0),
    'KAT_HOST': ('str', 'KAT', 'kickass.cd'),
    'KAT': ('bool', 'KAT', 0),
    'KAT_DLPRIORITY': ('int', 'KAT', 0),
    'KAT_DLTYPES': ('str', 'KAT', 'A,E,M'),
    'WWT_HOST': ('str', 'WWT', 'https://worldwidetorrents.me'),
    'WWT': ('bool', 'WWT', 0),
    'WWT_DLPRIORITY': ('int', 'WWT', 0),
    'WWT_DLTYPES': ('str', 'WWT', 'A,E,M'),
    'TPB_HOST': ('str', 'TPB', 'https://pirateproxy.cc'),
    'TPB': ('bool', 'TPB', 0),
    'TPB_DLPRIORITY': ('int', 'TPB', 0),
    'TPB_DLTYPES': ('str', 'TPB', 'A,E,M'),
    'ZOO_HOST': ('str', 'ZOO', 'https://zooqle.com'),
    'ZOO': ('bool', 'ZOO', 0),
    'ZOO_DLPRIORITY': ('int', 'ZOO', 0),
    'ZOO_DLTYPES': ('str', 'ZOO', 'A,E,M'),
    # 'EXTRA_HOST': ('str', 'EXTRA', 'extratorrent.cc'),
    # 'EXTRA': ('bool', 'EXTRA', 0),
    # 'EXTRA_DLPRIORITY': ('int', 'EXTRA', 0),
    'TDL_HOST': ('str', 'TDL', 'torrentdownloads.me'),
    'TDL': ('bool', 'TDL', 0),
    'TDL_DLPRIORITY': ('int', 'TDL', 0),
    'TDL_DLTYPES': ('str', 'TDL', 'A,E,M'),
    'GEN_HOST': ('str', 'GEN', 'libgen.io'),
    'GEN_SEARCH': ('str', 'GEN', 'search.php'),
    'GEN': ('bool', 'GEN', 0),
    'GEN_DLPRIORITY': ('int', 'GEN', 0),
    'GEN_DLTYPES': ('str', 'GEN', 'EM'),
    'GEN2_HOST': ('str', 'GEN', 'libgen.io'),
    'GEN2_SEARCH': ('str', 'GEN', 'foreignfiction/index.php'),
    'GEN2': ('bool', 'GEN', 0),
    'GEN2_DLPRIORITY': ('int', 'GEN', 0),
    'GEN2_DLTYPES': ('str', 'GEN2', 'EM'),
    'LIME_HOST': ('str', 'LIME', 'https://www.limetorrents.cc'),
    'LIME': ('bool', 'LIME', 0),
    'LIME_DLPRIORITY': ('int', 'LIME', 0),
    'LIME_DLTYPES': ('str', 'LIME', 'A,E,M'),
    'NEWZBIN_UID': ('str', 'Newzbin', ''),
    'NEWZBIN_PASS': ('str', 'Newzbin', ''),
    'NEWZBIN': ('bool', 'Newzbin', 0),
    'EBOOK_TYPE': ('str', 'General', 'epub, mobi, pdf'),
    'AUDIOBOOK_TYPE': ('str', 'General', 'mp3'),
    'REJECT_WORDS': ('str', 'General', 'audiobook, mp3'),
    'REJECT_AUDIO': ('str', 'General', 'epub, mobi'),
    'REJECT_MAXSIZE': ('int', 'General', 0),
    'REJECT_MINSIZE': ('int', 'General', 0),
    'REJECT_MAXAUDIO': ('int', 'General', 0),
    'REJECT_MINAUDIO': ('int', 'General', 0),
    'SEARCH_BOOKINTERVAL': ('int', 'SearchScan', '360'),
    'SCAN_INTERVAL': ('int', 'SearchScan', '10'),
    'SEARCHRSS_INTERVAL': ('int', 'SearchScan', '20'),
    'WISHLIST_INTERVAL': ('int', 'SearchScan', '24'),
    'DELAYSEARCH': ('bool', 'SearchScan', 0),
    'FULL_SCAN': ('bool', 'LibraryScan', 0),
    'ADD_AUTHOR': ('bool', 'LibraryScan', 1),
    'NOTFOUND_STATUS': ('str', 'LibraryScan', 'Skipped'),
    'FOUND_STATUS': ('str', 'LibraryScan', 'Open'),
    'NEWBOOK_STATUS': ('str', 'LibraryScan', 'Skipped'),
    'NEWAUDIO_STATUS': ('str', 'LibraryScan', 'Skipped'),
    'NEWAUTHOR_STATUS': ('str', 'LibraryScan', 'Skipped'),
    'NEWAUTHOR_AUDIO': ('str', 'LibraryScan', 'Skipped'),
    'NEWAUTHOR_BOOKS': ('bool', 'LibraryScan', 0),
    'NO_FUTURE': ('bool', 'LibraryScan', 0),
    'NO_PUBDATE': ('bool', 'LibraryScan', 0),
    'NO_ISBN': ('bool', 'LibraryScan', 0),
    'NO_SETS': ('bool', 'LibraryScan', 0),
    'NO_LANG': ('bool', 'LibraryScan', 0),
    'ISBN_LOOKUP': ('bool', 'LibraryScan', 1),
    'IMP_IGNORE': ('bool', 'LibraryScan', 0),
    'IMP_GOOGLEIMAGE': ('bool', 'LibraryScan', 0),
    'EBOOK_DEST_FOLDER': ('str', 'PostProcess', '$Author/$Title'),
    'EBOOK_DEST_FILE': ('str', 'PostProcess', '$Title - $Author'),
    'AUDIOBOOK_DEST_FILE': ('str', 'PostProcess', '$Author - $Title Part $Part of $Total'),
    'ONE_FORMAT': ('bool', 'PostProcess', 0),
    'BOOK_API': ('str', 'API', 'GoogleBooks'),
    'LT_DEVKEY': ('str', 'API', ''),
    'GB_API': ('str', 'API', ''),  # API key has daily limits, each user needs their own
    'GB_COUNTRY': ('str', 'API', ''),  # optional two letter country code for geographically restricted results
    'OPDS_ENABLED': ('bool', 'OPDS', 0),
    'OPDS_AUTHENTICATION': ('bool', 'OPDS', 0),
    'OPDS_USERNAME': ('str', 'OPDS', ''),
    'OPDS_PASSWORD': ('str', 'OPDS', ''),
    'OPDS_METAINFO': ('bool', 'OPDS', 0),
    'OPDS_PAGE': ('int', 'OPDS', 30),
    'USER_AGENT': ('str', 'General', ''),
    # 'USER_AGENT': ('str', 'General',
    # 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'),
}


def check_section(sec):
    """ Check if INI section exists, if not create it """
    # noinspection PyUnresolvedReferences
    if CFG.has_section(sec):
        return True
    else:
        # noinspection PyUnresolvedReferences
        CFG.add_section(sec)
        return False


def check_setting(cfg_type, cfg_name, item_name, def_val, log=True):
    """ Check option exists, coerce to correct type, or return default"""
    my_val = def_val
    if cfg_type == 'int':
        try:
            # noinspection PyUnresolvedReferences
            my_val = CFG.getint(cfg_name, item_name)
        except configparser.Error:
            # no such item, might be a new entry
            my_val = int(def_val)
        except Exception as e:
            logger.warn('Invalid int for %s: %s, using default %s' % (cfg_name, item_name, int(def_val)))
            logger.debug(str(e))
            my_val = int(def_val)

    elif cfg_type == 'bool':
        try:
            # noinspection PyUnresolvedReferences
            my_val = CFG.getboolean(cfg_name, item_name)
        except configparser.Error:
            my_val = bool(def_val)
        except Exception as e:
            logger.warn('Invalid bool for %s: %s, using default %s' % (cfg_name, item_name, bool(def_val)))
            logger.debug(str(e))
            my_val = bool(def_val)

    elif cfg_type == 'str':
        try:
            # noinspection PyUnresolvedReferences
            my_val = CFG.get(cfg_name, item_name)
            # Old config file format had strings in quotes. ConfigParser doesn't.
            if my_val.startswith('"') and my_val.endswith('"'):
                my_val = my_val[1:-1]
            if not len(my_val):
                my_val = def_val
        except configparser.Error:
            my_val = str(def_val)
        except Exception as e:
            logger.warn('Invalid str for %s: %s, using default %s' % (cfg_name, item_name, str(def_val)))
            logger.debug(str(e))
            my_val = str(def_val)
        finally:
            my_val = makeUnicode(my_val)

    check_section(cfg_name)
    # noinspection PyUnresolvedReferences
    CFG.set(cfg_name, item_name, my_val)
    if log:
        logger.debug("%s : %s -> %s" % (cfg_name, item_name, my_val))

    return my_val


def initialize():
    global FULL_PATH, PROG_DIR, ARGS, DAEMON, SIGNAL, PIDFILE, DATADIR, CONFIGFILE, SYS_ENCODING, LOGLEVEL, \
        CONFIG, CFG, DBFILE, COMMIT_LIST, SCHED, INIT_LOCK, __INITIALIZED__, started, LOGLIST, LOGTOGGLE, \
        UPDATE_MSG, CURRENT_TAB, CACHE_HIT, CACHE_MISS, LAST_LIBRARYTHING, \
        SHOW_AUDIO, CACHEDIR, BOOKSTRAP_THEMELIST, MONTHNAMES, CONFIG_DEFINITIONS, isbn_979_dict, isbn_978_dict, \
        CONFIG_NONWEB, CONFIG_NONDEFAULT, AUDIO_UPDATE, EBOOK_UPDATE, POSTPROCESS_UPDATE, \
        GROUP_CONCAT, LT_SLEEP, GB_CALLS

    with INIT_LOCK:

        if __INITIALIZED__:
            return False

        SCHED = BackgroundScheduler(misfire_grace_time=30)

        check_section('General')
        # False to silence logging until logger initialised
        for key in ['LOGLIMIT', 'LOGFILES', 'LOGSIZE', 'LOGDIR']:
            item_type, section, default = CONFIG_DEFINITIONS[key]
            CONFIG[key.upper()] = check_setting(item_type, section, key.lower(), default, log=False)

        if not CONFIG['LOGDIR']:
            CONFIG['LOGDIR'] = os.path.join(DATADIR, 'Logs')

        # Create logdir
        if not os.path.isdir(CONFIG['LOGDIR']):
            try:
                os.makedirs(CONFIG['LOGDIR'])
            except OSError as e:
                print('%s : Unable to create folder for logs: %s' % (CONFIG['LOGDIR'], str(e)))

        # Start the logger, silence console logging if we need to
        CFGLOGLEVEL = check_int(check_setting('int', 'General', 'loglevel', 1, log=False), 9)
        if LOGLEVEL == 1:  # default if no debug or quiet on cmdline
            if CFGLOGLEVEL == 9:  # default value if none in config
                LOGLEVEL = 1  # If not set in Config or cmdline, then lets set to NORMAL
            else:
                LOGLEVEL = CFGLOGLEVEL  # Config setting picked up

        CONFIG['LOGLEVEL'] = LOGLEVEL
        logger.bookbagofholding_log.initLogger(loglevel=CONFIG['LOGLEVEL'])
        logger.info("Log level set to [%s]- Log Directory is [%s] - Config level is [%s]" % (
            CONFIG['LOGLEVEL'], CONFIG['LOGDIR'], CFGLOGLEVEL))
        if CONFIG['LOGLEVEL'] > 2:
            logger.info("Screen Log set to EXTENDED DEBUG")
        elif CONFIG['LOGLEVEL'] == 2:
            logger.info("Screen Log set to DEBUG")
        elif CONFIG['LOGLEVEL'] == 1:
            logger.info("Screen Log set to INFO")
        else:
            logger.info("Screen Log set to WARN/ERROR")

        config_read()

        # override detected encoding if required
        if CONFIG['SYS_ENCODING']:
            SYS_ENCODING = CONFIG['SYS_ENCODING']

        # Put the cache dir in the data dir for now
        CACHEDIR = os.path.join(DATADIR, 'cache')
        if not os.path.isdir(CACHEDIR):
            try:
                os.makedirs(CACHEDIR)
            except OSError as e:
                logger.error('Could not create cachedir; %s' % e)

        for item in ['book', 'author', 'SeriesCache', 'JSONCache', 'XMLCache', 'WorkCache']:
            cachelocation = os.path.join(CACHEDIR, item)
            if not os.path.isdir(cachelocation):
                try:
                    os.makedirs(cachelocation)
                except OSError as e:
                    logger.error('Could not create %s: %s' % (cachelocation, e))

        # keep track of last api calls so we don't call more than once per second
        # to respect api terms, but don't wait un-necessarily either
        # keep track of how long we slept
        time_now = int(time.time())
        LAST_LIBRARYTHING = time_now
        LT_SLEEP = 0.0
        GB_CALLS = 0

        # Initialize the database
        try:
            myDB = database.DBConnection()
            result = myDB.match('PRAGMA user_version')
            check = myDB.match('PRAGMA integrity_check')
            if result:
                version = result[0]
            else:
                version = 0
            logger.info("Database is version %s, integrity check: %s" % (version, check[0]))
        except Exception as e:
            logger.error("Can't connect to the database: %s %s" % (type(e).__name__, str(e)))
            sys.exit(0)

        if version:
            check_db(myDB)

        # group_concat needs sqlite3 >= 3.5.4
        GROUP_CONCAT = False
        try:
            sqlv = getattr(sqlite3, 'sqlite_version', None)
            parts = sqlv.split('.')
            if int(parts[0]) == 3:
                if int(parts[1]) > 5 or int(parts[1]) == 5 and int(parts[2]) >= 4:
                    GROUP_CONCAT = True
        except Exception as e:
            logger.warn("Unable to parse sqlite3 version: %s %s" % (type(e).__name__, str(e)))

        debuginfo = logHeader()
        for item in debuginfo.splitlines():
            if 'missing' in item:
                logger.warn(item)

        try:  # optional module, check database health, could also be upgraded to modify/repair db or run other code
            # noinspection PyUnresolvedReferences
            from .dbcheck import dbcheck
            dbcheck()
        except ImportError:
            pass

        MONTHNAMES = build_monthtable()
        BOOKSTRAP_THEMELIST = build_bookstrap_themes(PROG_DIR)

        __INITIALIZED__ = True
        return True


# noinspection PyUnresolvedReferences
def config_read(reloaded=False):
    global CONFIG, CONFIG_DEFINITIONS, CONFIG_NONWEB, CONFIG_NONDEFAULT, NEWZNAB_PROV, TORZNAB_PROV, RSS_PROV, \
        SHOW_AUDIO, NABAPICOUNT
    # legacy name conversion
    if not CFG.has_option('General', 'ebook_dir'):
        ebook_dir = check_setting('str', 'General', 'destination_dir', '')
        CFG.set('General', 'ebook_dir', ebook_dir)
        CFG.remove_option('General', 'destination_dir')
    # legacy type conversion
    if CFG.has_option('Git', 'git_updated'):
        val = CFG.get('Git', 'git_updated')
        newval = check_int(val, 0)
        if newval != val:
            CFG.set('Git', 'git_updated', newval)
    # legacy name conversions, separate out host/port
    for provider in ['NZBGet', 'UTORRENT', 'QBITTORRENT', 'TRANSMISSION']:
        if not CFG.has_option(provider, '%s_port' % provider.lower()):
            port = 0
            host = check_setting('str', provider, '%s_host' % provider.lower(), '')
            if host.startswith('http'):
                hostpart = 2
            else:
                hostpart = 1
            words = host.split(':')
            if len(words) > hostpart:
                host = ':'.join(words[:hostpart])
                port = ':'.join(words[hostpart:])
            CFG.set(provider, '%s_port' % provider.lower(), port)
            CFG.set(provider, '%s_host' % provider.lower(), host)

    count = 0
    while CFG.has_section('Newznab%i' % count):
        newz_name = 'Newznab%i' % count
        # legacy name conversions
        if CFG.has_option(newz_name, 'newznab%i' % count):
            CFG.set(newz_name, 'ENABLED', CFG.getboolean(newz_name, 'newznab%i' % count))
            CFG.remove_option(newz_name, 'newznab%i' % count)
        if CFG.has_option(newz_name, 'newznab_host%i' % count):
            CFG.set(newz_name, 'HOST', CFG.get(newz_name, 'newznab_host%i' % count))
            CFG.remove_option(newz_name, 'newznab_host%i' % count)
        if CFG.has_option(newz_name, 'newznab_api%i' % count):
            CFG.set(newz_name, 'API', CFG.get(newz_name, 'newznab_api%i' % count))
            CFG.remove_option(newz_name, 'newznab_api%i' % count)
        if CFG.has_option(newz_name, 'nzedb'):
            CFG.remove_option(newz_name, 'nzedb')
        disp_name = check_setting('str', newz_name, 'dispname', newz_name)

        NEWZNAB_PROV.append({"NAME": newz_name,
                             "DISPNAME": disp_name,
                             "ENABLED": check_setting('bool', newz_name, 'enabled', 0),
                             "HOST": check_setting('str', newz_name, 'host', ''),
                             "API": check_setting('str', newz_name, 'api', ''),
                             "GENERALSEARCH": check_setting('str', newz_name, 'generalsearch', 'search'),
                             "BOOKSEARCH": check_setting('str', newz_name, 'booksearch', ''),
                             "AUDIOSEARCH": check_setting('str', newz_name, 'audiosearch', ''),
                             "BOOKCAT": check_setting('str', newz_name, 'bookcat', '7000,7020'),
                             "AUDIOCAT": check_setting('str', newz_name, 'audiocat', '3030'),
                             "EXTENDED": check_setting('str', newz_name, 'extended', '1'),
                             "UPDATED": check_setting('str', newz_name, 'updated', ''),
                             "MANUAL": check_setting('bool', newz_name, 'manual', 0),
                             "APILIMIT": check_setting('int', newz_name, 'apilimit', 0),
                             "APICOUNT": 0,
                             "DLPRIORITY": check_setting('int', newz_name, 'dlpriority', 0),
                             "DLTYPES": check_setting('str', newz_name, 'dltypes', 'A,E'),
                             })
        count += 1
    # if the last slot is full, add an empty one on the end
    add_newz_slot()

    count = 0
    while CFG.has_section('Torznab%i' % count):
        torz_name = 'Torznab%i' % count
        # legacy name conversions
        if CFG.has_option(torz_name, 'torznab%i' % count):
            CFG.set(torz_name, 'ENABLED', CFG.getboolean(torz_name, 'torznab%i' % count))
            CFG.remove_option(torz_name, 'torznab%i' % count)
        if CFG.has_option(torz_name, 'torznab_host%i' % count):
            CFG.set(torz_name, 'HOST', CFG.get(torz_name, 'torznab_host%i' % count))
            CFG.remove_option(torz_name, 'torznab_host%i' % count)
        if CFG.has_option(torz_name, 'torznab_api%i' % count):
            CFG.set(torz_name, 'API', CFG.get(torz_name, 'torznab_api%i' % count))
            CFG.remove_option(torz_name, 'torznab_api%i' % count)
        if CFG.has_option(torz_name, 'nzedb'):
            CFG.remove_option(torz_name, 'nzedb')
        disp_name = check_setting('str', torz_name, 'dispname', torz_name)

        TORZNAB_PROV.append({"NAME": torz_name,
                             "DISPNAME": disp_name,
                             "ENABLED": check_setting('bool', torz_name, 'enabled', 0),
                             "HOST": check_setting('str', torz_name, 'host', ''),
                             "API": check_setting('str', torz_name, 'api', ''),
                             "GENERALSEARCH": check_setting('str', torz_name, 'generalsearch', 'search'),
                             "BOOKSEARCH": check_setting('str', torz_name, 'booksearch', ''),
                             "AUDIOSEARCH": check_setting('str', torz_name, 'audiosearch', ''),
                             "BOOKCAT": check_setting('str', torz_name, 'bookcat', '8000,8010'),
                             "AUDIOCAT": check_setting('str', torz_name, 'audiocat', '3030'),
                             "EXTENDED": check_setting('str', torz_name, 'extended', '1'),
                             "UPDATED": check_setting('str', torz_name, 'updated', ''),
                             "MANUAL": check_setting('bool', torz_name, 'manual', 0),
                             "APILIMIT": check_setting('int', torz_name, 'apilimit', 0),
                             "APICOUNT": 0,
                             "DLPRIORITY": check_setting('int', torz_name, 'dlpriority', 0),
                             "DLTYPES": check_setting('str', torz_name, 'dltypes', 'A,E'),
                             })
        count += 1
    # if the last slot is full, add an empty one on the end
    add_torz_slot()

    count = 0
    while CFG.has_section('RSS_%i' % count):
        rss_name = 'RSS_%i' % count
        # legacy name conversions
        if CFG.has_option(rss_name, 'rss%i' % count):
            CFG.set(rss_name, 'ENABLED', CFG.getboolean(rss_name, 'rss%i' % count))
            CFG.remove_option(rss_name, 'rss%i' % count)
        if CFG.has_option(rss_name, 'rss_host%i' % count):
            CFG.set(rss_name, 'HOST', CFG.get(rss_name, 'rss_host%i' % count))
            CFG.remove_option(rss_name, 'rss_host%i' % count)
        if CFG.has_option(rss_name, 'rss_user%i' % count):
            # CFG.set(rss_name, 'USER', CFG.get(rss_name, 'rss_user%i' % count))
            CFG.remove_option(rss_name, 'rss_user%i' % count)
        if CFG.has_option(rss_name, 'rss_pass%i' % count):
            # CFG.set(rss_name, 'PASS', CFG.get(rss_name, 'rss_pass%i' % count))
            CFG.remove_option(rss_name, 'rss_pass%i' % count)
        if CFG.has_option(rss_name, 'PASS'):
            CFG.remove_option(rss_name, 'PASS')
        if CFG.has_option(rss_name, 'USER'):
            CFG.remove_option(rss_name, 'USER')
        disp_name = check_setting('str', rss_name, 'dispname', rss_name)

        RSS_PROV.append({"NAME": rss_name,
                         "DISPNAME": disp_name,
                         "ENABLED": check_setting('bool', rss_name, 'ENABLED', 0),
                         "HOST": check_setting('str', rss_name, 'HOST', ''),
                         "DLPRIORITY": check_setting('int', rss_name, 'DLPRIORITY', 0),
                         "DLTYPES": check_setting('str', rss_name, 'dltypes', 'E'),
                         })
        count += 1
    # if the last slot is full, add an empty one on the end
    add_rss_slot()

    for key in list(CONFIG_DEFINITIONS.keys()):
        item_type, section, default = CONFIG_DEFINITIONS[key]
        CONFIG[key.upper()] = check_setting(item_type, section, key.lower(), default)

    # Environment variable overrides for sensitive settings
    # BOOKBAGOFHOLDING_SSL_VERIFY overrides config file setting (0/1 or true/false)
    env_ssl_verify = os.environ.get('BOOKBAGOFHOLDING_SSL_VERIFY', '')
    if env_ssl_verify:
        CONFIG['SSL_VERIFY'] = env_ssl_verify.lower() in ('1', 'true', 'yes')

    if not CONFIG['LOGDIR']:
        CONFIG['LOGDIR'] = os.path.join(DATADIR, 'Logs')
    if CONFIG['HTTP_PORT'] < 21 or CONFIG['HTTP_PORT'] > 65535:
        CONFIG['HTTP_PORT'] = 5299

    # to make extension matching easier
    CONFIG['EBOOK_TYPE'] = CONFIG['EBOOK_TYPE'].lower()
    CONFIG['AUDIOBOOK_TYPE'] = CONFIG['AUDIOBOOK_TYPE'].lower()
    CONFIG['REJECT_WORDS'] = CONFIG['REJECT_WORDS'].lower()
    CONFIG['REJECT_AUDIO'] = CONFIG['REJECT_AUDIO'].lower()
    CONFIG['BANNED_EXT'] = CONFIG['BANNED_EXT'].lower()

    myDB = database.DBConnection()
    # check if we have an active database yet, not a fresh install
    result = myDB.match('PRAGMA user_version')
    if result:
        version = result[0]
    else:
        version = 0

    ###################################################################
    # ensure all these are boolean 1 0, not True False for javascript #
    ###################################################################
    # Show audio tab based on config
    if CONFIG['AUDIO_TAB']:
        SHOW_AUDIO = 1
    else:
        SHOW_AUDIO = 0

    for item in ['BOOK_IMG', 'AUTHOR_IMG', 'TOGGLES']:
        if CONFIG[item]:
            CONFIG[item] = 1
        else:
            CONFIG[item] = 0

    if reloaded:
        logger.info('Config file reloaded')
    else:
        logger.info('Config file loaded')


# noinspection PyUnresolvedReferences
def config_write(part=None):
    global SHOW_AUDIO, CONFIG_NONWEB, CONFIG_NONDEFAULT, LOGLEVEL, NEWZNAB_PROV, \
        TORZNAB_PROV, RSS_PROV

    if part:
        logger.info("Writing config for section [%s]" % part)

    currentname = threading.currentThread().name
    threading.currentThread().name = "CONFIG_WRITE"
    myDB = database.DBConnection()

    for key in list(CONFIG_DEFINITIONS.keys()):
        item_type, section, default = CONFIG_DEFINITIONS[key]
        if key in ['WALL_COLUMNS', 'DISPLAY_LENGTH']:  # may be modified by user interface but not on config page
            value = check_int(CONFIG[key], 5)
        elif part and section != part:
            value = CFG.get(section, key.lower())  # keep the old value
            # if CONFIG['LOGLEVEL'] > 2:
            #     logger.debug("Leaving %s unchanged (%s)" % (key, value))
        elif key not in CONFIG_NONWEB:
            check_section(section)
            value = CONFIG[key]
            if key == 'LOGLEVEL':
                LOGLEVEL = check_int(value, 1)
            elif key in ['REJECT_WORDS', 'REJECT_AUDIO', 'EBOOK_TYPE',
                         'BANNED_EXT', 'AUDIOBOOK_TYPE']:
                value = value.lower()
        else:
            # keep the old value
            value = CFG.get(section, key.lower())
            CONFIG[key] = value
            # if CONFIG['LOGLEVEL'] > 2:
            #    logger.debug("Leaving %s unchanged (%s)" % (key, value))

        if isinstance(value, str):
            value = value.strip()
            if 'DLTYPES' in key:
                value = ','.join(sorted(set([i for i in value.upper() if i in 'AEM'])))
                if not value:
                    value = 'E'
                CONFIG[key] = value

        if key in ['SEARCH_BOOKINTERVAL', 'SCAN_INTERVAL',
                   'SEARCHRSS_INTERVAL', 'WISHLIST_INTERVAL']:
            oldvalue = CFG.get(section, key.lower())
            if value != oldvalue:
                if key == 'SEARCH_BOOKINTERVAL':
                    scheduleJob('Restart', 'search_book')
                elif key == 'SEARCHRSS_INTERVAL':
                    scheduleJob('Restart', 'search_rss_book')
                elif key == 'WISHLIST_INTERVAL':
                    scheduleJob('Restart', 'search_wishlist')
                elif key == 'SCAN_INTERVAL':
                    scheduleJob('Restart', 'PostProcessor')

        CFG.set(section, key.lower(), value)

    # sanity check for typos...
    for key in list(CONFIG.keys()):
        if key not in list(CONFIG_DEFINITIONS.keys()):
            logger.warn('Unsaved/invalid config key: %s' % key)

    if not part or part.startswith('Newznab') or part.startswith('Torznab'):
        NAB_ITEMS = ['ENABLED', 'DISPNAME', 'HOST', 'API', 'GENERALSEARCH', 'BOOKSEARCH',
                     'AUDIOSEARCH', 'BOOKCAT', 'AUDIOCAT', 'EXTENDED', 'DLPRIORITY', 'DLTYPES',
                     'UPDATED', 'MANUAL', 'APILIMIT']
        for entry in [[NEWZNAB_PROV, 'Newznab'], [TORZNAB_PROV, 'Torznab']]:
            new_list = []
            # strip out any empty slots
            for provider in entry[0]:  # type: dict
                if provider['HOST']:
                    new_list.append(provider)

            # Remove duplicate providers by HOST URL (handles Prowlarr syncing duplicates)
            seen_hosts = set()
            unique_list = []
            for provider in new_list:
                host_key = provider['HOST'].lower().rstrip('/')
                if host_key not in seen_hosts:
                    seen_hosts.add(host_key)
                    unique_list.append(provider)
                else:
                    logger.warn('Removing duplicate %s provider: %s (%s)' %
                                (entry[1], provider.get('DISPNAME', ''), provider['HOST']))
            if len(unique_list) < len(new_list):
                logger.info('Removed %d duplicate %s providers' % (len(new_list) - len(unique_list), entry[1]))
            new_list = unique_list

            if part:  # only update the named provider
                for provider in new_list:
                    if provider['NAME'].lower() != part.lower():  # keep old values
                        if CONFIG['LOGLEVEL'] > 2:
                            logger.debug("Keep %s" % provider['NAME'])
                        for item in NAB_ITEMS:
                            provider[item] = CFG.get(provider['NAME'], item.lower())

            # renumber the items
            for index, item in enumerate(new_list):
                item['NAME'] = '%s%i' % (entry[1], index)

            # delete the old entries
            sections = CFG.sections()
            for item in sections:
                if item.startswith(entry[1]):
                    CFG.remove_section(item)

            for provider in new_list:
                check_section(provider['NAME'])
                for item in NAB_ITEMS:
                    value = provider[item]
                    if isinstance(value, str):
                        value = value.strip()
                    if item == 'DLTYPES':
                        value = ','.join(sorted(set([i for i in value.upper() if i in 'AEM'])))
                        if not value:
                            value = 'E'
                        provider['DLTYPES'] = value
                    CFG.set(provider['NAME'], item, value)

            if entry[1] == 'Newznab':
                NEWZNAB_PROV = new_list
                add_newz_slot()
            else:
                TORZNAB_PROV = new_list
                add_torz_slot()

    if not part or part.startswith('rss_'):
        RSS_ITEMS = ['ENABLED', 'DISPNAME', 'HOST', 'DLPRIORITY', 'DLTYPES']
        new_list = []
        # strip out any empty slots
        for provider in RSS_PROV:
            if provider['HOST']:
                new_list.append(provider)

        # Remove duplicate RSS providers by HOST URL
        seen_hosts = set()
        unique_list = []
        for provider in new_list:
            host_key = provider['HOST'].lower().rstrip('/')
            if host_key not in seen_hosts:
                seen_hosts.add(host_key)
                unique_list.append(provider)
            else:
                logger.warn('Removing duplicate RSS provider: %s (%s)' %
                            (provider.get('DISPNAME', ''), provider['HOST']))
        if len(unique_list) < len(new_list):
            logger.info('Removed %d duplicate RSS providers' % (len(new_list) - len(unique_list)))
        new_list = unique_list

        if part:  # only update the named provider
            for provider in new_list:
                if provider['NAME'].lower() != part:  # keep old values
                    if CONFIG['LOGLEVEL'] > 2:
                        logger.debug("Keep %s" % provider['NAME'])
                    for item in RSS_ITEMS:
                        provider[item] = CFG.get(provider['NAME'], item.lower())

        # renumber the items
        for index, item in enumerate(new_list):
            item['NAME'] = 'RSS_%i' % index

        # strip out the old config entries
        sections = CFG.sections()
        for item in sections:
            if item.startswith('RSS_'):
                CFG.remove_section(item)

        for provider in new_list:
            check_section(provider['NAME'])
            for item in RSS_ITEMS:
                value = provider[item]
                if isinstance(value, str):
                    value = value.strip()
                if item == 'DLTYPES':
                    value = ','.join(sorted(set([i for i in value.upper() if i in 'AEM'])))
                    if not value:
                        value = 'E'
                    provider['DLTYPES'] = value
                CFG.set(provider['NAME'], item, value)

        RSS_PROV = new_list
        add_rss_slot()

    if CONFIG['AUDIO_TAB']:
        SHOW_AUDIO = 1
    else:
        SHOW_AUDIO = 0

    msg = None
    try:
        with open(CONFIGFILE + '.new', 'w') as configfile:
            CFG.write(configfile)
    except Exception as e:
        msg = '{} {} {} {}'.format('Unable to create new config file:', CONFIGFILE, type(e).__name__, str(e))
        logger.warn(msg)
        threading.currentThread().name = currentname
        return
    try:
        os.remove(CONFIGFILE + '.bak')
    except OSError as e:
        if e.errno is not 2:  # doesn't exist is ok
            msg = '{} {}{} {} {}'.format(type(e).__name__, 'deleting backup file:', CONFIGFILE, '.bak', e.strerror)
            logger.warn(msg)
    try:
        os.rename(CONFIGFILE, CONFIGFILE + '.bak')
    except OSError as e:
        if e.errno is not 2:  # doesn't exist is ok as wouldn't exist until first save
            msg = '{} {} {} {}'.format('Unable to backup config file:', CONFIGFILE, type(e).__name__, e.strerror)
            logger.warn(msg)
    try:
        os.rename(CONFIGFILE + '.new', CONFIGFILE)
    except OSError as e:
        msg = '{} {} {} {}'.format('Unable to rename new config file:', CONFIGFILE, type(e).__name__, e.strerror)
        logger.warn(msg)

    if not msg:
        if part is None:
            part = ''
        msg = 'Config file [%s] %s has been updated' % (CONFIGFILE, part)
        logger.info(msg)

    threading.currentThread().name = currentname


# noinspection PyUnresolvedReferences
def add_newz_slot():
    count = len(NEWZNAB_PROV)
    if count == 0 or len(CFG.get('Newznab%i' % int(count - 1), 'HOST')):
        prov_name = 'Newznab%i' % count
        empty = {"NAME": prov_name,
                 "DISPNAME": prov_name,
                 "ENABLED": 0,
                 "HOST": '',
                 "API": '',
                 "GENERALSEARCH": 'search',
                 "BOOKSEARCH": 'book',
                 "AUDIOSEARCH": '',
                 "BOOKCAT": '7000,7020',
                 "AUDIOCAT": '3030',
                 "EXTENDED": '1',
                 "UPDATED": '',
                 "MANUAL": 0,
                 "APILIMIT": 0,
                 "APICOUNT": 0,
                 "DLPRIORITY": 0,
                 "DLTYPES": 'A,E'
                 }
        NEWZNAB_PROV.append(empty)

        check_section(prov_name)
        for item in empty:
            if item != 'NAME':
                CFG.set(prov_name, item, empty[item])


# noinspection PyUnresolvedReferences
def add_torz_slot():
    count = len(TORZNAB_PROV)
    if count == 0 or len(CFG.get('Torznab%i' % int(count - 1), 'HOST')):
        prov_name = 'Torznab%i' % count
        empty = {"NAME": prov_name,
                 "DISPNAME": prov_name,
                 "ENABLED": 0,
                 "HOST": '',
                 "API": '',
                 "GENERALSEARCH": 'search',
                 "BOOKSEARCH": 'book',
                 "AUDIOSEARCH": '',
                 "BOOKCAT": '8000,8010',
                 "AUDIOCAT": '8030',
                 "EXTENDED": '1',
                 "UPDATED": '',
                 "MANUAL": 0,
                 "APILIMIT": 0,
                 "APICOUNT": 0,
                 "DLPRIORITY": 0,
                 "DLTYPES": 'A,E'
                 }
        TORZNAB_PROV.append(empty)

        check_section(prov_name)
        for item in empty:
            if item != 'NAME':
                CFG.set(prov_name, item, empty[item])


def DIRECTORY(dirname):
    usedir = ''
    if dirname == "eBook":
        usedir = CONFIG['EBOOK_DIR']
    elif dirname == "AudioBook" or dirname == "Audio":
        usedir = CONFIG['AUDIO_DIR']
    elif dirname == "Download":
        try:
            usedir = getList(CONFIG['DOWNLOAD_DIR'], ',')[0]
        except IndexError:
            usedir = ''
    elif dirname == "Alternate":
        usedir = CONFIG['ALTERNATE_DIR']
    else:
        return usedir

    if usedir and os.path.isdir(usedir):
        try:
            with open(os.path.join(usedir, 'll_temp'), 'w') as f:
                f.write('test')
            os.remove(os.path.join(usedir, 'll_temp'))
        except Exception as why:
            logger.warn("%s dir [%s] not writeable, using %s: %s" % (dirname, usedir, DATADIR, str(why)))
            logger.debug("Folder: %s Mode: %s UID: %s GID: %s W_OK: %s X_OK: %s" % (usedir,
                         oct(os.stat(usedir).st_mode), os.stat(usedir).st_uid, os.stat(usedir).st_gid,
                         os.access(usedir, os.W_OK), os.access(usedir, os.X_OK)))
            usedir = DATADIR
    else:
        logger.warn("%s dir [%s] not found, using %s" % (dirname, usedir, DATADIR))
        usedir = DATADIR

    # return directory as unicode so we get unicode results from listdir
    return makeUnicode(usedir)


# noinspection PyUnresolvedReferences
def add_rss_slot():
    count = len(RSS_PROV)
    if count == 0 or len(CFG.get('RSS_%i' % int(count - 1), 'HOST')):
        rss_name = 'RSS_%i' % count
        check_section(rss_name)
        CFG.set(rss_name, 'ENABLED', False)
        CFG.set(rss_name, 'HOST', '')
        # CFG.set(rss_name, 'USER', '')
        # CFG.set(rss_name, 'PASS', '')
        RSS_PROV.append({"NAME": rss_name,
                         "DISPNAME": rss_name,
                         "ENABLED": 0,
                         "HOST": '',
                         "DLPRIORITY": 0,
                         "DLTYPES": 'E'
                         })


def WishListType(host):
    """ Return type of wishlist or empty string if not a wishlist """
    # NYTimes best-sellers html pages
    if 'nytimes' in host and 'best-sellers' in host:
        return 'NYTIMES'
    return ''


def USE_RSS():
    count = 0
    for provider in RSS_PROV:
        if bool(provider['ENABLED']) and not WishListType(provider['HOST']):
            count += 1
    return count


def USE_WISHLIST():
    count = 0
    for provider in RSS_PROV:
        if bool(provider['ENABLED']) and WishListType(provider['HOST']):
            count += 1
    return count


def USE_NZB():
    # Count how many nzb providers are active
    count = 0
    for provider in NEWZNAB_PROV:
        if bool(provider['ENABLED']):
            count += 1
    for provider in TORZNAB_PROV:
        if bool(provider['ENABLED']):
            count += 1
    return count


def USE_TOR():
    count = 0
    for provider in [CONFIG['KAT'], CONFIG['WWT'], CONFIG['TPB'], CONFIG['ZOO'], CONFIG['LIME'], CONFIG['TDL']]:
        if bool(provider):
            count += 1
    return count


def USE_DIRECT():
    count = 0
    for provider in [CONFIG['GEN'], CONFIG['GEN2']]:
        if bool(provider):
            count += 1
    return count


def build_bookstrap_themes(prog_dir):
    themelist = []
    if not os.path.isdir(os.path.join(prog_dir, 'data', 'interfaces', 'bookstrap')):
        return themelist  # return empty if bookstrap interface not installed

    URL = 'http://bootswatch.com/api/3.json'
    result, success = fetchURL(URL, headers=None, retry=False)
    if not success:
        logger.debug("Error getting bookstrap themes : %s" % result)
        return themelist

    try:
        results = json.loads(result)
        for theme in results['themes']:
            themelist.append(theme['name'].lower())
    except Exception as e:
        # error reading results
        logger.warn('JSON Error reading bookstrap themes, %s %s' % (type(e).__name__, str(e)))

    logger.info("Bookstrap found %i themes" % len(themelist))
    return themelist


def build_monthtable():
    table = []
    json_file = os.path.join(DATADIR, 'monthnames.json')
    if os.path.isfile(json_file):
        try:
            with open(json_file) as json_data:
                table = json.load(json_data)
            mlist = ''
            # list alternate entries as each language is in twice (long and short month names)
            for item in table[0][::2]:
                mlist += item + ' '
            logger.debug('Loaded monthnames.json : %s' % mlist)
        except Exception as e:
            logger.error('Failed to load monthnames.json, %s %s' % (type(e).__name__, str(e)))

    if not table:
        # Default Month names table to hold long/short month names for multiple languages
        # which we can use for date matching
        table = [
            ['en_GB.UTF-8', 'en_GB.UTF-8'],
            ['january', 'jan'],
            ['february', 'feb'],
            ['march', 'mar'],
            ['april', 'apr'],
            ['may', 'may'],
            ['june', 'jun'],
            ['july', 'jul'],
            ['august', 'aug'],
            ['september', 'sep'],
            ['october', 'oct'],
            ['november', 'nov'],
            ['december', 'dec']
        ]

    if len(getList(CONFIG['IMP_MONTHLANG'])) == 0:  # any extra languages wanted?
        return table
    try:
        current_locale = locale.setlocale(locale.LC_ALL, '')  # read current state.
        if 'LC_CTYPE' in current_locale:
            current_locale = locale.setlocale(locale.LC_CTYPE, '')
        # getdefaultlocale() doesnt seem to work as expected on windows, returns 'None'
        logger.debug('Current locale is %s' % current_locale)
    except locale.Error as e:
        logger.debug("Error getting current locale : %s" % str(e))
        return table

    lang = str(current_locale)
    # check not already loaded, also all english variants and 'C' use the same month names
    if lang in table[0] or ((lang.startswith('en_') or lang == 'C') and 'en_' in str(table[0])):
        logger.debug('Month names for %s already loaded' % lang)
    else:
        logger.debug('Loading month names for %s' % lang)
        table[0].append(lang)
        for f in range(1, 13):
            table[f].append(unaccented(calendar.month_name[f]).lower())
        table[0].append(lang)
        for f in range(1, 13):
            table[f].append(unaccented(calendar.month_abbr[f]).lower().strip('.'))
        logger.info("Added month names for locale [%s], %s, %s ..." % (
            lang, table[1][len(table[1]) - 2], table[1][len(table[1]) - 1]))

    for lang in getList(CONFIG['IMP_MONTHLANG']):
        try:
            if lang in table[0] or ((lang.startswith('en_') or lang == 'C') and 'en_' in str(table[0])):
                logger.debug('Month names for %s already loaded' % lang)
            else:
                locale.setlocale(locale.LC_ALL, lang)
                logger.debug('Loading month names for %s' % lang)
                table[0].append(lang)
                for f in range(1, 13):
                    table[f].append(unaccented(calendar.month_name[f]).lower())
                table[0].append(lang)
                for f in range(1, 13):
                    table[f].append(unaccented(calendar.month_abbr[f]).lower().strip('.'))
                locale.setlocale(locale.LC_ALL, current_locale)  # restore entry state
                logger.info("Added month names for locale [%s], %s, %s ..." % (
                    lang, table[1][len(table[1]) - 2], table[1][len(table[1]) - 1]))
        except Exception as e:
            locale.setlocale(locale.LC_ALL, current_locale)  # restore entry state
            logger.warn("Unable to load requested locale [%s] %s %s" % (lang, type(e).__name__, str(e)))
            try:
                wanted_lang = lang.split('_')[0]
                params = ['locale', '-a']
                res = subprocess.check_output(params, stderr=subprocess.STDOUT)
                all_locales = makeUnicode(res).split()
                locale_list = []
                for a_locale in all_locales:
                    if a_locale.startswith(wanted_lang):
                        locale_list.append(a_locale)
                if locale_list:
                    logger.warn("Found these alternatives: " + str(locale_list))
                else:
                    logger.warn("Unable to find an alternative")
            except Exception as e:
                logger.warn("Unable to get a list of alternatives, %s %s" % (type(e).__name__, str(e)))
            logger.debug("Set locale back to entry state %s" % current_locale)

    # with open(json_file, 'w') as f:
    #    json.dump(table, f)
    return table


def daemonize():
    """
    Fork off as a daemon
    """
    threadcount = threading.activeCount()
    if threadcount != 1:
        logger.warn('There are %d active threads. Daemonizing may cause strange behavior.' % threadcount)

    sys.stdout.flush()
    sys.stderr.flush()

    # Make a non-session-leader child process
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError as e:
        raise RuntimeError("1st fork failed: %s [%d]" % (e.strerror, e.errno))

    os.setsid()  # @UndefinedVariable - only available in UNIX

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError as e:
        raise RuntimeError("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

    dev_null = open('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = os.getpid()
    logger.debug("Daemonized to PID %d" % pid)

    if PIDFILE:
        logger.debug("Writing PID %d to %s" % (pid, PIDFILE))
        with open(PIDFILE, 'w') as pidfile:
            pidfile.write("%s\n" % pid)


def launch_browser(host, port, root):
    if host == '0.0.0.0':
        host = 'localhost'

    if CONFIG['HTTPS_ENABLED']:
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
    except Exception as e:
        logger.error('Could not launch browser:%s  %s' % (type(e).__name__, str(e)))


def start():
    global __INITIALIZED__, started, SHOW_AUDIO

    if __INITIALIZED__:
        # Crons and scheduled jobs started here
        SCHED.start()
        started = True
        if not UPDATE_MSG:
            restartJobs(start='Start')

            if CONFIG['AUDIO_TAB']:
                SHOW_AUDIO = 1
            else:
                SHOW_AUDIO = 0


def logmsg(level, msg):
    # log messages to logger if initialised, or print if not.
    if __INITIALIZED__:
        if level == 'error':
            logger.error(msg)
        elif level == 'debug':
            logger.debug(msg)
        elif level == 'warn':
            logger.warn(msg)
        else:
            logger.info(msg)
    else:
        print(level.upper(), msg)


def shutdown(restart=False):
    cherrypy.engine.exit()
    if SCHED:
        SCHED.shutdown(wait=False)
    # config_write() don't automatically rewrite config on exit

    if not restart:
        logmsg('info', 'Bookbag of Holding is shutting down...')

    if PIDFILE:
        logmsg('info', 'Removing pidfile %s' % PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logmsg('info', 'Bookbag of Holding is restarting ...')

        # Try to use the currently running python executable, as it is known to work
        # if not able to determine, sys.executable returns empty string or None
        # and we have to go looking for it...
        executable = sys.executable

        if not executable:
            prg = "python3"
            if platform.system() == "Windows":
                params = ["where", prg]
                try:
                    executable = subprocess.check_output(params, stderr=subprocess.STDOUT)
                    executable = makeUnicode(executable).strip()
                except Exception as e:
                    logger.debug("where %s failed: %s %s" % (prg, type(e).__name__, str(e)))
            else:
                params = ["which", prg]
                try:
                    executable = subprocess.check_output(params, stderr=subprocess.STDOUT)
                    executable = makeUnicode(executable).strip()
                except Exception as e:
                    logger.debug("which %s failed: %s %s" % (prg, type(e).__name__, str(e)))

        if not executable:
            executable = 'python'  # default if not found

        popen_list = [executable, FULL_PATH]
        popen_list += ARGS
        if '--update' in popen_list:
            popen_list.remove('--update')
        if LOGLEVEL:
            if '--quiet' in popen_list:
                popen_list.remove('--quiet')
            if '-q' in popen_list:
                popen_list.remove('-q')
        if '--nolaunch' not in popen_list:
            popen_list += ['--nolaunch']

        logmsg('debug', 'Restarting Bookbag of Holding with ' + str(popen_list))
        subprocess.Popen(popen_list, cwd=os.getcwd())

    logmsg('info', 'Bookbag of Holding is exiting')
    sys.exit(0)
