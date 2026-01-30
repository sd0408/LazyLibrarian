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
Author API endpoints for Bookbag of Holding.

This module contains API methods for author operations:
- List authors
- Get author details
- Pause/resume/ignore authors
- Refresh author metadata
- Add/remove authors
"""

import threading
from typing import Any, Dict, List, Optional

from bookbagofholding import logger
from bookbagofholding.api_v2.base import ApiBase, api_endpoint, require_param
from bookbagofholding.cache import cache_img
from bookbagofholding.gb import GoogleBooks
from bookbagofholding.importer import addAuthorToDB, addAuthorNameToDB


class AuthorApi(ApiBase):
    """API handler for author-related endpoints."""

    @api_endpoint("List all authors")
    def get_index(self, **kwargs) -> List[Dict[str, Any]]:
        """Get a list of all authors.

        Returns:
            List of author dictionaries
        """
        return self.get_all_authors()

    @api_endpoint("Get author by AuthorID", ["&id= author ID"])
    @require_param('id')
    def get_author(self, **kwargs) -> Dict[str, Any]:
        """Get author details by ID.

        Args:
            id: Author ID

        Returns:
            Author data with books
        """
        author_id = kwargs['id']
        author = self.get_author_by_id(author_id)

        if not author:
            return self.error("Author not found: %s" % author_id)

        # Get author's books
        rows = self.db.select(
            "SELECT * FROM books WHERE AuthorID=? ORDER BY BookName",
            (author_id,)
        )
        author['books'] = self.rows_to_dicts(rows)

        return author

    @api_endpoint("Get an image for this author", ["&id= author ID"])
    @require_param('id')
    def get_author_image(self, **kwargs) -> Dict[str, Any]:
        """Get or fetch an author image.

        Args:
            id: Author ID

        Returns:
            Image URL or error
        """
        from bookbagofholding.images import getAuthorImage

        author_id = kwargs['id']
        author = self.get_author_by_id(author_id)

        if not author:
            return self.error("Author not found: %s" % author_id)

        image_url = getAuthorImage(author_id)
        if image_url:
            return self.success({"image": image_url})
        else:
            return self.error("No image found for author")

    @api_endpoint("Set a new image for this author", ["&id= author ID", "&img= image URL"])
    @require_param('id', 'img')
    def set_author_image(self, **kwargs) -> Dict[str, Any]:
        """Set an author's image.

        Args:
            id: Author ID
            img: Image URL or file path

        Returns:
            Success or error
        """
        author_id = kwargs['id']
        img_url = kwargs['img']

        if not self.check_author_exists(author_id):
            return self.error("Author not found: %s" % author_id)

        # Cache the image
        cached_url, success, _ = cache_img("author", author_id, img_url)
        if success:
            self.db.upsert("authors", {'AuthorImg': cached_url}, {'AuthorID': author_id})
            logger.info("Updated author image for %s" % author_id)
            return self.success(message="Author image updated")
        else:
            return self.error("Failed to cache image")

    @api_endpoint("Lock author name/image/dates", ["&id= author ID"])
    @require_param('id')
    def set_author_lock(self, **kwargs) -> Dict[str, Any]:
        """Lock an author's details from automatic updates.

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        author_id = kwargs['id']

        if not self.check_author_exists(author_id):
            return self.error("Author not found: %s" % author_id)

        self.db.upsert("authors", {'Manual': 1}, {'AuthorID': author_id})
        logger.info("Author %s locked" % author_id)
        return self.success(message="Author locked")

    @api_endpoint("Unlock author name/image/dates", ["&id= author ID"])
    @require_param('id')
    def set_author_unlock(self, **kwargs) -> Dict[str, Any]:
        """Unlock an author's details for automatic updates.

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        author_id = kwargs['id']

        if not self.check_author_exists(author_id):
            return self.error("Author not found: %s" % author_id)

        self.db.upsert("authors", {'Manual': 0}, {'AuthorID': author_id})
        logger.info("Author %s unlocked" % author_id)
        return self.success(message="Author unlocked")

    @api_endpoint("Pause author by AuthorID", ["&id= author ID"])
    @require_param('id')
    def pause_author(self, **kwargs) -> Dict[str, Any]:
        """Pause an author.

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        return self._set_author_status(kwargs['id'], 'Paused')

    @api_endpoint("Resume author by AuthorID", ["&id= author ID"])
    @require_param('id')
    def resume_author(self, **kwargs) -> Dict[str, Any]:
        """Resume an author (set to Active).

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        return self._set_author_status(kwargs['id'], 'Active')

    @api_endpoint("Ignore author by AuthorID", ["&id= author ID"])
    @require_param('id')
    def ignore_author(self, **kwargs) -> Dict[str, Any]:
        """Ignore an author.

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        return self._set_author_status(kwargs['id'], 'Ignored')

    @api_endpoint("Reload author and books", ["&name= author name", "&refresh= refresh cache"])
    @require_param('name')
    def refresh_author(self, **kwargs) -> Dict[str, Any]:
        """Refresh an author's metadata.

        Args:
            name: Author name
            refresh: Whether to refresh cache (optional)

        Returns:
            Success or error
        """
        author_name = kwargs['name']
        refresh = kwargs.get('refresh', False)

        author = self.db.match(
            "SELECT AuthorID FROM authors WHERE AuthorName=?",
            (author_name,)
        )

        if not author:
            return self.error("Author not found: %s" % author_name)

        threading.Thread(
            target=addAuthorToDB,
            name='REFRESHAUTHOR',
            args=[None, refresh, author['AuthorID']]
        ).start()

        return self.success(message="Author refresh started")

    @api_endpoint("Add author to database by name", ["&name= author name"])
    @require_param('name')
    def add_author(self, **kwargs) -> Dict[str, Any]:
        """Add an author by name.

        Args:
            name: Author name

        Returns:
            Success or error
        """
        author_name = kwargs['name']

        # Check if already exists
        existing = self.db.match(
            "SELECT AuthorID FROM authors WHERE AuthorName=?",
            (author_name,)
        )
        if existing:
            return self.error("Author already exists: %s" % author_name)

        threading.Thread(
            target=addAuthorNameToDB,
            name='ADDAUTHOR',
            args=[author_name, False]
        ).start()

        return self.success(message="Adding author: %s" % author_name)

    @api_endpoint("Add author to database by AuthorID", ["&id= author ID"])
    @require_param('id')
    def add_author_id(self, **kwargs) -> Dict[str, Any]:
        """Add an author by ID.

        Args:
            id: Author ID (e.g., Goodreads ID)

        Returns:
            Success or error
        """
        author_id = kwargs['id']

        # Check if already exists
        existing = self.db.match(
            "SELECT AuthorID FROM authors WHERE AuthorID=?",
            (author_id,)
        )
        if existing:
            return self.error("Author already exists: %s" % author_id)

        threading.Thread(
            target=addAuthorToDB,
            name='ADDAUTHOR',
            args=['', False, author_id]
        ).start()

        return self.success(message="Adding author ID: %s" % author_id)

    @api_endpoint("Remove author from database by AuthorID", ["&id= author ID"])
    @require_param('id')
    def remove_author(self, **kwargs) -> Dict[str, Any]:
        """Remove an author from the database.

        Args:
            id: Author ID

        Returns:
            Success or error
        """
        author_id = kwargs['id']

        author = self.db.match(
            "SELECT AuthorName FROM authors WHERE AuthorID=?",
            (author_id,)
        )

        if not author:
            return self.error("Author not found: %s" % author_id)

        author_name = author['AuthorName']
        self.db.action('DELETE FROM authors WHERE AuthorID=?', (author_id,))
        logger.info("Removed author: %s" % author_name)

        return self.success(message="Removed author: %s" % author_name)

    @api_endpoint("Search for author by name", ["&name= author name"])
    @require_param('name')
    def find_author(self, **kwargs) -> Dict[str, Any]:
        """Search for authors by name using Google Books.

        Args:
            name: Author name to search

        Returns:
            List of matching authors
        """
        author_name = kwargs['name']

        GB = GoogleBooks(author_name)
        results = GB.find_results(author_name)

        if results:
            return self.success(data=results)
        else:
            return self.error("No authors found matching: %s" % author_name)

    @api_endpoint("List all authors with no books")
    def list_no_books(self, **kwargs) -> List[Dict[str, Any]]:
        """Get authors with no books.

        Returns:
            List of author dictionaries
        """
        rows = self.db.select(
            "SELECT * FROM authors WHERE TotalBooks=0 OR TotalBooks IS NULL"
        )
        return self.rows_to_dicts(rows)

    @api_endpoint("List all ignored authors")
    def list_ignored_authors(self, **kwargs) -> List[Dict[str, Any]]:
        """Get all ignored authors.

        Returns:
            List of author dictionaries
        """
        rows = self.db.select("SELECT * FROM authors WHERE Status='Ignored'")
        return self.rows_to_dicts(rows)

    def _set_author_status(self, author_id: str, status: str) -> Dict[str, Any]:
        """Set an author's status.

        Args:
            author_id: Author ID
            status: New status

        Returns:
            Success or error
        """
        author = self.db.match(
            "SELECT AuthorName FROM authors WHERE AuthorID=?",
            (author_id,)
        )

        if not author:
            return self.error("Author not found: %s" % author_id)

        self.db.upsert("authors", {'Status': status}, {'AuthorID': author_id})
        logger.info("Author %s set to %s" % (author['AuthorName'], status))

        return self.success(message="Author %s set to %s" % (author['AuthorName'], status))
