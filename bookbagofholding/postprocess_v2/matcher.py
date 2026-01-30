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
Book matching for Bookbag of Holding post-processing.

This module provides utilities for matching downloaded files to books
in the database using fuzzy string matching.
"""

from typing import Any, Dict, List, Optional, Tuple

import bookbagofholding
from bookbagofholding import database, logger
from bookbagofholding.formatter import check_int, unaccented_str


class BookMatcher:
    """Book matching utilities.

    Provides methods for matching files to database entries using
    fuzzy string matching on author and title.
    """

    def __init__(self):
        """Initialize the matcher with configured thresholds."""
        self.match_ratio = check_int(
            bookbagofholding.CONFIG.get('MATCH_RATIO', 80), 80
        )
        self.download_ratio = check_int(
            bookbagofholding.CONFIG.get('DLOAD_RATIO', 90), 90
        )

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for matching.

        Removes accents, converts to lowercase, and removes extra whitespace.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ''

        # Remove accents and convert to lowercase
        result = unaccented_str(text).lower()

        # Remove common articles that might differ
        for article in ['the ', 'a ', 'an ']:
            if result.startswith(article):
                result = result[len(article):]

        # Normalize whitespace
        result = ' '.join(result.split())

        return result

    @staticmethod
    def fuzzy_ratio(str1: str, str2: str) -> int:
        """Calculate fuzzy match ratio between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Match ratio (0-100)
        """
        try:
            from fuzzywuzzy import fuzz
            return fuzz.ratio(str1, str2)
        except ImportError:
            # Simple fallback if fuzzywuzzy not available
            if str1 == str2:
                return 100
            if str1 in str2 or str2 in str1:
                return 80
            return 0

    @staticmethod
    def partial_ratio(str1: str, str2: str) -> int:
        """Calculate partial fuzzy match ratio.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Partial match ratio (0-100)
        """
        try:
            from fuzzywuzzy import fuzz
            return fuzz.partial_ratio(str1, str2)
        except ImportError:
            # Simple fallback
            if str1 == str2:
                return 100
            if str1 in str2 or str2 in str1:
                return 90
            return 0

    def match_author(self, author_name: str) -> Optional[Dict[str, Any]]:
        """Find a matching author in the database.

        Args:
            author_name: Author name to match

        Returns:
            Author dictionary if found, None otherwise
        """
        if not author_name:
            return None

        myDB = database.DBConnection()
        normalized = self.normalize(author_name)

        # First try exact match
        author = myDB.match(
            "SELECT * FROM authors WHERE AuthorName=?",
            (author_name,)
        )
        if author:
            return dict(author)

        # Try fuzzy matching
        all_authors = myDB.select("SELECT * FROM authors")
        best_match = None
        best_ratio = 0

        for author in all_authors:
            db_normalized = self.normalize(author['AuthorName'])
            ratio = self.fuzzy_ratio(normalized, db_normalized)

            if ratio > best_ratio and ratio >= self.match_ratio:
                best_ratio = ratio
                best_match = dict(author)

        if best_match:
            logger.debug("Fuzzy matched author '%s' to '%s' (ratio: %d)" %
                         (author_name, best_match['AuthorName'], best_ratio))

        return best_match

    def match_book(self, author_name: str, book_title: str,
                   library: str = 'eBook') -> Optional[Dict[str, Any]]:
        """Find a matching book in the database.

        Args:
            author_name: Author name
            book_title: Book title
            library: Library type ('eBook' or 'AudioBook')

        Returns:
            Book dictionary if found, None otherwise
        """
        if not book_title:
            return None

        myDB = database.DBConnection()
        normalized_title = self.normalize(book_title)
        normalized_author = self.normalize(author_name) if author_name else ''

        # Build query for books
        if author_name:
            # First try to find the author
            author = self.match_author(author_name)
            if author:
                # Search books by this author
                books = myDB.select(
                    "SELECT * FROM books WHERE AuthorID=?",
                    (author['AuthorID'],)
                )
            else:
                # Search all books
                books = myDB.select("SELECT * FROM books")
        else:
            books = myDB.select("SELECT * FROM books")

        best_match = None
        best_ratio = 0

        for book in books:
            db_title = self.normalize(book['BookName'])

            # Calculate title match
            title_ratio = self.fuzzy_ratio(normalized_title, db_title)

            # If we have an author, also consider author match
            if normalized_author:
                # Get book's author
                book_author = myDB.match(
                    "SELECT AuthorName FROM authors WHERE AuthorID=?",
                    (book['AuthorID'],)
                )
                if book_author:
                    author_ratio = self.fuzzy_ratio(
                        normalized_author,
                        self.normalize(book_author['AuthorName'])
                    )
                    # Combined score
                    ratio = (title_ratio * 0.7) + (author_ratio * 0.3)
                else:
                    ratio = title_ratio
            else:
                ratio = title_ratio

            if ratio > best_ratio and ratio >= self.match_ratio:
                best_ratio = ratio
                best_match = dict(book)

        if best_match:
            logger.debug("Fuzzy matched book '%s' to '%s' (ratio: %d)" %
                         (book_title, best_match['BookName'], int(best_ratio)))

        return best_match

    def find_book_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Find a book by ISBN.

        Args:
            isbn: ISBN (10 or 13 digit)

        Returns:
            Book dictionary if found, None otherwise
        """
        if not isbn:
            return None

        # Normalize ISBN (remove hyphens, spaces)
        isbn = isbn.replace('-', '').replace(' ', '').strip()

        myDB = database.DBConnection()
        book = myDB.match(
            "SELECT * FROM books WHERE BookIsbn=?",
            (isbn,)
        )

        if book:
            return dict(book)

        # Try partial match (ISBN-10 vs ISBN-13)
        if len(isbn) == 10:
            # Try adding 978 prefix for ISBN-13
            isbn13 = '978' + isbn[:-1]  # Without check digit
            books = myDB.select(
                "SELECT * FROM books WHERE BookIsbn LIKE ?",
                (isbn13 + '%',)
            )
            if books:
                return dict(books[0])

        return None

    def get_match_candidates(self, author_name: str, book_title: str,
                             limit: int = 10) -> List[Tuple[Dict[str, Any], int]]:
        """Get a list of potential matches with their scores.

        Args:
            author_name: Author name
            book_title: Book title
            limit: Maximum number of candidates to return

        Returns:
            List of (book_dict, score) tuples, sorted by score descending
        """
        if not book_title:
            return []

        myDB = database.DBConnection()
        normalized_title = self.normalize(book_title)
        normalized_author = self.normalize(author_name) if author_name else ''

        candidates = []

        # Get all books with their authors
        cmd = '''SELECT books.*, authors.AuthorName
                 FROM books
                 JOIN authors ON books.AuthorID = authors.AuthorID'''
        books = myDB.select(cmd)

        for book in books:
            db_title = self.normalize(book['BookName'])
            db_author = self.normalize(book['AuthorName'])

            title_ratio = self.fuzzy_ratio(normalized_title, db_title)

            if normalized_author:
                author_ratio = self.fuzzy_ratio(normalized_author, db_author)
                score = int((title_ratio * 0.7) + (author_ratio * 0.3))
            else:
                score = title_ratio

            if score >= 50:  # Minimum threshold for candidates
                candidates.append((dict(book), score))

        # Sort by score descending and limit
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]
