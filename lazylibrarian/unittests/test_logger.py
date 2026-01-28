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
Unit tests for lazylibrarian.logger module.

Tests cover:
- Log level handling
- Log message formatting
- Logger initialization
"""

import os
import tempfile
import pytest
from unittest.mock import patch, Mock

import lazylibrarian
from lazylibrarian import logger


@pytest.fixture
def logger_config():
    """Set up configuration for logger testing."""
    original_config = dict(lazylibrarian.CONFIG)
    original_logdir = lazylibrarian.CONFIG.get('LOGDIR', '')
    original_loglevel = getattr(lazylibrarian, 'LOGLEVEL', 0)
    original_initialized = getattr(lazylibrarian, '__INITIALIZED__', False)

    with tempfile.TemporaryDirectory() as tmpdir:
        lazylibrarian.CONFIG['LOGDIR'] = tmpdir
        lazylibrarian.CONFIG['LOGSIZE'] = 204800
        lazylibrarian.CONFIG['LOGFILES'] = 5
        lazylibrarian.CONFIG['LOGLEVEL'] = 1
        lazylibrarian.LOGLEVEL = 1

        yield tmpdir

    lazylibrarian.CONFIG.update(original_config)
    lazylibrarian.CONFIG['LOGDIR'] = original_logdir
    lazylibrarian.LOGLEVEL = original_loglevel


class TestLoggerFunctions:
    """Tests for logger module functions."""

    def test_logger_debug_when_debug_enabled(self, logger_config):
        """Logger should log debug messages when debug level is enabled."""
        lazylibrarian.LOGLEVEL = 2  # Enable debug
        # Should not raise
        logger.debug('Test debug message')

    def test_logger_info(self, logger_config):
        """Logger should log info messages."""
        # Should not raise
        logger.info('Test info message')

    def test_logger_warn(self, logger_config):
        """Logger should log warning messages."""
        # Should not raise
        logger.warn('Test warning message')

    def test_logger_error(self, logger_config):
        """Logger should log error messages."""
        # Should not raise
        logger.error('Test error message')


class TestLogLevelFlags:
    """Tests for log level flag constants."""

    def test_log_magdates_flag(self):
        """log_magdates should be defined."""
        assert hasattr(lazylibrarian, 'log_magdates')
        assert lazylibrarian.log_magdates == 4

    def test_log_searchmag_flag(self):
        """log_searchmag should be defined."""
        assert hasattr(lazylibrarian, 'log_searchmag')
        assert lazylibrarian.log_searchmag == 8

    def test_log_dlcomms_flag(self):
        """log_dlcomms should be defined."""
        assert hasattr(lazylibrarian, 'log_dlcomms')
        assert lazylibrarian.log_dlcomms == 16

    def test_log_dbcomms_flag(self):
        """log_dbcomms should be defined."""
        assert hasattr(lazylibrarian, 'log_dbcomms')
        assert lazylibrarian.log_dbcomms == 32

    def test_log_postprocess_flag(self):
        """log_postprocess should be defined."""
        assert hasattr(lazylibrarian, 'log_postprocess')
        assert lazylibrarian.log_postprocess == 64

    def test_log_fuzz_flag(self):
        """log_fuzz should be defined."""
        assert hasattr(lazylibrarian, 'log_fuzz')
        assert lazylibrarian.log_fuzz == 128

    def test_log_serverside_flag(self):
        """log_serverside should be defined."""
        assert hasattr(lazylibrarian, 'log_serverside')
        assert lazylibrarian.log_serverside == 256

    def test_log_flags_are_powers_of_two(self):
        """Log flags should be powers of 2 for bitwise operations."""
        flags = [
            lazylibrarian.log_magdates,
            lazylibrarian.log_searchmag,
            lazylibrarian.log_dlcomms,
            lazylibrarian.log_dbcomms,
            lazylibrarian.log_postprocess,
            lazylibrarian.log_fuzz,
            lazylibrarian.log_serverside,
        ]
        for flag in flags:
            # Check if power of 2 (only one bit set)
            assert flag > 0
            assert (flag & (flag - 1)) == 0


class TestLogLevelOperations:
    """Tests for log level bitwise operations."""

    def test_loglevel_can_combine_flags(self):
        """Log level flags can be combined with bitwise OR."""
        combined = lazylibrarian.log_dlcomms | lazylibrarian.log_dbcomms
        assert combined == 48  # 16 + 32

    def test_loglevel_check_with_bitwise_and(self):
        """Log level check uses bitwise AND."""
        level = lazylibrarian.log_dlcomms | lazylibrarian.log_dbcomms  # 48

        # Check if dlcomms is enabled
        assert level & lazylibrarian.log_dlcomms

        # Check if postprocess is NOT enabled
        assert not (level & lazylibrarian.log_postprocess)
