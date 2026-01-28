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
Magazine API endpoints for LazyLibrarian.

This module contains API methods for magazine operations:
- List magazines
- Get magazine issues
- Add/remove magazines
- Search for magazines
"""

import threading
from typing import Any, Dict, List

from lazylibrarian import logger
from lazylibrarian.api_v2.base import ApiBase, api_endpoint, require_param
from lazylibrarian.formatter import replace_all, today
from lazylibrarian.images import createMagCover, createMagCovers
from lazylibrarian.searchmag import search_magazines


class MagazineApi(ApiBase):
    """API handler for magazine-related endpoints."""

    @api_endpoint("List magazines")
    def get_magazines(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all magazines.

        Returns:
            List of magazine dictionaries
        """
        return self.get_all_magazines()

    @api_endpoint("List issues of named magazine", ["&name= magazine title"])
    @require_param('name')
    def get_issues(self, **kwargs) -> Dict[str, Any]:
        """Get issues for a magazine.

        Args:
            name: Magazine title

        Returns:
            List of issue dictionaries
        """
        title = kwargs['name']

        magazine = self.get_magazine_by_title(title)
        if not magazine:
            return self.error("Magazine not found: %s" % title)

        issues = self.get_issues_by_title(title)
        return self.success(data=issues)

    @api_endpoint("Get name of issue from path/filename", ["&name= path or filename"])
    @require_param('name')
    def get_issue_name(self, **kwargs) -> Dict[str, Any]:
        """Parse issue name from a path or filename.

        Args:
            name: Path or filename

        Returns:
            Parsed issue information
        """
        from lazylibrarian.searchmag import get_issue_date

        name = kwargs['name']
        issue_date, issue_type = get_issue_date(name)

        if issue_date:
            return self.success({
                "issue_date": issue_date,
                "issue_type": issue_type
            })
        else:
            return self.error("Could not parse issue date from: %s" % name)

    @api_endpoint("Create covers for magazines", ["&wait= wait for completion",
                                                   "&refresh= refresh existing"])
    def create_mag_covers(self, **kwargs) -> Dict[str, Any]:
        """Create cover images for all magazines.

        Args:
            wait: Whether to wait for completion
            refresh: Whether to refresh existing covers

        Returns:
            Success message
        """
        wait = kwargs.get('wait', False)
        refresh = kwargs.get('refresh', False)

        t = threading.Thread(
            target=createMagCovers,
            name='MAGCOVERS',
            args=[refresh]
        )
        t.start()

        if wait:
            t.join()
            return self.success(message="Magazine covers created")
        else:
            return self.success(message="Magazine cover creation started")

    @api_endpoint("Create cover for magazine issue",
                  ["&file= issue file path", "&refresh= refresh existing", "&page= page number"])
    @require_param('file')
    def create_mag_cover(self, **kwargs) -> Dict[str, Any]:
        """Create a cover image for a single magazine issue.

        Args:
            file: Path to the issue file
            refresh: Whether to refresh existing cover
            page: Page number to use for cover

        Returns:
            Success or error
        """
        import os

        issue_file = kwargs['file']
        refresh = kwargs.get('refresh', False)
        page = int(kwargs.get('page', 1))

        if not os.path.isfile(issue_file):
            return self.error("File not found: %s" % issue_file)

        cover = createMagCover(issue_file, refresh=refresh, pagenum=page)
        if cover:
            return self.success({"cover": cover})
        else:
            return self.error("Failed to create cover for: %s" % issue_file)

    @api_endpoint("Add magazine to database by name", ["&name= magazine title"])
    @require_param('name')
    def add_magazine(self, **kwargs) -> Dict[str, Any]:
        """Add a magazine subscription.

        Args:
            name: Magazine title (optionally with ~reject_words)

        Returns:
            Success or error
        """
        title = kwargs['name']

        if not title or title == 'None':
            return self.error("Invalid magazine title")

        reject = None
        if '~' in title:
            reject = title.split('~', 1)[1].strip()
            title = title.split('~', 1)[0].strip()

        # Replace non-ASCII quotes
        dic = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'}
        title = replace_all(title, dic)

        existing = self.db.match("SELECT Title FROM magazines WHERE Title=?", (title,))
        if existing:
            return self.error("Magazine already exists: %s" % title)

        self.db.upsert(
            "magazines",
            {
                "Regex": None,
                "Reject": reject,
                "DateType": "",
                "Status": "Active",
                "MagazineAdded": today(),
                "IssueStatus": "Wanted"
            },
            {"Title": title}
        )
        logger.info("Added magazine: %s" % title)

        return self.success(message="Added magazine: %s" % title)

    @api_endpoint("Remove magazine from database", ["&name= magazine title"])
    @require_param('name')
    def remove_magazine(self, **kwargs) -> Dict[str, Any]:
        """Remove a magazine subscription.

        Args:
            name: Magazine title

        Returns:
            Success or error
        """
        title = kwargs['name']

        magazine = self.get_magazine_by_title(title)
        if not magazine:
            return self.error("Magazine not found: %s" % title)

        self.db.action('DELETE FROM magazines WHERE Title=?', (title,))
        self.db.action('DELETE FROM pastissues WHERE BookID=?', (title,))
        self.db.action('DELETE FROM wanted WHERE BookID=?', (title,))
        logger.info("Removed magazine: %s" % title)

        return self.success(message="Removed magazine: %s" % title)

    @api_endpoint("Search for all wanted magazines", ["&wait= wait for completion"])
    def force_mag_search(self, **kwargs) -> Dict[str, Any]:
        """Force a search for all wanted magazines.

        Args:
            wait: Whether to wait for completion

        Returns:
            Success message
        """
        import lazylibrarian

        wait = kwargs.get('wait', False)

        if not (lazylibrarian.USE_NZB() or lazylibrarian.USE_TOR() or
                lazylibrarian.USE_RSS() or lazylibrarian.USE_DIRECT()):
            return self.error("No search methods enabled, check config")

        t = threading.Thread(target=search_magazines, name='SEARCHMAG', args=[None, False])
        t.start()

        if wait:
            t.join()
            return self.success(message="Magazine search completed")
        else:
            return self.success(message="Magazine search started")
