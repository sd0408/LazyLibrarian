#  This file is part of Bookbag of Holding.
#
#  Bookbag of Holding is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

"""
Unit tests for bookbagofholding.logger module.

Tests cover:
- Log level handling
- Log message formatting
- Logger initialization
"""

import os
import tempfile
import pytest
from unittest.mock import patch, Mock

import bookbagofholding
from bookbagofholding import logger


@pytest.fixture
def logger_config():
    """Set up configuration for logger testing."""
    original_config = dict(bookbagofholding.CONFIG)
    original_logdir = bookbagofholding.CONFIG.get('LOGDIR', '')
    original_loglevel = getattr(bookbagofholding, 'LOGLEVEL', 0)
    original_initialized = getattr(bookbagofholding, '__INITIALIZED__', False)

    with tempfile.TemporaryDirectory() as tmpdir:
        bookbagofholding.CONFIG['LOGDIR'] = tmpdir
        bookbagofholding.CONFIG['LOGSIZE'] = 204800
        bookbagofholding.CONFIG['LOGFILES'] = 5
        bookbagofholding.CONFIG['LOGLEVEL'] = 1
        bookbagofholding.LOGLEVEL = 1

        yield tmpdir

    bookbagofholding.CONFIG.update(original_config)
    bookbagofholding.CONFIG['LOGDIR'] = original_logdir
    bookbagofholding.LOGLEVEL = original_loglevel


class TestLoggerFunctions:
    """Tests for logger module functions."""

    def test_logger_debug_when_debug_enabled(self, logger_config):
        """Logger should log debug messages when debug level is enabled."""
        bookbagofholding.LOGLEVEL = 2  # Enable debug
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

    def test_log_dlcomms_flag(self):
        """log_dlcomms should be defined."""
        assert hasattr(bookbagofholding, 'log_dlcomms')
        assert bookbagofholding.log_dlcomms == 16

    def test_log_dbcomms_flag(self):
        """log_dbcomms should be defined."""
        assert hasattr(bookbagofholding, 'log_dbcomms')
        assert bookbagofholding.log_dbcomms == 32

    def test_log_postprocess_flag(self):
        """log_postprocess should be defined."""
        assert hasattr(bookbagofholding, 'log_postprocess')
        assert bookbagofholding.log_postprocess == 64

    def test_log_fuzz_flag(self):
        """log_fuzz should be defined."""
        assert hasattr(bookbagofholding, 'log_fuzz')
        assert bookbagofholding.log_fuzz == 128

    def test_log_serverside_flag(self):
        """log_serverside should be defined."""
        assert hasattr(bookbagofholding, 'log_serverside')
        assert bookbagofholding.log_serverside == 256

    def test_log_flags_are_powers_of_two(self):
        """Log flags should be powers of 2 for bitwise operations."""
        flags = [
            bookbagofholding.log_dlcomms,
            bookbagofholding.log_dbcomms,
            bookbagofholding.log_postprocess,
            bookbagofholding.log_fuzz,
            bookbagofholding.log_serverside,
        ]
        for flag in flags:
            # Check if power of 2 (only one bit set)
            assert flag > 0
            assert (flag & (flag - 1)) == 0


class TestLogLevelOperations:
    """Tests for log level bitwise operations."""

    def test_loglevel_can_combine_flags(self):
        """Log level flags can be combined with bitwise OR."""
        combined = bookbagofholding.log_dlcomms | bookbagofholding.log_dbcomms
        assert combined == 48  # 16 + 32

    def test_loglevel_check_with_bitwise_and(self):
        """Log level check uses bitwise AND."""
        level = bookbagofholding.log_dlcomms | bookbagofholding.log_dbcomms  # 48

        # Check if dlcomms is enabled
        assert level & bookbagofholding.log_dlcomms

        # Check if postprocess is NOT enabled
        assert not (level & bookbagofholding.log_postprocess)
