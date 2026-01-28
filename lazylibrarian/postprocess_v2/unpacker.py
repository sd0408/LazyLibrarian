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
Archive unpacking for LazyLibrarian post-processing.

This module provides utilities for extracting files from various archive
formats including ZIP, RAR, TAR, and 7Z files.
"""

import os
import tarfile
import zipfile
from typing import List, Optional

from lazylibrarian import logger


class ArchiveUnpacker:
    """Archive extraction utilities.

    Provides methods for detecting archive types and extracting their contents.
    """

    @staticmethod
    def can_unpack(filepath: str) -> bool:
        """Check if a file can be unpacked.

        Args:
            filepath: Path to the archive file

        Returns:
            True if the file can be unpacked
        """
        ext = os.path.splitext(filepath)[1].lower()
        return ext in ['.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.cbz']

    @staticmethod
    def unpack_zip(archive_path: str, dest_dir: str) -> List[str]:
        """Extract a ZIP archive.

        Args:
            archive_path: Path to the ZIP file
            dest_dir: Destination directory

        Returns:
            List of extracted file paths
        """
        extracted_files = []

        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # Check for dangerous paths
                for name in zf.namelist():
                    if name.startswith('/') or '..' in name:
                        logger.warn("Skipping potentially dangerous path: %s" % name)
                        continue

                    target_path = os.path.join(dest_dir, name)
                    zf.extract(name, dest_dir)
                    extracted_files.append(target_path)

            logger.debug("Extracted %d files from %s" % (len(extracted_files), archive_path))

        except zipfile.BadZipFile as e:
            logger.error("Bad ZIP file %s: %s" % (archive_path, str(e)))
        except Exception as e:
            logger.error("Failed to extract %s: %s %s" %
                         (archive_path, type(e).__name__, str(e)))

        return extracted_files

    @staticmethod
    def unpack_tar(archive_path: str, dest_dir: str) -> List[str]:
        """Extract a TAR archive (including .tar.gz and .tar.bz2).

        Args:
            archive_path: Path to the TAR file
            dest_dir: Destination directory

        Returns:
            List of extracted file paths
        """
        extracted_files = []

        try:
            with tarfile.open(archive_path, 'r:*') as tf:
                # Check for dangerous paths
                for member in tf.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        logger.warn("Skipping potentially dangerous path: %s" % member.name)
                        continue

                    target_path = os.path.join(dest_dir, member.name)
                    tf.extract(member, dest_dir)
                    extracted_files.append(target_path)

            logger.debug("Extracted %d files from %s" % (len(extracted_files), archive_path))

        except tarfile.TarError as e:
            logger.error("Bad TAR file %s: %s" % (archive_path, str(e)))
        except Exception as e:
            logger.error("Failed to extract %s: %s %s" %
                         (archive_path, type(e).__name__, str(e)))

        return extracted_files

    @classmethod
    def unpack(cls, archive_path: str, dest_dir: Optional[str] = None) -> Optional[str]:
        """Extract an archive to a destination directory.

        Args:
            archive_path: Path to the archive file
            dest_dir: Destination directory (default: same directory as archive)

        Returns:
            Path to extraction directory, or None if extraction failed
        """
        if not os.path.isfile(archive_path):
            logger.error("Archive not found: %s" % archive_path)
            return None

        if dest_dir is None:
            # Create a subdirectory based on archive name
            base_name = os.path.splitext(os.path.basename(archive_path))[0]
            dest_dir = os.path.join(os.path.dirname(archive_path), base_name)

        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)

        ext = os.path.splitext(archive_path)[1].lower()

        if ext in ['.zip', '.cbz']:
            files = cls.unpack_zip(archive_path, dest_dir)
        elif ext in ['.tar', '.tgz'] or archive_path.endswith('.tar.gz') or \
                archive_path.endswith('.tar.bz2'):
            files = cls.unpack_tar(archive_path, dest_dir)
        else:
            logger.warn("Unsupported archive format: %s" % ext)
            return None

        if files:
            return dest_dir
        else:
            return None

    @staticmethod
    def list_archive_contents(archive_path: str) -> List[str]:
        """List the contents of an archive without extracting.

        Args:
            archive_path: Path to the archive file

        Returns:
            List of filenames in the archive
        """
        contents = []
        ext = os.path.splitext(archive_path)[1].lower()

        try:
            if ext in ['.zip', '.cbz']:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    contents = zf.namelist()
            elif ext in ['.tar', '.tgz'] or archive_path.endswith('.tar.gz') or \
                    archive_path.endswith('.tar.bz2'):
                with tarfile.open(archive_path, 'r:*') as tf:
                    contents = [m.name for m in tf.getmembers()]
        except Exception as e:
            logger.error("Failed to list archive %s: %s %s" %
                         (archive_path, type(e).__name__, str(e)))

        return contents

    @staticmethod
    def get_archive_size(archive_path: str) -> int:
        """Get the uncompressed size of an archive.

        Args:
            archive_path: Path to the archive file

        Returns:
            Total uncompressed size in bytes
        """
        total_size = 0
        ext = os.path.splitext(archive_path)[1].lower()

        try:
            if ext in ['.zip', '.cbz']:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for info in zf.infolist():
                        total_size += info.file_size
            elif ext in ['.tar', '.tgz'] or archive_path.endswith('.tar.gz') or \
                    archive_path.endswith('.tar.bz2'):
                with tarfile.open(archive_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        total_size += member.size
        except Exception as e:
            logger.error("Failed to get archive size %s: %s %s" %
                         (archive_path, type(e).__name__, str(e)))

        return total_size
