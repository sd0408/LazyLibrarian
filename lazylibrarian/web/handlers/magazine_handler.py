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
Magazine-related web handlers for LazyLibrarian.

This module contains handler methods for magazine operations:
- Magazine listing and pagination
- Magazine subscription management
- Issue management
- Magazine search operations
"""

import datetime
import os
import threading
from shutil import copyfile
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, unquote_plus

import cherrypy

import lazylibrarian
from lazylibrarian import database, logger
from lazylibrarian.common import setperm
from lazylibrarian.formatter import (
    check_int, md5_utf8, makeUnicode, replace_all, today, plural
)
from lazylibrarian.images import createMagCover
from lazylibrarian.searchmag import search_magazines
from lazylibrarian.web.templates import serve_template


class MagazineHandler:
    """Handler class for magazine-related web operations.

    This class provides methods that can be called from the main WebInterface
    to handle magazine-related routes.
    """

    @staticmethod
    def get_magazines_page() -> str:
        """Render the magazines list page.

        Returns:
            Rendered HTML for the magazines page
        """
        if lazylibrarian.CONFIG['HTTP_LOOK'] != 'legacy':
            cookie = cherrypy.request.cookie
            user = cookie['ll_uid'].value if cookie and 'll_uid' in list(cookie.keys()) else 0

            covers = 1
            if not lazylibrarian.CONFIG['TOGGLES'] and not lazylibrarian.CONFIG['MAG_IMG']:
                covers = 0

            return serve_template(
                templatename="magazines.html",
                title="Magazines",
                magazines=[],
                covercount=covers,
                user=user
            )

        # Legacy mode - load all magazines
        myDB = database.DBConnection()
        cmd = ('SELECT magazines.*, '
               '(SELECT count(*) FROM issues WHERE magazines.title = issues.title) AS Iss_Cnt '
               'FROM magazines ORDER BY Title')
        magazines = myDB.select(cmd)

        mags = []
        covercount = 0

        if magazines:
            for mag in magazines:
                magimg = mag['LatestCover']
                if not lazylibrarian.CONFIG['IMP_MAGCOVER'] or not magimg or not os.path.isfile(magimg):
                    magimg = 'images/nocover.jpg'
                else:
                    myhash = md5_utf8(magimg)
                    hashname = os.path.join(lazylibrarian.CACHEDIR, 'magazine', '%s.jpg' % myhash)
                    if not os.path.isfile(hashname):
                        copyfile(magimg, hashname)
                        setperm(hashname)
                    magimg = 'cache/magazine/' + myhash + '.jpg'
                    covercount += 1

                this_mag = dict(mag)
                this_mag['Cover'] = magimg
                this_mag['safetitle'] = quote_plus(mag['Title'])
                mags.append(this_mag)

            if not lazylibrarian.CONFIG['MAG_IMG']:
                covercount = 0

        return serve_template(
            templatename="magazines.html",
            title="Magazines",
            magazines=mags,
            covercount=covercount
        )

    @staticmethod
    def get_issues_page(title: str) -> str:
        """Render the issues page for a magazine.

        Args:
            title: The magazine title

        Returns:
            Rendered HTML for the issues page

        Raises:
            cherrypy.HTTPRedirect: If no issues found
        """
        # Escape ampersand for HTML
        if title and '&' in title and '&amp;' not in title:
            safetitle = title.replace('&', '&amp;')
        else:
            safetitle = title

        if lazylibrarian.CONFIG['HTTP_LOOK'] != 'legacy':
            covercount = 1
            if not lazylibrarian.CONFIG['TOGGLES'] and not lazylibrarian.CONFIG['MAG_IMG']:
                covercount = 0
            return serve_template(
                templatename="issues.html",
                title=safetitle,
                issues=[],
                covercount=covercount
            )

        # Legacy mode
        myDB = database.DBConnection()
        issues = myDB.select(
            'SELECT * FROM issues WHERE Title=? ORDER BY IssueDate DESC',
            (title,)
        )

        if not issues:
            raise cherrypy.HTTPRedirect("magazines")

        mod_issues = []
        covercount = 0

        for issue in issues:
            magfile = issue['IssueFile']
            extn = os.path.splitext(magfile)[1]

            if extn:
                magimg = magfile.replace(extn, '.jpg')
                if not magimg or not os.path.isfile(magimg):
                    magimg = 'images/nocover.jpg'
                else:
                    myhash = md5_utf8(magimg)
                    hashname = os.path.join(lazylibrarian.CACHEDIR, 'magazine', myhash + ".jpg")
                    if not os.path.isfile(hashname):
                        copyfile(magimg, hashname)
                        setperm(hashname)
                    magimg = 'cache/magazine/' + myhash + '.jpg'
                    covercount += 1
            else:
                logger.debug('No extension found on %s' % magfile)
                magimg = 'images/nocover.jpg'

            this_issue = dict(issue)
            this_issue['Cover'] = magimg
            mod_issues.append(this_issue)

        logger.debug("Found %s cover%s" % (covercount, plural(covercount)))

        if not lazylibrarian.CONFIG['MAG_IMG'] or not lazylibrarian.CONFIG['IMP_MAGCOVER']:
            covercount = 0

        return serve_template(
            templatename="issues.html",
            title=safetitle,
            issues=mod_issues,
            covercount=covercount
        )

    @staticmethod
    def add_magazine(title: str) -> None:
        """Add a new magazine subscription.

        Args:
            title: Magazine title (optionally with ~reject_words)

        Raises:
            cherrypy.HTTPRedirect: To magazines page
        """
        myDB = database.DBConnection()

        if not title or title == 'None':
            raise cherrypy.HTTPRedirect("magazines")

        reject = None
        if '~' in title:
            reject = title.split('~', 1)[1].strip()
            title = title.split('~', 1)[0].strip()

        # Replace non-ASCII quotes/apostrophes with ASCII ones
        dic = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'}
        title = replace_all(title, dic)

        exists = myDB.match('SELECT Title FROM magazines WHERE Title=?', (title,))
        if exists:
            logger.debug("Magazine %s already exists (%s)" % (title, exists['Title']))
        else:
            myDB.upsert(
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
            mags = [{"bookid": title}]
            if lazylibrarian.CONFIG['IMP_AUTOSEARCH']:
                MagazineHandler.start_magazine_search(mags)

        raise cherrypy.HTTPRedirect("magazines")

    @staticmethod
    def start_magazine_search(mags: List[Dict[str, str]]) -> None:
        """Start a background search for magazines.

        Args:
            mags: List of magazine dictionaries with 'bookid' keys
        """
        if mags:
            if (lazylibrarian.USE_NZB() or lazylibrarian.USE_TOR() or
                    lazylibrarian.USE_RSS() or lazylibrarian.USE_DIRECT()):
                threading.Thread(
                    target=search_magazines,
                    name='SEARCHMAG',
                    args=[mags, False]
                ).start()
                logger.debug("Searching for magazine with title: %s" % mags[0]["bookid"])
            else:
                logger.warn("Not searching for magazine, no download methods set, check config")
        else:
            logger.debug("MagazineSearch called with no magazines")

    @staticmethod
    def search_for_magazine(bookid: str) -> None:
        """Search for a specific magazine.

        Args:
            bookid: The magazine title (URL encoded)

        Raises:
            cherrypy.HTTPRedirect: To magazines page
        """
        myDB = database.DBConnection()
        bookid = unquote_plus(bookid)

        bookdata = myDB.match('SELECT * FROM magazines WHERE Title=?', (bookid,))
        if bookdata:
            mags = [{"bookid": bookid}]
            MagazineHandler.start_magazine_search(mags)

        raise cherrypy.HTTPRedirect("magazines")

    @staticmethod
    def mark_magazines(action: Optional[str], mag_ids: Dict[str, Any]) -> None:
        """Perform bulk actions on magazines.

        Args:
            action: Action to perform (Paused, Active, Delete, Remove, Reset)
            mag_ids: Dictionary containing magazine titles as keys

        Raises:
            cherrypy.HTTPRedirect: To magazines page
        """
        myDB = database.DBConnection()
        mag_ids.pop('book_table_length', None)

        for item in mag_ids:
            title = makeUnicode(unquote_plus(item))

            if action in ["Paused", "Active"]:
                myDB.upsert("magazines", {"Status": action}, {"Title": title})
                logger.info('Status of magazine %s changed to %s' % (title, action))

            elif action == "Delete":
                issues = myDB.select('SELECT IssueFile FROM issues WHERE Title=?', (title,))
                logger.debug('Deleting magazine %s from disc' % title)
                issuedir = ''

                for issue in issues:
                    result = MagazineHandler.delete_issue_file(issue['IssueFile'])
                    if result:
                        logger.debug('Issue %s deleted from disc' % issue['IssueFile'])
                        issuedir = os.path.dirname(issue['IssueFile'])
                    else:
                        logger.debug('Failed to delete %s' % issue['IssueFile'])

                # Delete empty directory
                if issuedir and lazylibrarian.CONFIG['MAG_DELFOLDER']:
                    magdir = os.path.dirname(issuedir)
                    try:
                        os.rmdir(magdir)
                        logger.debug('Magazine directory %s deleted from disc' % magdir)
                    except OSError:
                        logger.debug('Magazine directory %s is not empty' % magdir)
                    logger.info('Magazine %s deleted from disc' % title)

            if action in ["Remove", "Delete"]:
                myDB.action('DELETE FROM magazines WHERE Title=?', (title,))
                myDB.action('DELETE FROM pastissues WHERE BookID=?', (title,))
                myDB.action('DELETE FROM wanted WHERE BookID=?', (title,))
                logger.info('Magazine %s removed from database' % title)

            elif action == "Reset":
                myDB.upsert(
                    "magazines",
                    {
                        "LastAcquired": None,
                        "IssueDate": None,
                        "LatestCover": None,
                        "IssueStatus": "Wanted"
                    },
                    {"Title": title}
                )
                logger.info('Magazine %s details reset' % title)

        raise cherrypy.HTTPRedirect("magazines")

    @staticmethod
    def mark_issues(action: Optional[str], issue_ids: Dict[str, Any]) -> None:
        """Perform bulk actions on magazine issues.

        Args:
            action: Action to perform (Delete, Remove, reCover1-4)
            issue_ids: Dictionary containing issue IDs as keys

        Raises:
            cherrypy.HTTPRedirect: To issues page or magazines page
        """
        myDB = database.DBConnection()
        title = ''
        issue_ids.pop('book_table_length', None)

        if action:
            for item in issue_ids:
                issue = myDB.match(
                    'SELECT IssueFile, Title, IssueDate FROM issues WHERE IssueID=?',
                    (item,)
                )
                if issue:
                    title = issue['Title']

                    if 'reCover' in action:
                        pagenum = check_int(action[-1], 1)
                        createMagCover(issue['IssueFile'], refresh=True, pagenum=pagenum)

                    if action == "Delete":
                        result = MagazineHandler.delete_issue_file(issue['IssueFile'])
                        if result:
                            logger.info('Issue %s of %s deleted from disc' %
                                        (issue['IssueDate'], issue['Title']))

                    if action in ["Remove", "Delete"]:
                        myDB.action('DELETE FROM issues WHERE IssueID=?', (item,))
                        logger.info('Issue %s of %s removed from database' %
                                    (issue['IssueDate'], issue['Title']))
                        _update_magazine_after_issue_removal(myDB, title)

        if title:
            raise cherrypy.HTTPRedirect("issuePage?title=%s" % quote_plus(title))
        else:
            raise cherrypy.HTTPRedirect("magazines")

    @staticmethod
    def delete_issue_file(issuefile: str) -> bool:
        """Delete an issue file and associated files.

        Args:
            issuefile: Path to the issue file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the magazine file
            if os.path.exists(issuefile):
                os.remove(issuefile)

            # Delete associated cover and OPF
            fname = os.path.splitext(issuefile)[0]
            for extn in ['.opf', '.jpg']:
                if os.path.exists(fname + extn):
                    os.remove(fname + extn)

            # Delete empty directory if configured
            if lazylibrarian.CONFIG['MAG_DELFOLDER']:
                try:
                    os.rmdir(os.path.dirname(issuefile))
                except OSError as e:
                    logger.debug('Directory %s not deleted: %s' %
                                 (os.path.dirname(issuefile), str(e)))

            return True

        except Exception as e:
            logger.warn('delete issue failed on %s, %s %s' %
                        (issuefile, type(e).__name__, str(e)))
            return False


