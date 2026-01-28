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
Post-processing pipeline for LazyLibrarian.

This module contains the refactored post-processing pipeline, organized into
focused components:

- detector.py - File type detection
- unpacker.py - Archive extraction
- metadata.py - Metadata extraction (OPF, ID3, filename)
- matcher.py - Book identification and fuzzy matching
- organizer.py - File organization and renaming
- cover.py - Cover extraction
- database.py - Database updates

The pipeline coordinates these components to process downloaded files.
"""

from lazylibrarian.postprocess_v2.detector import FileDetector
from lazylibrarian.postprocess_v2.unpacker import ArchiveUnpacker
from lazylibrarian.postprocess_v2.metadata import MetadataExtractor
from lazylibrarian.postprocess_v2.matcher import BookMatcher
from lazylibrarian.postprocess_v2.organizer import FileOrganizer

__all__ = [
    'FileDetector',
    'ArchiveUnpacker',
    'MetadataExtractor',
    'BookMatcher',
    'FileOrganizer',
]
