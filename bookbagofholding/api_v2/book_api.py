#  This file is part of Bookbag of Holding.
#  Bookbag of Holding is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

"""
Book API endpoints for Bookbag of Holding.

This module contains API methods for book operations:
- List wanted/snatched/read books
- Get book details
- Queue/unqueue books
- Search for books
"""

import threading
from typing import Any, Dict, List

from bookbagofholding import logger
from bookbagofholding.api_v2.base import ApiBase, api_endpoint, require_param
from bookbagofholding.cache import cache_img
from bookbagofholding.gb import GoogleBooks
from bookbagofholding.images import getBookCover
from bookbagofholding.importer import update_totals
from bookbagofholding.searchbook import search_book


class BookApi(ApiBase):
    """API handler for book-related endpoints."""

    @api_endpoint("List wanted books")
    def get_wanted(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all wanted books.

        Returns:
            List of wanted book dictionaries
        """
        return self.get_books_by_status('Wanted')

    @api_endpoint("List snatched books")
    def get_snatched(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all snatched books.

        Returns:
            List of snatched book dictionaries
        """
        return self.get_books_by_status('Snatched')

    @api_endpoint("List all books in the database")
    def get_all_books(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all books.

        Returns:
            List of book dictionaries
        """
        rows = self.db.select("SELECT * FROM books ORDER BY BookName")
        return self.rows_to_dicts(rows)

    @api_endpoint("Get book details", ["&id= book ID"])
    @require_param('id')
    def get_book(self, **kwargs) -> Dict[str, Any]:
        """Get book details by ID.

        Args:
            id: Book ID

        Returns:
            Book data dictionary
        """
        book_id = kwargs['id']
        book = self.get_book_by_id(book_id)

        if not book:
            return self.error("Book not found: %s" % book_id)

        return book

    @api_endpoint("Fetch cover from various sources", ["&id= book ID", "&src= source (optional)"])
    @require_param('id')
    def get_book_cover(self, **kwargs) -> Dict[str, Any]:
        """Get or fetch a book cover.

        Args:
            id: Book ID
            src: Cover source (optional)

        Returns:
            Cover URL or error
        """
        book_id = kwargs['id']
        source = kwargs.get('src', None)

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        cover_url, source_used = getBookCover(book_id, source)
        if cover_url:
            return self.success({"cover": cover_url, "source": source_used})
        else:
            return self.error("No cover found for book")

    @api_endpoint("Set a new image for this book", ["&id= book ID", "&img= image URL"])
    @require_param('id', 'img')
    def set_book_image(self, **kwargs) -> Dict[str, Any]:
        """Set a book's cover image.

        Args:
            id: Book ID
            img: Image URL or file path

        Returns:
            Success or error
        """
        book_id = kwargs['id']
        img_url = kwargs['img']

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        cached_url, success, _ = cache_img("book", book_id, img_url)
        if success:
            self.db.upsert("books", {'BookImg': cached_url}, {'BookID': book_id})
            logger.info("Updated book cover for %s" % book_id)
            return self.success(message="Book cover updated")
        else:
            return self.error("Failed to cache image")

    @api_endpoint("Lock book details", ["&id= book ID"])
    @require_param('id')
    def set_book_lock(self, **kwargs) -> Dict[str, Any]:
        """Lock a book's details from automatic updates.

        Args:
            id: Book ID

        Returns:
            Success or error
        """
        book_id = kwargs['id']

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        self.db.upsert("books", {'Manual': 1}, {'BookID': book_id})
        logger.info("Book %s locked" % book_id)
        return self.success(message="Book locked")

    @api_endpoint("Unlock book details", ["&id= book ID"])
    @require_param('id')
    def set_book_unlock(self, **kwargs) -> Dict[str, Any]:
        """Unlock a book's details for automatic updates.

        Args:
            id: Book ID

        Returns:
            Success or error
        """
        book_id = kwargs['id']

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        self.db.upsert("books", {'Manual': 0}, {'BookID': book_id})
        logger.info("Book %s unlocked" % book_id)
        return self.success(message="Book unlocked")

    @api_endpoint("Mark book as Wanted", ["&id= book ID", "&type= eBook/AudioBook (optional)"])
    @require_param('id')
    def queue_book(self, **kwargs) -> Dict[str, Any]:
        """Queue a book for download.

        Args:
            id: Book ID
            type: Book type (eBook or AudioBook)

        Returns:
            Success or error
        """
        book_id = kwargs['id']
        book_type = kwargs.get('type', 'eBook')

        book = self.db.match("SELECT AuthorID FROM books WHERE BookID=?", (book_id,))
        if not book:
            return self.error("Book not found: %s" % book_id)

        if book_type == 'AudioBook':
            self.db.upsert("books", {'AudioStatus': 'Wanted'}, {'BookID': book_id})
        else:
            self.db.upsert("books", {'Status': 'Wanted'}, {'BookID': book_id})

        update_totals(book['AuthorID'])
        logger.info("Queued %s: %s" % (book_type, book_id))

        return self.success(message="Book queued as Wanted")

    @api_endpoint("Mark book as Skipped", ["&id= book ID", "&type= eBook/AudioBook (optional)"])
    @require_param('id')
    def unqueue_book(self, **kwargs) -> Dict[str, Any]:
        """Unqueue a book (mark as Skipped).

        Args:
            id: Book ID
            type: Book type (eBook or AudioBook)

        Returns:
            Success or error
        """
        book_id = kwargs['id']
        book_type = kwargs.get('type', 'eBook')

        book = self.db.match("SELECT AuthorID FROM books WHERE BookID=?", (book_id,))
        if not book:
            return self.error("Book not found: %s" % book_id)

        if book_type == 'AudioBook':
            self.db.upsert("books", {'AudioStatus': 'Skipped'}, {'BookID': book_id})
        else:
            self.db.upsert("books", {'Status': 'Skipped'}, {'BookID': book_id})

        update_totals(book['AuthorID'])
        logger.info("Unqueued %s: %s" % (book_type, book_id))

        return self.success(message="Book marked as Skipped")

    @api_endpoint("Search for one book", ["&id= book ID", "&wait= wait for completion",
                                          "&type= eBook/AudioBook (optional)"])
    @require_param('id')
    def search_book(self, **kwargs) -> Dict[str, Any]:
        """Search for a specific book.

        Args:
            id: Book ID
            wait: Whether to wait for completion
            type: Book type (eBook or AudioBook)

        Returns:
            Success or error
        """
        import bookbagofholding

        book_id = kwargs['id']
        wait = kwargs.get('wait', False)
        book_type = kwargs.get('type', None)

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        if not (bookbagofholding.USE_NZB() or bookbagofholding.USE_TOR() or
                bookbagofholding.USE_RSS() or bookbagofholding.USE_DIRECT()):
            return self.error("No search methods enabled, check config")

        books = [{"bookid": book_id}]
        t = threading.Thread(target=search_book, name='SEARCHBOOK', args=[books, book_type])
        t.start()

        if wait:
            t.join()
            return self.success(message="Book search completed")
        else:
            return self.success(message="Book search started")

    @api_endpoint("Search GoogleBooks for book", ["&name= book title"])
    @require_param('name')
    def find_book(self, **kwargs) -> Dict[str, Any]:
        """Search for books by title.

        Args:
            name: Book title to search

        Returns:
            List of matching books
        """
        book_name = kwargs['name']

        GB = GoogleBooks(book_name)
        results = GB.find_results(book_name)

        if results:
            return self.success(data=results)
        else:
            return self.error("No books found matching: %s" % book_name)

    @api_endpoint("Add book to database", ["&id= book ID"])
    @require_param('id')
    def add_book(self, **kwargs) -> Dict[str, Any]:
        """Add a book to the database.

        Args:
            id: Book ID (Google Books ID)

        Returns:
            Success or error
        """
        book_id = kwargs['id']

        existing = self.db.match("SELECT BookID FROM books WHERE BookID=?", (book_id,))
        if existing:
            return self.error("Book already exists: %s" % book_id)

        GB = GoogleBooks(book_id)
        t = threading.Thread(target=GB.find_book, name='GB-BOOK', args=[book_id, "Wanted"])
        t.start()
        t.join(timeout=30)

        return self.success(message="Adding book: %s" % book_id)

    @api_endpoint("List books with unknown language")
    def list_no_lang(self, **kwargs) -> List[Dict[str, Any]]:
        """Get books with unknown language.

        Returns:
            List of book dictionaries
        """
        rows = self.db.select(
            "SELECT * FROM books WHERE BookLang='Unknown' OR BookLang IS NULL OR BookLang=''"
        )
        return self.rows_to_dicts(rows)

    @api_endpoint("List books with no description")
    def list_no_desc(self, **kwargs) -> List[Dict[str, Any]]:
        """Get books with no description.

        Returns:
            List of book dictionaries
        """
        rows = self.db.select(
            "SELECT * FROM books WHERE BookDesc IS NULL OR BookDesc=''"
        )
        return self.rows_to_dicts(rows)

    @api_endpoint("List books with no ISBN")
    def list_no_isbn(self, **kwargs) -> List[Dict[str, Any]]:
        """Get books with no ISBN.

        Returns:
            List of book dictionaries
        """
        rows = self.db.select(
            "SELECT * FROM books WHERE BookIsbn IS NULL OR BookIsbn=''"
        )
        return self.rows_to_dicts(rows)

    @api_endpoint("List all ignored books")
    def list_ignored_books(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all ignored books.

        Returns:
            List of book dictionaries
        """
        rows = self.db.select("SELECT * FROM books WHERE Status='Ignored'")
        return self.rows_to_dicts(rows)

    @api_endpoint("Get list of authors for a book", ["&id= book ID"])
    @require_param('id')
    def get_book_authors(self, **kwargs) -> Dict[str, Any]:
        """Get all authors associated with a book.

        Args:
            id: Book ID

        Returns:
            List of author dictionaries
        """
        from bookbagofholding.bookwork import getBookAuthors

        book_id = kwargs['id']

        if not self.check_book_exists(book_id):
            return self.error("Book not found: %s" % book_id)

        authors = getBookAuthors(book_id)
        return self.success(data=authors)
