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
Base API class and utilities for LazyLibrarian API.

This module provides:
- ApiBase class with common API functionality
- Decorators for endpoint definition and parameter validation
- Response formatting utilities
"""

import functools
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import lazylibrarian
from lazylibrarian import database, logger

F = TypeVar('F', bound=Callable[..., Any])


def api_endpoint(description: str, params: Optional[List[str]] = None) -> Callable[[F], F]:
    """Decorator to mark a method as an API endpoint.

    Args:
        description: Human-readable description of the endpoint
        params: List of parameter descriptions (e.g., ["&id= author ID"])

    Returns:
        Decorated function with metadata attached
    """
    def decorator(func: F) -> F:
        func._api_endpoint = True
        func._api_description = description
        func._api_params = params or []
        return func
    return decorator


def require_param(*param_names: str) -> Callable[[F], F]:
    """Decorator to require specific parameters for an API endpoint.

    Args:
        *param_names: Names of required parameters

    Returns:
        Decorated function that validates parameters
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, **kwargs):
            missing = [p for p in param_names if p not in kwargs or not kwargs[p]]
            if missing:
                return self.error("Missing required parameter(s): %s" % ', '.join(missing))
            return func(self, **kwargs)
        return wrapper
    return decorator


class ApiBase:
    """Base class for API handlers.

    Provides common functionality for all API endpoint handlers including:
    - Response formatting
    - Database access
    - Error handling
    - Common query patterns
    """

    def __init__(self):
        """Initialize the API handler."""
        self._db = None

    @property
    def db(self) -> database.DBConnection:
        """Get a database connection (lazy initialization)."""
        if self._db is None:
            self._db = database.DBConnection()
        return self._db

    @staticmethod
    def success(data: Any = None, message: str = "OK") -> Dict[str, Any]:
        """Format a successful response.

        Args:
            data: Response data
            message: Success message

        Returns:
            Formatted response dictionary
        """
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def error(message: str, code: int = 400) -> Dict[str, Any]:
        """Format an error response.

        Args:
            message: Error message
            code: Error code

        Returns:
            Formatted error dictionary
        """
        return {"success": False, "error": message, "code": code}

    @staticmethod
    def rows_to_dicts(rows: List[Any]) -> List[Dict[str, Any]]:
        """Convert database rows to dictionaries.

        Args:
            rows: List of database row objects

        Returns:
            List of dictionaries
        """
        if not rows:
            return []
        return [dict(row) for row in rows]

    @staticmethod
    def row_to_dict(row: Any) -> Optional[Dict[str, Any]]:
        """Convert a single database row to a dictionary.

        Args:
            row: Database row object

        Returns:
            Dictionary or None if row is None
        """
        if row is None:
            return None
        return dict(row)

    def get_author_by_id(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Get an author by ID.

        Args:
            author_id: The author's ID

        Returns:
            Author data dictionary or None
        """
        row = self.db.match("SELECT * FROM authors WHERE AuthorID=?", (author_id,))
        return self.row_to_dict(row)

    def get_book_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get a book by ID.

        Args:
            book_id: The book's ID

        Returns:
            Book data dictionary or None
        """
        row = self.db.match("SELECT * FROM books WHERE BookID=?", (book_id,))
        return self.row_to_dict(row)

    def get_magazine_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Get a magazine by title.

        Args:
            title: The magazine title

        Returns:
            Magazine data dictionary or None
        """
        row = self.db.match("SELECT * FROM magazines WHERE Title=?", (title,))
        return self.row_to_dict(row)

    def log_api_call(self, command: str, **kwargs) -> None:
        """Log an API call for debugging.

        Args:
            command: The API command being called
            **kwargs: Command parameters
        """
        if lazylibrarian.LOGLEVEL & lazylibrarian.log_admin:
            params = ', '.join('%s=%s' % (k, v) for k, v in kwargs.items() if k != 'apikey')
            logger.debug("API call: %s(%s)" % (command, params))

    def check_author_exists(self, author_id: str) -> bool:
        """Check if an author exists.

        Args:
            author_id: The author's ID

        Returns:
            True if author exists
        """
        row = self.db.match("SELECT AuthorID FROM authors WHERE AuthorID=?", (author_id,))
        return row is not None

    def check_book_exists(self, book_id: str) -> bool:
        """Check if a book exists.

        Args:
            book_id: The book's ID

        Returns:
            True if book exists
        """
        row = self.db.match("SELECT BookID FROM books WHERE BookID=?", (book_id,))
        return row is not None

    def get_all_authors(self) -> List[Dict[str, Any]]:
        """Get all authors.

        Returns:
            List of author dictionaries
        """
        rows = self.db.select("SELECT * FROM authors ORDER BY AuthorName COLLATE NOCASE")
        return self.rows_to_dicts(rows)

    def get_books_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get books by status.

        Args:
            status: Book status (Wanted, Have, etc.)

        Returns:
            List of book dictionaries
        """
        rows = self.db.select("SELECT * FROM books WHERE Status=?", (status,))
        return self.rows_to_dicts(rows)

    def get_all_magazines(self) -> List[Dict[str, Any]]:
        """Get all magazines.

        Returns:
            List of magazine dictionaries
        """
        rows = self.db.select("SELECT * FROM magazines ORDER BY Title")
        return self.rows_to_dicts(rows)

    def get_issues_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Get magazine issues by title.

        Args:
            title: Magazine title

        Returns:
            List of issue dictionaries
        """
        rows = self.db.select(
            "SELECT * FROM issues WHERE Title=? ORDER BY IssueDate DESC",
            (title,)
        )
        return self.rows_to_dicts(rows)