def _update_magazine_after_issue_removal(myDB, title: str) -> None:
    """Update magazine metadata after an issue is removed.

    Args:
        myDB: Database connection
        title: Magazine title
    """
    cmd = 'SELECT IssueDate, IssueAcquired, IssueFile FROM issues WHERE title=? ORDER BY IssueDate '
    newest = myDB.match(cmd + 'DESC', (title,))
    oldest = myDB.match(cmd + 'ASC', (title,))

    if newest and oldest:
        old_acquired = ''
        new_acquired = ''
        cover = ''

        issuefile = newest['IssueFile']
        if os.path.exists(issuefile):
            cover = os.path.splitext(issuefile)[0] + '.jpg'
            mtime = os.path.getmtime(issuefile)
            new_acquired = datetime.date.isoformat(datetime.date.fromtimestamp(mtime))

        issuefile = oldest['IssueFile']
        if os.path.exists(issuefile):
            mtime = os.path.getmtime(issuefile)
            old_acquired = datetime.date.isoformat(datetime.date.fromtimestamp(mtime))

        new_values = {
            'IssueDate': newest['IssueDate'],
            'LatestCover': cover,
            'LastAcquired': new_acquired,
            'MagazineAdded': old_acquired
        }
    else:
        new_values = {
            'IssueDate': '',
            'LastAcquired': '',
            'LatestCover': '',
            'MagazineAdded': ''
        }

    myDB.upsert("magazines", new_values, {'Title': title})
