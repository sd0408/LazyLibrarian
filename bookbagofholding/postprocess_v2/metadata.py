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
Metadata extraction for Bookbag of Holding post-processing.

This module provides utilities for extracting metadata from various
file formats including OPF files, ebook files, and audiobook files.
"""

import os
import re
from typing import Any, Dict, Optional
from xml.etree import ElementTree

from bookbagofholding import logger


class MetadataExtractor:
    """Metadata extraction utilities.

    Provides methods for extracting author, title, and other metadata
    from various file formats.
    """

    # Common metadata fields
    FIELDS = ['title', 'creator', 'author', 'description', 'publisher',
              'date', 'language', 'isbn', 'series', 'series_index']

    @staticmethod
    def extract_from_opf(opf_path: str) -> Dict[str, Any]:
        """Extract metadata from an OPF file.

        Args:
            opf_path: Path to the OPF file

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}

        if not os.path.isfile(opf_path):
            return metadata

        try:
            tree = ElementTree.parse(opf_path)
            root = tree.getroot()

            # Handle namespaces
            namespaces = {
                'dc': 'http://purl.org/dc/elements/1.1/',
                'opf': 'http://www.idpf.org/2007/opf'
            }

            # Try to find metadata element
            metadata_elem = root.find('.//{http://www.idpf.org/2007/opf}metadata')
            if metadata_elem is None:
                metadata_elem = root.find('.//metadata')
            if metadata_elem is None:
                metadata_elem = root

            # Extract Dublin Core elements
            for field in ['title', 'creator', 'description', 'publisher',
                          'date', 'language', 'identifier']:
                elem = metadata_elem.find('.//{http://purl.org/dc/elements/1.1/}' + field)
                if elem is None:
                    elem = metadata_elem.find('.//' + field)
                if elem is not None and elem.text:
                    if field == 'creator':
                        metadata['author'] = elem.text.strip()
                    elif field == 'identifier':
                        # Check if it's an ISBN
                        text = elem.text.strip()
                        scheme = elem.get('{http://www.idpf.org/2007/opf}scheme', '')
                        if scheme.upper() == 'ISBN' or text.startswith('isbn:'):
                            metadata['isbn'] = text.replace('isbn:', '').strip()
                    else:
                        metadata[field] = elem.text.strip()

            # Try to extract series info from meta elements
            for meta in metadata_elem.findall('.//{http://www.idpf.org/2007/opf}meta'):
                name = meta.get('name', '')
                content = meta.get('content', '')
                if 'series' in name.lower() and 'index' not in name.lower():
                    metadata['series'] = content
                elif 'series_index' in name.lower() or 'series-index' in name.lower():
                    metadata['series_index'] = content

            logger.debug("Extracted metadata from OPF: %s" % opf_path)

        except ElementTree.ParseError as e:
            logger.error("Failed to parse OPF %s: %s" % (opf_path, str(e)))
        except Exception as e:
            logger.error("Failed to extract OPF metadata: %s %s" %
                         (type(e).__name__, str(e)))

        return metadata

    @staticmethod
    def extract_from_filename(filename: str) -> Dict[str, Any]:
        """Extract metadata from a filename.

        Attempts to parse author and title from common filename patterns:
        - "Author - Title.ext"
        - "Author_Title.ext"
        - "Title (Author).ext"

        Args:
            filename: The filename to parse

        Returns:
            Dictionary with 'title' and 'author' if found
        """
        metadata = {}

        # Remove extension
        name = os.path.splitext(os.path.basename(filename))[0]

        # Try "Author - Title" pattern
        if ' - ' in name:
            parts = name.split(' - ', 1)
            metadata['author'] = parts[0].strip()
            metadata['title'] = parts[1].strip()
        # Try "Title (Author)" pattern
        elif '(' in name and ')' in name:
            match = re.match(r'(.+?)\s*\(([^)]+)\)\s*$', name)
            if match:
                metadata['title'] = match.group(1).strip()
                metadata['author'] = match.group(2).strip()
        # Try underscore separator
        elif '_' in name:
            parts = name.split('_', 1)
            # Could be author_title or title_author, just return as is
            metadata['author'] = parts[0].replace('_', ' ').strip()
            metadata['title'] = parts[1].replace('_', ' ').strip()
        else:
            # Just use the whole name as title
            metadata['title'] = name.replace('_', ' ').strip()

        return metadata

    @staticmethod
    def extract_from_epub(epub_path: str) -> Dict[str, Any]:
        """Extract metadata from an EPUB file.

        Args:
            epub_path: Path to the EPUB file

        Returns:
            Dictionary of extracted metadata
        """
        import zipfile

        metadata = {}

        if not os.path.isfile(epub_path):
            return metadata

        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                # Find the OPF file
                container_path = 'META-INF/container.xml'
                if container_path in zf.namelist():
                    container = zf.read(container_path)
                    tree = ElementTree.fromstring(container)
                    rootfile = tree.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
                    if rootfile is not None:
                        opf_path = rootfile.get('full-path')
                        if opf_path and opf_path in zf.namelist():
                            opf_content = zf.read(opf_path)
                            # Parse OPF content
                            root = ElementTree.fromstring(opf_content)

                            for field in ['title', 'creator', 'description',
                                          'publisher', 'language']:
                                elem = root.find('.//{http://purl.org/dc/elements/1.1/}' + field)
                                if elem is not None and elem.text:
                                    if field == 'creator':
                                        metadata['author'] = elem.text.strip()
                                    else:
                                        metadata[field] = elem.text.strip()

            logger.debug("Extracted metadata from EPUB: %s" % epub_path)

        except zipfile.BadZipFile:
            logger.warn("Invalid EPUB file: %s" % epub_path)
        except Exception as e:
            logger.error("Failed to extract EPUB metadata: %s %s" %
                         (type(e).__name__, str(e)))

        return metadata

    @staticmethod
    def extract_from_id3(audio_path: str) -> Dict[str, Any]:
        """Extract metadata from an audiobook file using ID3 tags.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}

        if not os.path.isfile(audio_path):
            return metadata

        try:
            from mutagen import File as MutagenFile
            from mutagen.id3 import ID3

            audio = MutagenFile(audio_path)
            if audio is not None:
                # Different tag formats for different file types
                if hasattr(audio, 'tags') and audio.tags:
                    tags = audio.tags

                    # Try common tag names
                    title_tags = ['TIT2', 'title', '\xa9nam']
                    artist_tags = ['TPE1', 'artist', '\xa9ART', 'author']
                    album_tags = ['TALB', 'album', '\xa9alb']

                    for tag in title_tags:
                        if tag in tags:
                            metadata['title'] = str(tags[tag][0] if isinstance(tags[tag], list)
                                                    else tags[tag])
                            break

                    for tag in artist_tags:
                        if tag in tags:
                            metadata['author'] = str(tags[tag][0] if isinstance(tags[tag], list)
                                                     else tags[tag])
                            break

                    for tag in album_tags:
                        if tag in tags:
                            metadata['album'] = str(tags[tag][0] if isinstance(tags[tag], list)
                                                    else tags[tag])
                            break

            logger.debug("Extracted ID3 metadata from: %s" % audio_path)

        except ImportError:
            logger.debug("Mutagen not available for ID3 extraction")
        except Exception as e:
            logger.error("Failed to extract ID3 metadata: %s %s" %
                         (type(e).__name__, str(e)))

        return metadata

    @classmethod
    def extract(cls, filepath: str) -> Dict[str, Any]:
        """Extract metadata from a file.

        Automatically detects the file type and uses the appropriate
        extraction method.

        Args:
            filepath: Path to the file

        Returns:
            Dictionary of extracted metadata
        """
        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.opf':
            return cls.extract_from_opf(filepath)
        elif ext == '.epub':
            return cls.extract_from_epub(filepath)
        elif ext in ['.mp3', '.m4a', '.m4b', '.flac', '.ogg']:
            return cls.extract_from_id3(filepath)
        else:
            # Fall back to filename parsing
            return cls.extract_from_filename(filepath)

    @staticmethod
    def find_opf_file(directory: str) -> Optional[str]:
        """Find an OPF file in a directory.

        Args:
            directory: Directory to search

        Returns:
            Path to the OPF file, or None if not found
        """
        if not os.path.isdir(directory):
            return None

        for filename in os.listdir(directory):
            if filename.lower().endswith('.opf'):
                return os.path.join(directory, filename)

        return None
