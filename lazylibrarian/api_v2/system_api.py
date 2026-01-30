#  This file is part of Lazylibrarian.
#  Lazylibrarian is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

"""
System API endpoints for Bookbag of Holding.

This module contains API methods for system operations:
- Get logs
- Show jobs and stats
- Shutdown/restart
- Configuration read/write
- Library scans
"""

import configparser
import os
import sys
import threading
from typing import Any, Dict, List

import lazylibrarian
from lazylibrarian import logger
from lazylibrarian.api_v2.base import ApiBase, api_endpoint, require_param
from lazylibrarian.common import (
    clearLog, restartJobs, showJobs, checkRunningJobs, showStats,
    cleanCache, logHeader
)
from lazylibrarian.librarysync import LibraryScan
from lazylibrarian.magazinescan import magazineScan
from lazylibrarian.postprocess import processDir


class SystemApi(ApiBase):
    """API handler for system-related endpoints."""

    @api_endpoint("Show current log")
    def get_logs(self, **kwargs) -> Dict[str, Any]:
        """Get current log contents.

        Returns:
            Log entries
        """
        logfile = os.path.join(lazylibrarian.CONFIG['LOGDIR'], 'lazylibrarian.log')
        if os.path.isfile(logfile):
            with open(logfile, 'r') as f:
                log_contents = f.read()
            return self.success(data=log_contents)
        else:
            return self.error("Log file not found")

    @api_endpoint("Show debug log header")
    def get_debug(self, **kwargs) -> Dict[str, Any]:
        """Get debug log header.

        Returns:
            Debug header information
        """
        header = logHeader()
        return self.success(data=header)

    @api_endpoint("Clear current log")
    def clear_logs(self, **kwargs) -> Dict[str, Any]:
        """Clear the current log file.

        Returns:
            Success message
        """
        clearLog()
        return self.success(message="Log cleared")

    @api_endpoint("Show status of running jobs")
    def show_jobs(self, **kwargs) -> Dict[str, Any]:
        """Get status of background jobs.

        Returns:
            Job status information
        """
        jobs = showJobs()
        return self.success(data=jobs)

    @api_endpoint("Show database statistics")
    def show_stats(self, **kwargs) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics data
        """
        stats = showStats()
        return self.success(data=stats)

    @api_endpoint("Show threaded processes")
    def show_threads(self, **kwargs) -> List[str]:
        """Get list of running threads.

        Returns:
            List of thread names
        """
        threads = [t.name for t in threading.enumerate()]
        return threads

    @api_endpoint("Restart background jobs")
    def restart_jobs(self, **kwargs) -> Dict[str, Any]:
        """Restart all background jobs.

        Returns:
            Success message
        """
        restartJobs()
        return self.success(message="Jobs restarted")

    @api_endpoint("Ensure all needed jobs are running")
    def check_running_jobs(self, **kwargs) -> Dict[str, Any]:
        """Check and start any missing jobs.

        Returns:
            Success message
        """
        checkRunningJobs()
        return self.success(message="Jobs checked")

    @api_endpoint("Vacuum the database")
    def vacuum(self, **kwargs) -> Dict[str, Any]:
        """Vacuum the SQLite database.

        Returns:
            Success message
        """
        self.db.action("VACUUM")
        logger.info("Database vacuumed")
        return self.success(message="Database vacuumed")

    @api_endpoint("Read config variable", ["&name= config name", "&group= config section"])
    @require_param('name', 'group')
    def read_cfg(self, **kwargs) -> Dict[str, Any]:
        """Read a configuration value.

        Args:
            name: Config variable name
            group: Config section name

        Returns:
            Config value
        """
        name = kwargs['name'].upper()
        group = kwargs['group']

        configfile = lazylibrarian.CONFIGFILE
        config = configparser.ConfigParser()
        config.read(configfile)

        try:
            value = config.get(group, name)
            return self.success(data={name: value})
        except (configparser.NoSectionError, configparser.NoOptionError):
            return self.error("Config not found: [%s] %s" % (group, name))

    @api_endpoint("Write config variable",
                  ["&name= config name", "&group= config section", "&value= new value"])
    @require_param('name', 'group', 'value')
    def write_cfg(self, **kwargs) -> Dict[str, Any]:
        """Write a configuration value.

        Args:
            name: Config variable name
            group: Config section name
            value: New value

        Returns:
            Success or error
        """
        name = kwargs['name'].upper()
        group = kwargs['group']
        value = kwargs['value']

        configfile = lazylibrarian.CONFIGFILE
        config = configparser.ConfigParser()
        config.read(configfile)

        try:
            if not config.has_section(group):
                config.add_section(group)
            config.set(group, name, value)

            with open(configfile, 'w') as f:
                config.write(f)

            # Also update in-memory config if applicable
            if name in lazylibrarian.CONFIG:
                lazylibrarian.CONFIG[name] = value

            logger.info("Config updated: [%s] %s = %s" % (group, name, value))
            return self.success(message="Config updated")

        except Exception as e:
            return self.error("Failed to write config: %s" % str(e))

    @api_endpoint("Reload config from file")
    def load_cfg(self, **kwargs) -> Dict[str, Any]:
        """Reload configuration from file.

        Returns:
            Success message
        """
        lazylibrarian.config_read()
        return self.success(message="Config reloaded")

    @api_endpoint("Process downloads", ["&dir= directory (optional)",
                                         "&ignorekeepseeding= ignore keep seeding flag"])
    def force_process(self, **kwargs) -> Dict[str, Any]:
        """Force process downloads.

        Args:
            dir: Directory to process (optional)
            ignorekeepseeding: Whether to ignore keep seeding flag

        Returns:
            Success message
        """
        directory = kwargs.get('dir', None)
        ignore_keep = 'ignorekeepseeding' in kwargs

        t = threading.Thread(
            target=processDir,
            name='POSTPROCESS',
            args=[False, directory, ignore_keep]
        )
        t.start()

        return self.success(message="Post-processing started")

    @api_endpoint("Rescan book library",
                  ["&wait= wait for completion", "&remove= remove missing",
                   "&dir= directory", "&id= author ID"])
    def force_library_scan(self, **kwargs) -> Dict[str, Any]:
        """Force a library scan.

        Args:
            wait: Whether to wait for completion
            remove: Whether to remove missing books
            dir: Specific directory to scan
            id: Specific author ID to scan

        Returns:
            Success message
        """
        wait = kwargs.get('wait', False)
        remove = kwargs.get('remove', False)
        directory = kwargs.get('dir', None)
        author_id = kwargs.get('id', None)

        t = threading.Thread(
            target=LibraryScan,
            name='LIBRARYSCAN',
            args=[directory, 'eBook', author_id, remove]
        )
        t.start()

        if wait:
            t.join()
            return self.success(message="Library scan completed")
        else:
            return self.success(message="Library scan started")

    @api_endpoint("Rescan audiobook library",
                  ["&wait= wait for completion", "&remove= remove missing",
                   "&dir= directory", "&id= author ID"])
    def force_audiobook_scan(self, **kwargs) -> Dict[str, Any]:
        """Force an audiobook library scan.

        Args:
            wait: Whether to wait for completion
            remove: Whether to remove missing books
            dir: Specific directory to scan
            id: Specific author ID to scan

        Returns:
            Success message
        """
        wait = kwargs.get('wait', False)
        remove = kwargs.get('remove', False)
        directory = kwargs.get('dir', None)
        author_id = kwargs.get('id', None)

        t = threading.Thread(
            target=LibraryScan,
            name='AUDIOSCAN',
            args=[directory, 'AudioBook', author_id, remove]
        )
        t.start()

        if wait:
            t.join()
            return self.success(message="Audiobook scan completed")
        else:
            return self.success(message="Audiobook scan started")

    @api_endpoint("Rescan magazine library", ["&wait= wait for completion"])
    def force_magazine_scan(self, **kwargs) -> Dict[str, Any]:
        """Force a magazine library scan.

        Args:
            wait: Whether to wait for completion

        Returns:
            Success message
        """
        wait = kwargs.get('wait', False)

        t = threading.Thread(target=magazineScan, name='MAGSCAN')
        t.start()

        if wait:
            t.join()
            return self.success(message="Magazine scan completed")
        else:
            return self.success(message="Magazine scan started")

    @api_endpoint("Clean unused cache files", ["&wait= wait for completion"])
    def clean_cache(self, **kwargs) -> Dict[str, Any]:
        """Clean unused cache files.

        Args:
            wait: Whether to wait for completion

        Returns:
            Success message
        """
        wait = kwargs.get('wait', False)

        t = threading.Thread(target=cleanCache, name='CLEANCACHE')
        t.start()

        if wait:
            t.join()
            return self.success(message="Cache cleaned")
        else:
            return self.success(message="Cache cleaning started")

    @api_endpoint("Show installed modules")
    def get_modules(self, **kwargs) -> Dict[str, Any]:
        """Get list of installed Python modules.

        Returns:
            Module information
        """
        modules = {}
        for name in ['requests', 'cherrypy', 'mako', 'sqlite3']:
            try:
                mod = __import__(name)
                version = getattr(mod, '__version__', 'unknown')
                modules[name] = version
            except ImportError:
                modules[name] = 'not installed'

        modules['python'] = sys.version
        return self.success(data=modules)

    @api_endpoint("Send a message to logger", ["&level= log level", "&text= message"])
    @require_param('level', 'text')
    def log_message(self, **kwargs) -> Dict[str, Any]:
        """Send a message to the logger.

        Args:
            level: Log level (DEBUG, INFO, WARN, ERROR)
            text: Message text

        Returns:
            Success message
        """
        level = kwargs['level'].upper()
        text = kwargs['text']

        if level == 'DEBUG':
            logger.debug(text)
        elif level == 'INFO':
            logger.info(text)
        elif level == 'WARN':
            logger.warn(text)
        elif level == 'ERROR':
            logger.error(text)
        else:
            return self.error("Invalid log level: %s" % level)

        return self.success(message="Message logged")

    @api_endpoint("Stop Bookbag of Holding")
    def shutdown(self, **kwargs) -> Dict[str, Any]:
        """Shutdown Bookbag of Holding.

        Returns:
            Success message
        """
        lazylibrarian.SIGNAL = 'shutdown'
        return self.success(message="Shutting down")

    @api_endpoint("Restart Bookbag of Holding")
    def restart(self, **kwargs) -> Dict[str, Any]:
        """Restart Bookbag of Holding.

        Returns:
            Success message
        """
        lazylibrarian.SIGNAL = 'restart'
        return self.success(message="Restarting")
