#  This file is part of Lazylibrarian.
#
#  Lazylibrarian is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

"""
Test utilities and helpers for LazyLibrarian testing.

Provides:
- Random test data generators
- Assertion helpers
- Database population utilities
"""

import random
import string
from datetime import datetime, timedelta


def generate_random_id(prefix='id'):
    """Generate a random ID string.

    Args:
        prefix: String prefix for the ID (default: 'id')

    Returns:
        String in format 'prefix-randomchars'
    """
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f'{prefix}-{random_part}'


def generate_random_author():
    """Generate random author test data.

    Returns:
        Dictionary with author fields suitable for database insertion.
    """
    author_id = generate_random_id('author')
    first_names = ['John', 'Jane', 'Michael', 'Sarah', 'Robert', 'Emily', 'William', 'Emma']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Davis', 'Miller', 'Wilson']

    return {
        'AuthorID': author_id,
        'AuthorName': f'{random.choice(first_names)} {random.choice(last_names)}',
        'AuthorImg': f'http://example.com/images/{author_id}.jpg',
        'AuthorLink': f'http://example.com/author/{author_id}',
        'Status': random.choice(['Active', 'Paused', 'Ignored']),
        'HaveBooks': random.randint(0, 20),
        'TotalBooks': random.randint(10, 50),
        'UnignoredBooks': random.randint(5, 30),
    }


def generate_random_book(author_id=None):
    """Generate random book test data.

    Args:
        author_id: AuthorID to associate with the book. If None, generates one.

    Returns:
        Dictionary with book fields suitable for database insertion.
    """
    book_id = generate_random_id('book')
    if author_id is None:
        author_id = generate_random_id('author')

    titles = ['The Great Adventure', 'Mystery of the Lost City', 'Science Fiction Tales',
              'Romance in Paris', 'History of Everything', 'Programming Mastery',
              'The Last Journey', 'Secrets of Success', 'Fantasy Realms', 'Horror Stories']

    genres = ['Fiction', 'Mystery', 'Science Fiction', 'Romance', 'History',
              'Technology', 'Adventure', 'Self-Help', 'Fantasy', 'Horror']

    pub_date = datetime.now() - timedelta(days=random.randint(0, 3650))

    return {
        'BookID': book_id,
        'AuthorID': author_id,
        'BookName': random.choice(titles) + f' #{random.randint(1, 100)}',
        'BookSub': 'A Subtitle' if random.random() > 0.5 else '',
        'BookDesc': 'This is a randomly generated book description for testing purposes.',
        'BookGenre': random.choice(genres),
        'BookIsbn': ''.join(random.choices(string.digits, k=13)),
        'BookPub': f'Test Publisher {random.randint(1, 100)}',
        'BookRate': str(round(random.uniform(1, 5), 1)),
        'BookPages': random.randint(100, 800),
        'BookDate': pub_date.strftime('%Y-%m-%d'),
        'BookLang': random.choice(['en', 'es', 'fr', 'de', 'it']),
        'Status': random.choice(['Wanted', 'Have', 'Skipped', 'Ignored']),
    }


def generate_random_magazine():
    """Generate random magazine test data.

    Returns:
        Dictionary with magazine fields suitable for database insertion.
    """
    mag_id = generate_random_id('mag')
    names = ['Tech Weekly', 'Science Monthly', 'Fashion Today', 'Sports Illustrated',
             'News Digest', 'Business Review', 'Health Magazine', 'Travel World']

    return {
        'Title': f'{random.choice(names)} {mag_id[-4:].upper()}',
        'Regex': '',
        'Status': random.choice(['Active', 'Paused']),
        'IssueStatus': 'Wanted',
        'MagazineAdded': datetime.now().strftime('%Y-%m-%d'),
        'DateType': random.choice(['month', 'issue']),
    }


def assert_api_success(result):
    """Assert that an API call was successful.

    Args:
        result: The result string from api.fetchData

    Raises:
        AssertionError: If the result indicates an error
    """
    error_indicators = [
        'api not enabled',
        'missing api key',
        'incorrect api key',
        'missing parameter',
        'unknown command',
        'invalid',
    ]
    result_lower = result.lower() if isinstance(result, str) else str(result).lower()
    for indicator in error_indicators:
        assert indicator not in result_lower, f"API error detected: {result}"


