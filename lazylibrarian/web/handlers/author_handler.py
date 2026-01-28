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
Author-related web handlers for LazyLibrarian.

This module contains handler methods for author operations:
- Author listing and pagination
- Author status management (pause, resume, ignore, delete)
- Author details and editing
- Author library scanning
"""

import datetime
import os
import threading
from shutil import copyfile, rmtree
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import cherrypy

import lazylibrarian
from lazylibrarian import database, logger
from lazylibrarian.cache import cache_img
from lazylibrarian.common import setperm
from lazylibrarian.formatter import check_int, safe_unicode
from lazylibrarian.importer import addAuthorToDB, addAuthorNameToDB
from lazylibrarian.librarysync import LibraryScan
from lazylibrarian.web.templates import serve_template


# Track the last viewed author to detect page changes
_last_author = ''


class AuthorHandler:
    """Handler class for author-related web operations.

    This class provides methods that can be called from the main WebInterface
    to handle author-related routes.
    """

    @staticmethod
    def get_author_page(author_id: str, book_lang: Optional[str] = None,
                        library: str = 'eBook', ignored: bool = False) -> str:
        """Render the author details page.

        Args:
            author_id: The author's ID
            book_lang: Optional filter for book language
            library: Library type ('eBook' or 'AudioBook')
            ignored: Whether to show ignored books

        Returns:
            Rendered HTML for the author page

        Raises:
            cherrypy.HTTPRedirect: If author not found
        """
        global _last_author
        myDB = database.DBConnection()

        if ignored:
            languages = myDB.select(
                "SELECT DISTINCT BookLang FROM books WHERE AuthorID=? AND Status='Ignored'",
                (author_id,)
            )
        else:
            languages = myDB.select(
                "SELECT DISTINCT BookLang FROM books WHERE AuthorID=? AND Status!='Ignored'",
                (author_id,)
            )

        author = myDB.match("SELECT * FROM authors WHERE AuthorID=?", (author_id,))

        types = ['eBook']
        if lazylibrarian.SHOW_AUDIO:
            types.append('AudioBook')

        if not author:
            raise cherrypy.HTTPRedirect("home")

        # If we've changed author, reset to first page of new author's books
        if author_id == _last_author:
            firstpage = 'false'
        else:
            _last_author = author_id
            firstpage = 'true'

        authorname = author['AuthorName']
        if not authorname:  # still loading?
            raise cherrypy.HTTPRedirect("home")

        return serve_template(
            templatename="author.html",
            title=quote_plus(authorname),
            author=author,
            languages=languages,
            booklang=book_lang,
            types=types,
            library=library,
            ignored=ignored,
            showseries=lazylibrarian.SHOW_SERIES,
            firstpage=firstpage
        )

    @staticmethod
    def set_author_status(author_id: str, status: str) -> None:
        """Set an author's status.

        Args:
            author_id: The author's ID
            status: New status (Active, Paused, Wanted, Ignored)

        Raises:
            cherrypy.HTTPRedirect: To author page or home
        """
        myDB = database.DBConnection()
        authorsearch = myDB.match(
            'SELECT AuthorName FROM authors WHERE AuthorID=?',
            (author_id,)
        )

        if authorsearch:
            author_name = authorsearch['AuthorName']
            logger.info("%s author: %s" % (status, author_name))

            myDB.upsert("authors", {'Status': status}, {'AuthorID': author_id})
            logger.debug(
                'AuthorID [%s]-[%s] %s - redirecting to Author home page' %
                (author_id, author_name, status)
            )
            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)
        else:
            logger.debug('setAuthor Invalid authorid [%s]' % author_id)
            raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def remove_author(author_id: str) -> None:
        """Remove an author from the database.

        Args:
            author_id: The author's ID

        Raises:
            cherrypy.HTTPRedirect: To home page
        """
        myDB = database.DBConnection()
        authorsearch = myDB.match(
            'SELECT AuthorName FROM authors WHERE AuthorID=?',
            (author_id,)
        )

        if authorsearch:
            author_name = authorsearch['AuthorName']
            logger.info("Removing all references to author: %s" % author_name)
            myDB.action('DELETE FROM authors WHERE AuthorID=?', (author_id,))

        raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def refresh_author(author_id: str) -> None:
        """Refresh an author's metadata from the source.

        Args:
            author_id: The author's ID

        Raises:
            cherrypy.HTTPRedirect: To author page or home
        """
        myDB = database.DBConnection()
        authorsearch = myDB.match(
            'SELECT AuthorName FROM authors WHERE AuthorID=?',
            (author_id,)
        )

        if authorsearch:
            threading.Thread(
                target=addAuthorToDB,
                name='REFRESHAUTHOR',
                args=[None, True, author_id]
            ).start()
            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)
        else:
            logger.debug('refreshAuthor Invalid authorid [%s]' % author_id)
            raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def add_author_by_name(author_name: str) -> None:
        """Add an author to the database by name.

        Args:
            author_name: The author's name

        Raises:
            cherrypy.HTTPRedirect: To home page
        """
        threading.Thread(
            target=addAuthorNameToDB,
            name='ADDAUTHOR',
            args=[author_name, False]
        ).start()
        raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def add_author_by_id(author_id: str) -> None:
        """Add an author to the database by ID.

        Args:
            author_id: The author's ID

        Raises:
            cherrypy.HTTPRedirect: To author page
        """
        import time
        threading.Thread(
            target=addAuthorToDB,
            name='ADDAUTHOR',
            args=['', False, author_id]
        ).start()
        time.sleep(2)  # so we get some data before going to authorpage
        raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)

    @staticmethod
    def toggle_ignored_authors() -> None:
        """Toggle between showing active and ignored authors.

        Raises:
            cherrypy.HTTPRedirect: To home page
        """
        lazylibrarian.IGNORED_AUTHORS = not lazylibrarian.IGNORED_AUTHORS
        raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def mark_authors(action: Optional[str], redirect: Optional[str],
                     author_ids: Dict[str, Any]) -> None:
        """Perform bulk actions on multiple authors.

        Args:
            action: The action to perform (Active, Wanted, Paused, Ignored, Delete, Remove)
            redirect: Page to redirect to after action
            author_ids: Dictionary containing author IDs as keys

        Raises:
            cherrypy.HTTPRedirect: To redirect page
        """
        myDB = database.DBConnection()

        # Remove non-author-id keys
        for key in ['author_table_length', 'ignored']:
            author_ids.pop(key, None)

        if not redirect:
            redirect = "home"

        if action:
            for authorid in author_ids:
                check = myDB.match(
                    "SELECT AuthorName FROM authors WHERE AuthorID=?",
                    (authorid,)
                )
                if not check:
                    logger.warn('Unable to set Status to "%s" for "%s"' % (action, authorid))
                elif action in ["Active", "Wanted", "Paused", "Ignored"]:
                    myDB.upsert("authors", {'Status': action}, {'AuthorID': authorid})
                    logger.info('Status set to "%s" for "%s"' % (action, check['AuthorName']))
                elif action == "Delete":
                    logger.info("Removing author and books: %s" % check['AuthorName'])
                    books = myDB.select(
                        "SELECT BookFile FROM books WHERE AuthorID=? AND BookFile IS NOT NULL",
                        (authorid,)
                    )
                    for book in books:
                        if os.path.exists(book['BookFile']):
                            try:
                                rmtree(os.path.dirname(book['BookFile']), ignore_errors=True)
                            except Exception as e:
                                logger.warn(
                                    'rmtree failed on %s, %s %s' %
                                    (book['BookFile'], type(e).__name__, str(e))
                                )
                    myDB.action('DELETE FROM authors WHERE AuthorID=?', (authorid,))
                elif action == "Remove":
                    logger.info("Removing author: %s" % check['AuthorName'])
                    myDB.action('DELETE FROM authors WHERE AuthorID=?', (authorid,))

        raise cherrypy.HTTPRedirect(redirect)

    @staticmethod
    def library_scan_author(author_id: str, library: str = 'eBook') -> None:
        """Scan the library for a specific author's books.

        Args:
            author_id: The author's ID
            library: Library type ('eBook' or 'AudioBook')

        Raises:
            cherrypy.HTTPRedirect: To author page or home
        """
        myDB = database.DBConnection()
        authorsearch = myDB.match(
            'SELECT AuthorName FROM authors WHERE AuthorID=?',
            (author_id,)
        )

        if authorsearch:
            author_name = authorsearch['AuthorName']

            if library == 'AudioBook':
                authordir = safe_unicode(
                    os.path.join(lazylibrarian.DIRECTORY('AudioBook'), author_name)
                )
            else:
                authordir = safe_unicode(
                    os.path.join(lazylibrarian.DIRECTORY('eBook'), author_name)
                )

            if not os.path.isdir(authordir):
                # Try with different capitalization
                author_name_cap = ' '.join(
                    word[0].upper() + word[1:] for word in author_name.split()
                )
                if library == 'AudioBook':
                    authordir = safe_unicode(
                        os.path.join(lazylibrarian.DIRECTORY('Audio'), author_name_cap)
                    )
                else:
                    authordir = safe_unicode(
                        os.path.join(lazylibrarian.DIRECTORY('eBook'), author_name_cap)
                    )

            if not os.path.isdir(authordir):
                # Try to find from existing book
                sourcefile = 'AudioFile' if library == 'AudioBook' else 'BookFile'
                cmd = 'SELECT %s FROM books, authors WHERE books.AuthorID = authors.AuthorID' % sourcefile
                cmd += ' AND AuthorName=? AND %s <> ""' % sourcefile
                anybook = myDB.match(cmd, (author_name,))
                if anybook:
                    authordir = safe_unicode(
                        os.path.dirname(os.path.dirname(anybook[sourcefile]))
                    )

            if os.path.isdir(authordir):
                remove = bool(lazylibrarian.CONFIG['FULL_SCAN'])
                try:
                    threading.Thread(
                        target=LibraryScan,
                        name='AUTHOR_SCAN',
                        args=[authordir, library, author_id, remove]
                    ).start()
                except Exception as e:
                    logger.error('Unable to complete the scan: %s %s' % (type(e).__name__, str(e)))
            else:
                logger.warn('Unable to find author directory: %s' % authordir)

            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s&library=%s" % (author_id, library))
        else:
            logger.debug('ScanAuthor Invalid authorid [%s]' % author_id)
            raise cherrypy.HTTPRedirect("home")

    @staticmethod
    def get_edit_author_page(author_id: str) -> str:
        """Render the author edit page.

        Args:
            author_id: The author's ID

        Returns:
            Rendered HTML for the edit author page
        """
        myDB = database.DBConnection()
        data = myDB.match('SELECT * FROM authors WHERE AuthorID=?', (author_id,))

        if data:
            return serve_template(
                templatename="editauthor.html",
                title="Edit Author",
                config=data
            )
        else:
            logger.info('Missing author %s' % author_id)
            return ''

    @staticmethod
    def update_author(author_id: str, author_name: str, author_born: str,
                      author_death: str, author_img: str, manual: str = '0') -> None:
        """Update author details.

        Args:
            author_id: The author's ID
            author_name: Updated author name
            author_born: Birth date (YYYY/MM/DD format)
            author_death: Death date (YYYY/MM/DD format)
            author_img: Image URL or file path
            manual: Whether manually edited ('0' or '1')

        Raises:
            cherrypy.HTTPRedirect: To author page or authors list
        """
        myDB = database.DBConnection()

        if author_id:
            authdata = myDB.match('SELECT * FROM authors WHERE AuthorID=?', (author_id,))
            if authdata:
                edited = ""

                # Normalize empty values
                if not author_born or author_born == 'None':
                    author_born = None
                if not author_death or author_death == 'None':
                    author_death = None
                if author_img == 'None':
                    author_img = ''
                manual_bool = bool(check_int(manual, 0))

                # Track what changed
                if authdata["AuthorBorn"] != author_born:
                    edited += "Born "
                if authdata["AuthorDeath"] != author_death:
                    edited += "Died "
                if author_img and authdata["AuthorImg"] != author_img:
                    edited += "Image "
                if bool(check_int(authdata["Manual"], 0)) != manual_bool:
                    edited += "Manual "

                if authdata["AuthorName"] != author_name:
                    match = myDB.match(
                        'SELECT AuthorName FROM authors WHERE AuthorName=?',
                        (author_name,)
                    )
                    if match:
                        logger.debug("Unable to rename, new author name %s already exists" % author_name)
                        author_name = authdata["AuthorName"]
                    else:
                        edited += "Name "

                if edited:
                    # Validate and process dates
                    author_born = _validate_date(author_born, authdata["AuthorBorn"], "Born")
                    if author_born == authdata["AuthorBorn"]:
                        edited = edited.replace('Born ', '')

                    author_death = _validate_date(author_death, authdata["AuthorDeath"], "Died")
                    if author_death == authdata["AuthorDeath"]:
                        edited = edited.replace('Died ', '')

                    # Validate and cache image
                    if not author_img:
                        author_img = authdata["AuthorImg"]
                    else:
                        author_img, success = _cache_author_image(author_id, author_img)
                        if not success:
                            author_img = authdata["AuthorImg"]
                            edited = edited.replace('Image ', '')

                    myDB.upsert(
                        "authors",
                        {
                            'AuthorName': author_name,
                            'AuthorBorn': author_born,
                            'AuthorDeath': author_death,
                            'AuthorImg': author_img,
                            'Manual': manual_bool
                        },
                        {'AuthorID': author_id}
                    )
                    logger.info('Updated [%s] for %s' % (edited, author_name))
                else:
                    logger.debug('Author [%s] has not been changed' % author_name)

            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)
        else:
            raise cherrypy.HTTPRedirect("authors")


def _validate_date(date_str: Optional[str], current_value: Optional[str],
                   date_type: str) -> Optional[str]:
    """Validate a date string in YYYY/MM/DD format.

    Args:
        date_str: The date string to validate
        current_value: The current value to return if validation fails
        date_type: Type of date for logging ("Born" or "Died")

    Returns:
        The validated date string or current_value if invalid
    """
    if date_str is None:
        return current_value

    if not date_str:
        return current_value

    if len(date_str) != 10:
        logger.warn("Author %s date [%s] rejected" % (date_type, date_str))
        return current_value

    try:
        datetime.date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:]))
        return date_str
    except ValueError:
        logger.warn("Author %s date [%s] rejected" % (date_type, date_str))
        return current_value


def _cache_author_image(author_id: str, image_path: str) -> Tuple[str, bool]:
    """Cache an author image from file or URL.

    Args:
        author_id: The author's ID
        image_path: Path to local file, URL, or 'none' for default

    Returns:
        Tuple of (cached image path, success boolean)
    """
    if image_path == 'none':
        return os.path.join(lazylibrarian.PROG_DIR, 'data', 'images', 'nophoto.png'), True

    # Try local file
    if os.path.isfile(image_path):
        extn = os.path.splitext(image_path)[1].lower()
        if extn in ['.jpg', '.jpeg', '.png']:
            destfile = os.path.join(lazylibrarian.CACHEDIR, 'author', author_id + '.jpg')
            try:
                copyfile(image_path, destfile)
                setperm(destfile)
                return 'cache/author/' + author_id + '.jpg', True
            except Exception as why:
                logger.warn(
                    "Failed to copy file %s, %s %s" %
                    (image_path, type(why).__name__, str(why))
                )

    # Try URL
    if image_path.startswith('http'):
        extn = os.path.splitext(image_path)[1].lower()
        if extn in ['.jpg', '.jpeg', '.png']:
            cached_path, success, _ = cache_img("author", author_id, image_path)
            if success:
                return cached_path, True

    logger.warn("Author Image [%s] rejected" % image_path)
    return image_path, False
