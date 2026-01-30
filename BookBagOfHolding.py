#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
import locale
import os
import platform
import sys
import threading
import time

import bookbagofholding
from bookbagofholding import webStart, logger, dbupgrade
import configparser

def configure_ssl_verification():
    """
    Configure SSL certificate verification based on config settings.

    This can be controlled via:
    - config.ini: SSL_VERIFY = 0 (default, skip verification) or 1 (verify certificates)
    - Environment variable: BOOKBAGOFHOLDING_SSL_VERIFY = true/false or 1/0

    SSL verification is DISABLED by default for backward compatibility with systems
    that have broken SSL (like QNAP). Set SSL_VERIFY = 1 to enable verification.
    """
    # Check environment variable first, then config
    env_ssl_verify = os.environ.get('BOOKBAGOFHOLDING_SSL_VERIFY', '')
    if env_ssl_verify:
        ssl_verify = env_ssl_verify.lower() in ('1', 'true', 'yes')
    else:
        ssl_verify = bookbagofholding.CONFIG.get('SSL_VERIFY', False)

    if not ssl_verify:
        # noinspection PyBroadException
        try:
            import ssl
            # noinspection PyProtectedMember
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass


def main():
    # rename this thread
    threading.current_thread().name = "MAIN"

    # Set paths
    if hasattr(sys, 'frozen'):
        bookbagofholding.FULL_PATH = os.path.abspath(sys.executable)
    else:
        bookbagofholding.FULL_PATH = os.path.abspath(__file__)

    bookbagofholding.PROG_DIR = os.path.dirname(bookbagofholding.FULL_PATH)
    bookbagofholding.ARGS = sys.argv[1:]

    bookbagofholding.SYS_ENCODING = None

    try:
        locale.setlocale(locale.LC_ALL, "")
        bookbagofholding.SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # for OSes that are poorly configured I'll just force UTF-8
    # windows cp1252 can't handle some accented author names,
    # eg "Marie Kondō" U+014D: LATIN SMALL LETTER O WITH MACRON, but utf-8 does
    if not bookbagofholding.SYS_ENCODING or bookbagofholding.SYS_ENCODING in (
            'ANSI_X3.4-1968', 'US-ASCII', 'ASCII') or '1252' in bookbagofholding.SYS_ENCODING:
        bookbagofholding.SYS_ENCODING = 'UTF-8'

    # Set arguments
    from optparse import OptionParser

    p = OptionParser()
    p.add_option('-d', '--daemon', action="store_true",
                 dest='daemon', help="Run the server as a daemon")
    p.add_option('-q', '--quiet', action="store_true",
                 dest='quiet', help="Don't log to console")
    p.add_option('--debug', action="store_true",
                 dest='debug', help="Show debuglog messages")
    p.add_option('--nolaunch', action="store_true",
                 dest='nolaunch', help="Don't start browser")
    p.add_option('--port',
                 dest='port', default=None,
                 help="Force webinterface to listen on this port")
    p.add_option('--datadir',
                 dest='datadir', default=None,
                 help="Path to the data directory")
    p.add_option('--config',
                 dest='config', default=None,
                 help="Path to config.ini file")
    p.add_option('-p', '--pidfile',
                 dest='pidfile', default=None,
                 help="Store the process id in the given file")
    p.add_option('--loglevel',
                 dest='loglevel', default=None,
                 help="Debug loglevel")

    options, args = p.parse_args()

    bookbagofholding.LOGLEVEL = 1
    if options.debug:
        bookbagofholding.LOGLEVEL = 2

    if options.quiet:
        bookbagofholding.LOGLEVEL = 0

    if options.daemon:
        if 'windows' not in platform.system().lower():
            bookbagofholding.DAEMON = True
            # bookbagofholding.daemonize()
        else:
            print("Daemonize not supported under Windows, starting normally")

    if options.nolaunch:
        bookbagofholding.CONFIG['LAUNCH_BROWSER'] = False

    if options.loglevel:
        try:
            bookbagofholding.LOGLEVEL = int(options.loglevel)
        except:
            pass

    if options.datadir:
        bookbagofholding.DATADIR = str(options.datadir)
    else:
        bookbagofholding.DATADIR = bookbagofholding.PROG_DIR

    if options.config:
        bookbagofholding.CONFIGFILE = str(options.config)
    else:
        bookbagofholding.CONFIGFILE = os.path.join(bookbagofholding.DATADIR, "config.ini")

    if options.pidfile:
        if bookbagofholding.DAEMON:
            bookbagofholding.PIDFILE = str(options.pidfile)

    # create and check (optional) paths
    if not os.path.isdir(bookbagofholding.DATADIR):
        try:
            os.makedirs(bookbagofholding.DATADIR)
        except OSError:
            raise SystemExit('Could not create data directory: ' + bookbagofholding.DATADIR + '. Exit ...')

    if not os.access(bookbagofholding.DATADIR, os.W_OK):
        raise SystemExit('Cannot write to the data directory: ' + bookbagofholding.DATADIR + '. Exit ...')

    print("Bookbag of Holding is starting up...")
    time.sleep(4)  # allow a bit of time for old task to exit if restarting. Needs to free logfile and server port.

    # create database and config
    bookbagofholding.DBFILE = os.path.join(bookbagofholding.DATADIR, 'bookbagofholding.db')
    bookbagofholding.CFG = configparser.RawConfigParser()
    bookbagofholding.CFG.read(bookbagofholding.CONFIGFILE)

    # REMINDER ############ NO LOGGING BEFORE HERE ###############
    # There is no point putting in any logging above this line, as its not set till after initialize.
    bookbagofholding.initialize()

    # Configure SSL verification based on config/env settings
    configure_ssl_verification()


    if bookbagofholding.DAEMON:
        bookbagofholding.daemonize()

    # Try to start the server.
    if options.port:
        bookbagofholding.CONFIG['HTTP_PORT'] = int(options.port)
        logger.info('Starting Bookbag of Holding on forced port: %s, webroot "%s"' %
                    (bookbagofholding.CONFIG['HTTP_PORT'], bookbagofholding.CONFIG['HTTP_ROOT']))
    else:
        bookbagofholding.CONFIG['HTTP_PORT'] = int(bookbagofholding.CONFIG['HTTP_PORT'])
        logger.info('Starting Bookbag of Holding on port: %s, webroot "%s"' %
                    (bookbagofholding.CONFIG['HTTP_PORT'], bookbagofholding.CONFIG['HTTP_ROOT']))

    webStart.initialize({
        'http_port': bookbagofholding.CONFIG['HTTP_PORT'],
        'http_host': bookbagofholding.CONFIG['HTTP_HOST'],
        'http_root': bookbagofholding.CONFIG['HTTP_ROOT'],
        'http_user': bookbagofholding.CONFIG['HTTP_USER'],
        'http_pass': bookbagofholding.CONFIG['HTTP_PASS'],
        'http_proxy': bookbagofholding.CONFIG['HTTP_PROXY'],
        'https_enabled': bookbagofholding.CONFIG['HTTPS_ENABLED'],
        'https_cert': bookbagofholding.CONFIG['HTTPS_CERT'],
        'https_key': bookbagofholding.CONFIG['HTTPS_KEY'],
        'opds_enabled': bookbagofholding.CONFIG['OPDS_ENABLED'],
        'opds_authentication': bookbagofholding.CONFIG['OPDS_AUTHENTICATION'],
        'opds_username': bookbagofholding.CONFIG['OPDS_USERNAME'],
        'opds_password': bookbagofholding.CONFIG['OPDS_PASSWORD'],
    })

    if bookbagofholding.CONFIG['LAUNCH_BROWSER'] and not options.nolaunch:
        bookbagofholding.launch_browser(bookbagofholding.CONFIG['HTTP_HOST'],
                                     bookbagofholding.CONFIG['HTTP_PORT'],
                                     bookbagofholding.CONFIG['HTTP_ROOT'])

    curr_ver = dbupgrade.upgrade_needed()
    if curr_ver:
        bookbagofholding.UPDATE_MSG = 'Updating database to version %s' % curr_ver
        threading.Thread(target=dbupgrade.dbupgrade, name="DB_UPGRADE", args=[curr_ver]).start()

    bookbagofholding.start()

    while True:
        if not bookbagofholding.SIGNAL:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                bookbagofholding.shutdown()
        else:
            if bookbagofholding.SIGNAL == 'shutdown':
                bookbagofholding.shutdown()
            elif bookbagofholding.SIGNAL == 'restart':
                bookbagofholding.shutdown(restart=True)
            bookbagofholding.SIGNAL = None


if __name__ == "__main__":
    main()