def assert_api_error(result, error_type):
    """Assert that an API call returned a specific error.

    Args:
        result: The result string from api.fetchData
        error_type: Expected error substring (case-insensitive)

    Raises:
        AssertionError: If the expected error is not found
    """
    result_lower = result.lower() if isinstance(result, str) else str(result).lower()
    assert error_type.lower() in result_lower, f"Expected error '{error_type}' not found in: {result}"


def populate_test_database(db, num_authors=5, books_per_author=3, num_magazines=2):
    """Populate test database with sample data.

    Args:
        db: DBConnection instance
        num_authors: Number of authors to create
        books_per_author: Number of books per author
        num_magazines: Number of magazines to create

    Returns:
        Tuple of (authors_list, books_list, magazines_list)
    """
    authors = []
    books = []
    magazines = []

    for _ in range(num_authors):
        author = generate_random_author()
        db.action(
            """INSERT INTO authors (AuthorID, AuthorName, Status, HaveBooks, TotalBooks, UnignoredBooks)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [author['AuthorID'], author['AuthorName'], author['Status'],
             author['HaveBooks'], author['TotalBooks'], author['UnignoredBooks']]
        )
        authors.append(author)

        for _ in range(books_per_author):
            book = generate_random_book(author['AuthorID'])
            db.action(
                """INSERT INTO books (BookID, AuthorID, BookName, BookIsbn, Status)
                   VALUES (?, ?, ?, ?, ?)""",
                [book['BookID'], book['AuthorID'], book['BookName'],
                 book['BookIsbn'], book['Status']]
            )
            books.append(book)

    for _ in range(num_magazines):
        magazine = generate_random_magazine()
        db.action(
            "INSERT INTO magazines (Title, Status, IssueStatus) VALUES (?, ?, ?)",
            [magazine['Title'], magazine['Status'], magazine['IssueStatus']]
        )
        magazines.append(magazine)

    return authors, books, magazines


def count_records(db, table):
    """Count records in a database table.

    Args:
        db: DBConnection instance
        table: Table name

    Returns:
        Integer count of records
    """
    result = db.match(f"SELECT COUNT(*) as cnt FROM {table}")
    return result['cnt'] if result else 0


def clear_table(db, table):
    """Delete all records from a database table.

    Args:
        db: DBConnection instance
        table: Table name
    """
    db.action(f"DELETE FROM {table}")


# ============================================================================
# Self-Tests for Utilities
# ============================================================================

class TestUtilityFunctions:
    """Tests for the utility functions themselves."""

    def test_generate_random_id_has_prefix(self):
        """generate_random_id should include the prefix."""
        result = generate_random_id('test')
        assert result.startswith('test-')
        assert len(result) > 5

    def test_generate_random_author_has_required_fields(self):
        """generate_random_author should return all required fields."""
        author = generate_random_author()
        required = ['AuthorID', 'AuthorName', 'Status', 'HaveBooks', 'TotalBooks']
        for field in required:
            assert field in author

    def test_generate_random_book_has_required_fields(self):
        """generate_random_book should return all required fields."""
        book = generate_random_book()
        required = ['BookID', 'AuthorID', 'BookName', 'Status']
        for field in required:
            assert field in book

    def test_generate_random_book_uses_provided_author_id(self):
        """generate_random_book should use provided author_id."""
        book = generate_random_book('my-author-id')
        assert book['AuthorID'] == 'my-author-id'

    def test_generate_random_magazine_has_required_fields(self):
        """generate_random_magazine should return all required fields."""
        mag = generate_random_magazine()
        required = ['Title', 'Status', 'IssueStatus']
        for field in required:
            assert field in mag

    def test_assert_api_success_passes_for_ok(self):
        """assert_api_success should pass for 'OK' result."""
        assert_api_success('OK')  # Should not raise

    def test_assert_api_success_passes_for_json(self):
        """assert_api_success should pass for JSON data."""
        assert_api_success('{"data": "test"}')  # Should not raise

    def test_assert_api_error_finds_error(self):
        """assert_api_error should find expected error."""
        assert_api_error('Missing parameter: id', 'missing parameter')  # Should not raise

    def test_populate_test_database_creates_records(self, temp_db):
        """populate_test_database should create the specified records."""
        from lazylibrarian.database import DBConnection

        db = DBConnection()
        authors, books, magazines = populate_test_database(db, num_authors=3, books_per_author=2, num_magazines=1)

        assert len(authors) == 3
        assert len(books) == 6  # 3 authors * 2 books
        assert len(magazines) == 1

        # Verify in database
        assert count_records(db, 'authors') == 3
        assert count_records(db, 'books') == 6
        assert count_records(db, 'magazines') == 1
