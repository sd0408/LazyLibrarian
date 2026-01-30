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
File organization for Bookbag of Holding post-processing.

This module provides utilities for organizing and renaming files according
to configured patterns.
"""

import os
import re
import shutil
from typing import Any, Dict, Optional

import bookbagofholding
from bookbagofholding import logger
from bookbagofholding.common import setperm


class FileOrganizer:
    """File organization utilities.

    Provides methods for organizing files into the proper directory
    structure and renaming them according to configured patterns.
    """

    # Characters not allowed in filenames
    INVALID_CHARS = {
        '<': '', '>': '', ':': '', '"': '', '/': '-',
        '\\': '-', '|': '', '?': '', '*': '', '...': ''
    }

    @staticmethod
    def safe_filename(filename: str) -> str:
        """Make a filename safe for the filesystem.

        Removes or replaces characters that are not allowed in filenames.

        Args:
            filename: The filename to sanitize

        Returns:
            Safe filename
        """
        for char, replacement in FileOrganizer.INVALID_CHARS.items():
            filename = filename.replace(char, replacement)

        # Remove leading/trailing whitespace and dots
        filename = filename.strip().strip('.')

        # Collapse multiple spaces
        filename = ' '.join(filename.split())

        return filename

    @staticmethod
    def format_pattern(pattern: str, variables: Dict[str, Any]) -> str:
        """Format a naming pattern with variables.

        Supported variables:
        - $Author - Author name
        - $Title - Book title
        - $Series - Series name
        - $SeriesNum - Series number
        - $Year - Publication year
        - $ISBN - ISBN number

        Args:
            pattern: The pattern string with $Variable placeholders
            variables: Dictionary of variable values

        Returns:
            Formatted string
        """
        result = pattern

        # Replace each variable
        for var, value in variables.items():
            if value is None:
                value = ''
            placeholder = '$' + var
            result = result.replace(placeholder, str(value))

        # Remove any remaining placeholders
        result = re.sub(r'\$\w+', '', result)

        # Clean up extra whitespace and punctuation
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s*-\s*-\s*', ' - ', result)
        result = result.strip(' -')

        return FileOrganizer.safe_filename(result)

    @staticmethod
    def get_destination_folder(author_name: str, book_title: str,
                               library: str = 'eBook') -> str:
        """Get the destination folder for a book.

        Args:
            author_name: Author name
            book_title: Book title
            library: Library type ('eBook' or 'AudioBook')

        Returns:
            Path to the destination folder
        """
        if library == 'AudioBook':
            base_dir = bookbagofholding.DIRECTORY('AudioBook')
            pattern = bookbagofholding.CONFIG.get('AUDIOBOOK_DEST_FOLDER', '$Author/$Title')
        else:
            base_dir = bookbagofholding.DIRECTORY('eBook')
            pattern = bookbagofholding.CONFIG.get('EBOOK_DEST_FOLDER', '$Author/$Title')

        variables = {
            'Author': FileOrganizer.safe_filename(author_name or 'Unknown'),
            'Title': FileOrganizer.safe_filename(book_title or 'Unknown')
        }

        relative_path = FileOrganizer.format_pattern(pattern, variables)
        return os.path.join(base_dir, relative_path)

    @staticmethod
    def get_destination_filename(author_name: str, book_title: str,
                                 extension: str, library: str = 'eBook') -> str:
        """Get the destination filename for a book.

        Args:
            author_name: Author name
            book_title: Book title
            extension: File extension (with leading dot)
            library: Library type ('eBook' or 'AudioBook')

        Returns:
            Destination filename
        """
        if library == 'AudioBook':
            pattern = bookbagofholding.CONFIG.get('AUDIOBOOK_DEST_FILE', '$Title')
        else:
            pattern = bookbagofholding.CONFIG.get('EBOOK_DEST_FILE', '$Title')

        variables = {
            'Author': FileOrganizer.safe_filename(author_name or 'Unknown'),
            'Title': FileOrganizer.safe_filename(book_title or 'Unknown')
        }

        filename = FileOrganizer.format_pattern(pattern, variables)
        return filename + extension

    @classmethod
    def move_file(cls, source: str, dest_dir: str,
                  dest_filename: Optional[str] = None) -> Optional[str]:
        """Move a file to its destination.

        Creates the destination directory if needed and sets permissions.

        Args:
            source: Source file path
            dest_dir: Destination directory
            dest_filename: Optional new filename (default: keep original)

        Returns:
            Path to the moved file, or None if failed
        """
        if not os.path.isfile(source):
            logger.error("Source file not found: %s" % source)
            return None

        # Create destination directory
        if not os.path.isdir(dest_dir):
            try:
                os.makedirs(dest_dir)
                setperm(dest_dir)
            except OSError as e:
                logger.error("Failed to create directory %s: %s" %
                             (dest_dir, str(e)))
                return None

        # Determine destination path
        if dest_filename:
            dest_path = os.path.join(dest_dir, cls.safe_filename(dest_filename))
        else:
            dest_path = os.path.join(dest_dir, os.path.basename(source))

        # Move the file
        try:
            if bookbagofholding.CONFIG.get('DESTINATION_COPY', False):
                shutil.copy2(source, dest_path)
            else:
                shutil.move(source, dest_path)

            setperm(dest_path)
            logger.debug("Moved file to: %s" % dest_path)
            return dest_path

        except Exception as e:
            logger.error("Failed to move file: %s %s" %
                         (type(e).__name__, str(e)))
            return None

    @classmethod
    def copy_file(cls, source: str, dest_dir: str,
                  dest_filename: Optional[str] = None) -> Optional[str]:
        """Copy a file to its destination.

        Args:
            source: Source file path
            dest_dir: Destination directory
            dest_filename: Optional new filename

        Returns:
            Path to the copied file, or None if failed
        """
        if not os.path.isfile(source):
            logger.error("Source file not found: %s" % source)
            return None

        # Create destination directory
        if not os.path.isdir(dest_dir):
            try:
                os.makedirs(dest_dir)
                setperm(dest_dir)
            except OSError as e:
                logger.error("Failed to create directory %s: %s" %
                             (dest_dir, str(e)))
                return None

        # Determine destination path
        if dest_filename:
            dest_path = os.path.join(dest_dir, cls.safe_filename(dest_filename))
        else:
            dest_path = os.path.join(dest_dir, os.path.basename(source))

        try:
            shutil.copy2(source, dest_path)
            setperm(dest_path)
            logger.debug("Copied file to: %s" % dest_path)
            return dest_path

        except Exception as e:
            logger.error("Failed to copy file: %s %s" %
                         (type(e).__name__, str(e)))
            return None

    @staticmethod
    def cleanup_empty_dirs(directory: str) -> None:
        """Remove empty directories recursively.

        Args:
            directory: Root directory to clean
        """
        if not os.path.isdir(directory):
            return

        # Walk bottom-up to remove empty directories
        for root, dirs, files in os.walk(directory, topdown=False):
            for dirname in dirs:
                dirpath = os.path.join(root, dirname)
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                        logger.debug("Removed empty directory: %s" % dirpath)
                except OSError:
                    pass  # Directory not empty or permission denied

    @staticmethod
    def get_unique_path(filepath: str) -> str:
        """Get a unique path by adding a number if the file exists.

        Args:
            filepath: Desired file path

        Returns:
            Unique file path
        """
        if not os.path.exists(filepath):
            return filepath

        base, ext = os.path.splitext(filepath)
        counter = 1

        while os.path.exists(filepath):
            filepath = "%s (%d)%s" % (base, counter, ext)
            counter += 1

        return filepath
