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
Book-related web handlers for LazyLibrarian.

This module contains handler methods for book operations:
- Book listing and pagination
- Book status management (wanted, have, ignored, skipped)
- Book details and editing
- Book search operations
"""

import datetime
import os
import threading
from shutil import copyfile, rmtree
from typing import Any, Dict, List, Optional

import cherrypy

import lazylibrarian
from lazylibrarian import database, logger
from lazylibrarian.bookwork import setSeries, deleteEmptySeries
from lazylibrarian.calibre import calibredb
from lazylibrarian.formatter import check_int, getList, cleanName, unaccented, unaccented_str, check_year
from lazylibrarian.gb import GoogleBooks
from lazylibrarian.images import getBookCover
from lazylibrarian.importer import update_totals
from lazylibrarian.searchbook import search_book
from lazylibrarian.web.templates import serve_template


class BookHandler:
    """Handler class for book-related web operations.

    This class provides methods that can be called from the main WebInterface
    to handle book-related routes.
    """

    @staticmethod
    def get_books_page(book_lang: Optional[str] = None) -> str:
        """Render the books list page.

        Args:
            book_lang: Optional filter for book language

        Returns:
            Rendered HTML for the books page
        """
        cookie = cherrypy.request.cookie
        user = cookie['ll_uid'].value if cookie and 'll_uid' in list(cookie.keys()) else 0

        myDB = database.DBConnection()
        if not book_lang or book_lang == 'None':
            book_lang = None

        languages = myDB.select(
            'SELECT DISTINCT BookLang FROM books WHERE STATUS!="Skipped" AND STATUS!="Ignored"'
        )
        return serve_template(
            templatename="books.html",
            title='Books',
            books=[],
            languages=languages,
            booklang=book_lang,
            user=user
        )

    @staticmethod
    def get_audio_page(book_lang: Optional[str] = None) -> str:
        """Render the audiobooks list page.

        Args:
            book_lang: Optional filter for book language

        Returns:
            Rendered HTML for the audiobooks page
        """
        cookie = cherrypy.request.cookie
        user = cookie['ll_uid'].value if cookie and 'll_uid' in list(cookie.keys()) else 0

        myDB = database.DBConnection()
        if not book_lang or book_lang == 'None':
            book_lang = None

        languages = myDB.select(
            'SELECT DISTINCT BookLang FROM books WHERE AUDIOSTATUS!="Skipped" AND AUDIOSTATUS!="Ignored"'
        )
        return serve_template(
            templatename="audio.html",
            title='AudioBooks',
            books=[],
            languages=languages,
            booklang=book_lang,
            user=user
        )

    @staticmethod
    def add_book(bookid: str) -> None:
        """Add a book to the wanted list.

        Args:
            bookid: The book's ID

        Raises:
            cherrypy.HTTPRedirect: To author page or books page
        """
        myDB = database.DBConnection()
        author_id = ""

        match = myDB.match('SELECT AuthorID FROM books WHERE BookID=?', (bookid,))
        if match:
            myDB.upsert("books", {'Status': 'Wanted'}, {'BookID': bookid})
            author_id = match['AuthorID']
            update_totals(author_id)
        else:
            GB = GoogleBooks(bookid)
            t = threading.Thread(target=GB.find_book, name='GB-BOOK', args=[bookid, "Wanted"])
            t.start()
            t.join(timeout=10)

        if lazylibrarian.CONFIG['IMP_AUTOSEARCH']:
            books = [{"bookid": bookid}]
            BookHandler.start_book_search(books)

        if author_id:
            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)
        else:
            raise cherrypy.HTTPRedirect("books")

    @staticmethod
    def start_book_search(books: List[Dict[str, str]], library: Optional[str] = None) -> None:
        """Start a background search for books.

        Args:
            books: List of book dictionaries with 'bookid' keys
            library: Library type ('eBook' or 'AudioBook')
        """
        if books:
            if (lazylibrarian.USE_NZB() or lazylibrarian.USE_TOR() or
                    lazylibrarian.USE_RSS() or lazylibrarian.USE_DIRECT()):
                threading.Thread(
                    target=search_book,
                    name='SEARCHBOOK',
                    args=[books, library]
                ).start()
                booktype = library if library else 'book'
                logger.debug("Searching for %s with id: %s" % (booktype, books[0]["bookid"]))
            else:
                logger.warn("Not searching for book, no search methods set, check config.")
        else:
            logger.debug("BookSearch called with no books")

    @staticmethod
    def search_for_book(bookid: str, library: Optional[str] = None) -> None:
        """Search for a specific book.

        Args:
            bookid: The book's ID
            library: Library type ('eBook' or 'AudioBook')

        Raises:
            cherrypy.HTTPRedirect: To author page or books page
        """
        myDB = database.DBConnection()
        author_id = ''

        bookdata = myDB.match('SELECT AuthorID FROM books WHERE BookID=?', (bookid,))
        if bookdata:
            author_id = bookdata["AuthorID"]
            books = [{"bookid": bookid}]
            BookHandler.start_book_search(books, library=library)

        if author_id:
            raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s" % author_id)
        else:
            raise cherrypy.HTTPRedirect("books")

    @staticmethod
    def get_edit_book_page(bookid: str) -> str:
        """Render the book edit page.

        Args:
            bookid: The book's ID

        Returns:
            Rendered HTML for the edit book page
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        myDB = database.DBConnection()

        authors = myDB.select(
            "SELECT AuthorName FROM authors WHERE Status!='Ignored' ORDER BY AuthorName COLLATE NOCASE"
        )

        cmd = ('SELECT BookName, BookID, BookSub, BookGenre, BookLang, BookDesc, books.Manual, '
               'AuthorName, books.AuthorID, BookDate FROM books, authors '
               'WHERE books.AuthorID = authors.AuthorID AND BookID=?')
        bookdata = myDB.match(cmd, (bookid,))

        cmd = ('SELECT SeriesName, SeriesNum FROM member, series '
               'WHERE series.SeriesID=member.SeriesID AND BookID=?')
        seriesdict = myDB.select(cmd, (bookid,))

        if bookdata:
            covers = []
            for source in ['current', 'cover', 'librarything', 'whatwork',
                           'openlibrary', 'googleisbn', 'googleimage']:
                cover, _ = getBookCover(bookid, source)
                if cover:
                    covers.append([source, cover])

            return serve_template(
                templatename="editbook.html",
                title="Edit Book",
                config=bookdata,
                seriesdict=seriesdict,
                authors=authors,
                covers=covers
            )
        else:
            logger.info('Missing book %s' % bookid)
            return ''

    @staticmethod
    def update_book(bookid: str, bookname: str, booksub: str, bookgenre: str,
                    booklang: str, bookdate: str, manual: str, authorname: str,
                    cover: str, newid: str, editordata: str, **kwargs) -> None:
        """Update book details.

        Args:
            bookid: The book's ID
            bookname: Updated book name
            booksub: Book subtitle
            bookgenre: Book genre
            booklang: Book language
            bookdate: Publication date
            manual: Whether manually edited ('0' or '1')
            authorname: Author name
            cover: Cover source to use
            newid: New book ID (not currently supported)
            editordata: Book description
            **kwargs: Series data

        Raises:
            cherrypy.HTTPRedirect: To edit book page or books list
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        myDB = database.DBConnection()

        if not bookid:
            raise cherrypy.HTTPRedirect("books")

        cmd = ('SELECT BookName, BookSub, BookGenre, BookLang, BookImg, BookDate, BookDesc, '
               'books.Manual, AuthorName, books.AuthorID FROM books, authors '
               'WHERE books.AuthorID = authors.AuthorID AND BookID=?')
        bookdata = myDB.match(cmd, (bookid,))

        if not bookdata:
            raise cherrypy.HTTPRedirect("books")

        edited = ''
        moved = False

        if bookgenre == 'None':
            bookgenre = ''
        manual_bool = bool(check_int(manual, 0))

        # Check for BookID change (not currently supported)
        if newid and bookid != newid:
            cmd = ("SELECT BookName, AuthorName FROM books, authors "
                   "WHERE books.AuthorID = authors.AuthorID AND BookID=?")
            match = myDB.match(cmd, (newid,))
            if match:
                logger.warn("Cannot change bookid to %s, in use by %s/%s" %
                            (newid, match['BookName'], match['AuthorName']))
            else:
                logger.warn("Updating bookid is not supported yet")

        # Track what changed
        if bookdata["BookName"] != bookname:
            edited += "Title "
        if bookdata["BookSub"] != booksub:
            edited += "Subtitle "
        if bookdata["BookDesc"] != editordata:
            edited += "Description "
        if bookdata["BookGenre"] != bookgenre:
            edited += "Genre "
        if bookdata["BookLang"] != booklang:
            edited += "Language "
        if bookdata["BookDate"] != bookdate:
            if bookdate == '0000':
                edited += "Date "
            elif _validate_book_date(bookdate):
                edited += "Date "
            else:
                bookdate = bookdata["BookDate"]
        if bool(check_int(bookdata["Manual"], 0)) != manual_bool:
            edited += "Manual "
        if bookdata["AuthorName"] != authorname:
            moved = True

        # Handle cover change
        coverlink = _process_cover_change(bookid, cover, bookdata['BookImg'])
        if coverlink != bookdata['BookImg']:
            edited += 'Cover '

        # Update database
        if edited:
            myDB.upsert(
                "books",
                {
                    'BookName': bookname,
                    'BookSub': booksub,
                    'BookGenre': bookgenre,
                    'BookLang': booklang,
                    'BookDate': bookdate,
                    'BookDesc': editordata,
                    'BookImg': coverlink,
                    'Manual': manual_bool
                },
                {'BookID': bookid}
            )

        # Handle series changes
        series_edited = _process_series_changes(myDB, bookid, kwargs)
        if series_edited:
            edited += "Series "

        if edited:
            logger.info('Updated [%s] for %s' % (edited, bookname))
        else:
            logger.debug('Book [%s] has not been changed' % bookname)

        # Handle author move
        if moved:
            authordata = myDB.match('SELECT AuthorID FROM authors WHERE AuthorName=?', (authorname,))
            if authordata:
                myDB.upsert("books", {'AuthorID': authordata['AuthorID']}, {'BookID': bookid})
                update_totals(bookdata["AuthorID"])
                update_totals(authordata['AuthorID'])
                logger.info('Book [%s] has been moved' % bookname)
        else:
            logger.debug('Book [%s] has not been moved' % bookname)

        raise cherrypy.HTTPRedirect("editBook?bookid=%s" % bookid)

    @staticmethod
    def mark_books(author_id: Optional[str], series_id: Optional[str],
                   action: Optional[str], redirect: Optional[str],
                   book_ids: Dict[str, Any]) -> None:
        """Perform bulk actions on multiple books.

        Args:
            author_id: Author ID for redirect
            series_id: Series ID for redirect
            action: Action to perform (Wanted, Have, Ignored, Skipped, Remove, Delete, etc.)
            redirect: Page to redirect to
            book_ids: Dictionary containing book IDs as keys

        Raises:
            cherrypy.HTTPRedirect: To redirect page
        """
        library = book_ids.get('library', 'eBook')
        if redirect == 'audio':
            library = 'AudioBook'
        if 'marktype' in book_ids:
            library = book_ids['marktype']

        # Remove non-book-id keys
        for key in ['book_table_length', 'ignored', 'library', 'booklang', 'marktype']:
            book_ids.pop(key, None)

        myDB = database.DBConnection()
        if not redirect:
            redirect = "books"

        check_totals = []
        if redirect == 'author' and author_id:
            check_totals = [author_id]

        if action:
            for bookid in book_ids:
                _process_book_action(myDB, bookid, action, library, check_totals)

        # Update author totals
        for author in check_totals:
            update_totals(author)

        # Start search for wanted books
        if action == 'Wanted':
            _start_wanted_search(book_ids, library)

        # Handle redirect
        _handle_book_redirect(redirect, author_id, series_id, library)


def _validate_book_date(bookdate: str) -> bool:
    """Validate a book date string.

    Args:
        bookdate: Date string in YYYY, YYYY-MM, or YYYY-MM-DD format

    Returns:
        True if valid, False otherwise
    """
    try:
        if len(bookdate) == 4:
            return bool(check_year(bookdate))
        elif len(bookdate) == 7:
            if not check_year(bookdate[:4]):
                return False
            datetime.date(int(bookdate[:4]), int(bookdate[5:7]), 1)
            return True
        elif len(bookdate) == 10:
            if not check_year(bookdate[:4]):
                return False
            datetime.date(int(bookdate[:4]), int(bookdate[5:7]), int(bookdate[8:]))
            return True
    except ValueError:
        pass
    return False


def _process_cover_change(bookid: str, cover: str, current_img: str) -> str:
    """Process a cover source change.

    Args:
        bookid: The book's ID
        cover: Cover source identifier
        current_img: Current image path

    Returns:
        New cover link
    """
    cover_map = {
        'librarything': '_lt',
        'whatwork': '_ww',
        'openlibrary': '_ol',
        'googleisbn': '_gi',
        'googleimage': '_gb'
    }

    covertype = cover_map.get(cover, '')
    if not covertype:
        return current_img

    cachedir = lazylibrarian.CACHEDIR
    coverfile = os.path.join(cachedir, "book", bookid + '.jpg')
    newcoverfile = os.path.join(cachedir, "book", bookid + covertype + '.jpg')

    if os.path.exists(newcoverfile):
        copyfile(newcoverfile, coverfile)
        return 'cache/book/' + bookid + '.jpg'

    return current_img


def _process_series_changes(myDB, bookid: str, kwargs: Dict[str, Any]) -> bool:
    """Process series membership changes.

    Args:
        myDB: Database connection
        bookid: The book's ID
        kwargs: Form data containing series information

    Returns:
        True if series were changed
    """
    cmd = ('SELECT SeriesName, SeriesNum, series.SeriesID FROM member, series '
           'WHERE series.SeriesID=member.SeriesID AND BookID=?')
    old_series = myDB.select(cmd, (bookid,))

    old_list = [[item['SeriesID'], item['SeriesNum'], item['SeriesName']] for item in old_series]
    new_list = []

    dict_counter = 0
    while "series[%s][name]" % dict_counter in kwargs:
        s_name = kwargs["series[%s][name]" % dict_counter]
        s_name = cleanName(unaccented(s_name), '&/')
        s_num = kwargs["series[%s][number]" % dict_counter]
        match = myDB.match('SELECT SeriesID FROM series WHERE SeriesName=?', (s_name,))
        if match:
            new_list.append([match['SeriesID'], s_num, s_name])
        else:
            new_list.append(['', s_num, s_name])
        dict_counter += 1

    if 'series[new][name]' in kwargs and 'series[new][number]' in kwargs:
        if kwargs['series[new][name]']:
            s_name = cleanName(unaccented(kwargs["series[new][name]"]), '&/')
            s_num = kwargs['series[new][number]']
            new_list.append(['', s_num, s_name])

    # Check if series changed
    series_changed = False
    for item in old_list:
        if item[1:] not in [i[1:] for i in new_list]:
            series_changed = True
    for item in new_list:
        if item[1:] not in [i[1:] for i in old_list]:
            series_changed = True

    if series_changed:
        setSeries(new_list, bookid)
        deleteEmptySeries()

    return series_changed


def _process_book_action(myDB, bookid: str, action: str, library: str,
                         check_totals: List[str]) -> None:
    """Process a single book action.

    Args:
        myDB: Database connection
        bookid: The book's ID
        action: Action to perform
        library: Library type
        check_totals: List of author IDs to update totals for
    """
    if action in ["Unread", "Read", "ToRead"]:
        _process_read_status(myDB, bookid, action)
    elif action in ["Wanted", "Have", "Ignored", "Skipped"]:
        _process_status_change(myDB, bookid, action, library, check_totals)
    elif action == "NoDelay":
        myDB.action("DELETE FROM failedsearch WHERE BookID=? AND Library=?", (bookid, library))
        logger.debug('%s delay set to zero for %s' % (library, bookid))
    elif action in ["Remove", "Delete"]:
        _process_book_removal(myDB, bookid, action, library, check_totals)


def _process_read_status(myDB, bookid: str, action: str) -> None:
    """Update read/to-read status for a book."""
    cookie = cherrypy.request.cookie
    if not (cookie and 'll_uid' in list(cookie.keys())):
        return

    res = myDB.match(
        'SELECT ToRead, HaveRead FROM users WHERE UserID=?',
        (cookie['ll_uid'].value,)
    )
    if not res:
        return

    to_read = getList(res['ToRead'])
    have_read = getList(res['HaveRead'])

    if action == "Unread":
        if bookid in to_read:
            to_read.remove(bookid)
        if bookid in have_read:
            have_read.remove(bookid)
        logger.debug('Status set to "unread" for "%s"' % bookid)
    elif action == "Read":
        if bookid in to_read:
            to_read.remove(bookid)
        if bookid not in have_read:
            have_read.append(bookid)
        logger.debug('Status set to "read" for "%s"' % bookid)
    elif action == "ToRead":
        if bookid not in to_read:
            to_read.append(bookid)
        if bookid in have_read:
            have_read.remove(bookid)
        logger.debug('Status set to "to read" for "%s"' % bookid)

    to_read = list(set(to_read))
    have_read = list(set(have_read))
    myDB.action(
        'UPDATE users SET ToRead=?, HaveRead=? WHERE UserID=?',
        (', '.join(to_read), ', '.join(have_read), cookie['ll_uid'].value)
    )


def _process_status_change(myDB, bookid: str, action: str, library: str,
                           check_totals: List[str]) -> None:
    """Update book status (Wanted, Have, etc.)."""
    bookdata = myDB.match('SELECT AuthorID, BookName FROM books WHERE BookID=?', (bookid,))
    if not bookdata:
        return

    authorid = bookdata['AuthorID']
    bookname = bookdata['BookName']
    if authorid not in check_totals:
        check_totals.append(authorid)

    if 'eBook' in library:
        myDB.upsert("books", {'Status': action}, {'BookID': bookid})
        logger.debug('Status set to "%s" for "%s"' % (action, bookname))
    if 'Audio' in library:
        myDB.upsert("books", {'AudioStatus': action}, {'BookID': bookid})
        logger.debug('AudioStatus set to "%s" for "%s"' % (action, bookname))


def _process_book_removal(myDB, bookid: str, action: str, library: str,
                          check_totals: List[str]) -> None:
    """Process book removal or deletion."""
    bookdata = myDB.match(
        'SELECT AuthorID, BookName, BookFile, AudioFile FROM books WHERE BookID=?',
        (bookid,)
    )
    if not bookdata:
        return

    authorid = bookdata['AuthorID']
    bookname = bookdata['BookName']
    if authorid not in check_totals:
        check_totals.append(authorid)

    if action == "Delete":
        if 'Audio' in library:
            bookfile = bookdata['AudioFile']
            if bookfile and os.path.isfile(bookfile):
                try:
                    rmtree(os.path.dirname(bookfile), ignore_errors=True)
                    logger.info('AudioBook %s deleted from disc' % bookname)
                except Exception as e:
                    logger.warn('rmtree failed on %s, %s %s' %
                                (bookfile, type(e).__name__, str(e)))

        if 'eBook' in library:
            bookfile = bookdata['BookFile']
            if bookfile and os.path.isfile(bookfile):
                _delete_ebook(bookfile, bookname)

    # Update database
    authorcheck = myDB.match('SELECT Status FROM authors WHERE AuthorID=?', (authorid,))
    if authorcheck:
        if authorcheck['Status'] not in ['Active', 'Wanted']:
            myDB.action('DELETE FROM books WHERE BookID=?', (bookid,))
            myDB.action('DELETE FROM wanted WHERE BookID=?', (bookid,))
            logger.info('Removed "%s" from database' % bookname)
        elif 'eBook' in library:
            myDB.upsert("books", {"Status": "Ignored"}, {"BookID": bookid})
            logger.debug('Status set to Ignored for "%s"' % bookname)
        elif 'Audio' in library:
            myDB.upsert("books", {"AudioStatus": "Ignored"}, {"BookID": bookid})
            logger.debug('AudioStatus set to Ignored for "%s"' % bookname)
    else:
        myDB.action('DELETE FROM books WHERE BookID=?', (bookid,))
        myDB.action('DELETE FROM wanted WHERE BookID=?', (bookid,))
        logger.info('Removed "%s" from database' % bookname)


def _delete_ebook(bookfile: str, bookname: str) -> None:
    """Delete an ebook file and optionally from Calibre."""
    try:
        rmtree(os.path.dirname(bookfile), ignore_errors=True)
        deleted = True
    except Exception as e:
        logger.warn('rmtree failed on %s, %s %s' % (bookfile, type(e).__name__, str(e)))
        deleted = False

    if deleted:
        logger.info('eBook %s deleted from disc' % bookname)
        # Try to remove from Calibre
        try:
            calibreid = os.path.dirname(bookfile)
            if calibreid.endswith(')'):
                calibreid = calibreid.rsplit('(', 1)[1].split(')')[0]
                if not calibreid or not calibreid.isdigit():
                    calibreid = None
            else:
                calibreid = None
        except IndexError:
            calibreid = None

        if calibreid:
            res, err, rc = calibredb('remove', [calibreid], None)
            if res and not rc:
                logger.debug('%s reports: %s' %
                             (lazylibrarian.CONFIG['IMP_CALIBREDB'], unaccented_str(res)))
            else:
                logger.debug('No response from %s' % lazylibrarian.CONFIG['IMP_CALIBREDB'])


def _start_wanted_search(book_ids: Dict[str, Any], library: str) -> None:
    """Start search for wanted books (only if IMP_AUTOSEARCH is enabled)."""
    if not lazylibrarian.CONFIG['IMP_AUTOSEARCH']:
        return

    books = []
    for key in ['booklang', 'library', 'ignored', 'book_table_length']:
        book_ids.pop(key, None)

    for bookid in book_ids:
        books.append({"bookid": bookid})

    if not books:
        return

    if (lazylibrarian.USE_NZB() or lazylibrarian.USE_TOR() or
            lazylibrarian.USE_RSS() or lazylibrarian.USE_DIRECT()):
        if 'eBook' in library:
            threading.Thread(target=search_book, name='SEARCHBOOK', args=[books, 'eBook']).start()
        if 'Audio' in library:
            threading.Thread(target=search_book, name='SEARCHBOOK', args=[books, 'AudioBook']).start()


def _handle_book_redirect(redirect: str, author_id: Optional[str],
                          series_id: Optional[str], library: str) -> None:
    """Handle redirect after book action."""
    if redirect == "author" and author_id:
        lib_type = 'eBook' if 'eBook' in library else 'AudioBook'
        raise cherrypy.HTTPRedirect("authorPage?AuthorID=%s&library=%s" % (author_id, lib_type))
    elif redirect in ["books", "audio"]:
        raise cherrypy.HTTPRedirect(redirect)
    elif redirect == "members" and series_id:
        raise cherrypy.HTTPRedirect("seriesMembers?seriesid=%s" % series_id)
    elif 'Audio' in library:
        raise cherrypy.HTTPRedirect("manage?library=AudioBook")
    raise cherrypy.HTTPRedirect("manage?library=eBook")
