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
Unit tests for lazylibrarian.versioncheck module.

Tests cover:
- getInstallType function
- getCurrentVersion function
- getCurrentGitBranch function
- runGit function
- getLatestVersion function
"""

import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, Mock

import lazylibrarian
from lazylibrarian import versioncheck, version


@pytest.fixture
def versioncheck_config():
    """Set up configuration for versioncheck testing."""
    original_config = dict(lazylibrarian.CONFIG)
    original_install_type = lazylibrarian.CONFIG.get('INSTALL_TYPE', '')
    original_prog_dir = lazylibrarian.PROG_DIR
    original_cachedir = getattr(lazylibrarian, 'CACHEDIR', None)

    # Create temp cache directory to avoid test pollution
    temp_cachedir = tempfile.mkdtemp(prefix='ll_versioncheck_test_')

    lazylibrarian.CONFIG['GIT_PROGRAM'] = ''
    lazylibrarian.CONFIG['GIT_HOST'] = 'github.com'
    lazylibrarian.CONFIG['GIT_USER'] = 'lazylibrarian'
    lazylibrarian.CONFIG['GIT_REPO'] = 'LazyLibrarian'
    lazylibrarian.CONFIG['GIT_BRANCH'] = 'master'
    lazylibrarian.CONFIG['GIT_UPDATED'] = 0
    lazylibrarian.CONFIG['INSTALL_TYPE'] = ''
    lazylibrarian.CONFIG['LATEST_VERSION'] = ''
    lazylibrarian.PROG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lazylibrarian.CACHEDIR = temp_cachedir
    lazylibrarian.CURRENT_BRANCH = 'master'

    yield

    lazylibrarian.CONFIG.update(original_config)
    lazylibrarian.CONFIG['INSTALL_TYPE'] = original_install_type
    lazylibrarian.PROG_DIR = original_prog_dir
    lazylibrarian.CACHEDIR = original_cachedir

    # Cleanup temp directory
    if os.path.exists(temp_cachedir):
        shutil.rmtree(temp_cachedir, ignore_errors=True)


class TestGetInstallType:
    """Tests for getInstallType() function."""

    @patch.object(version, 'LAZYLIBRARIAN_VERSION', 'windows')
    def test_getInstallType_windows(self, versioncheck_config):
        """getInstallType should detect Windows install."""
        versioncheck.getInstallType()
        assert lazylibrarian.CONFIG['INSTALL_TYPE'] == 'win'

    @patch.object(version, 'LAZYLIBRARIAN_VERSION', 'win32build')
    def test_getInstallType_win32build(self, versioncheck_config):
        """getInstallType should detect win32build install."""
        versioncheck.getInstallType()
        assert lazylibrarian.CONFIG['INSTALL_TYPE'] == 'win'

    @patch.object(version, 'LAZYLIBRARIAN_VERSION', 'package')
    def test_getInstallType_package(self, versioncheck_config):
        """getInstallType should detect package install."""
        versioncheck.getInstallType()
        assert lazylibrarian.CONFIG['INSTALL_TYPE'] == 'package'

    @patch.object(version, 'LAZYLIBRARIAN_VERSION', 'master')
    def test_getInstallType_git_or_source(self, versioncheck_config):
        """getInstallType should detect git or source install."""
        versioncheck.getInstallType()
        # Will be 'git' if .git folder exists, 'source' otherwise
        assert lazylibrarian.CONFIG['INSTALL_TYPE'] in ['git', 'source']


class TestGetCurrentVersion:
    """Tests for getCurrentVersion() function."""

    def test_getCurrentVersion_no_install_type(self, versioncheck_config):
        """getCurrentVersion should return error message when install type not set."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = ''
        result = versioncheck.getCurrentVersion()
        assert 'Install type not set' in result

    def test_getCurrentVersion_windows(self, versioncheck_config):
        """getCurrentVersion should return 'Windows Install' for win type."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'win'
        result = versioncheck.getCurrentVersion()
        assert result == 'Windows Install'

    def test_getCurrentVersion_package(self, versioncheck_config):
        """getCurrentVersion should return 'No Version File' when version.txt missing."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'package'
        result = versioncheck.getCurrentVersion()
        # With no version.txt file, returns 'No Version File'
        assert result == 'No Version File'

    def test_getCurrentVersion_package_with_version_file(self, versioncheck_config):
        """getCurrentVersion should return version from file for package type."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'package'
        # Create version.txt with a version
        version_file = os.path.join(lazylibrarian.CACHEDIR, 'version.txt')
        with open(version_file, 'w') as f:
            f.write('Package Install')
        result = versioncheck.getCurrentVersion()
        assert result == 'Package Install'


class TestGetCurrentGitBranch:
    """Tests for getCurrentGitBranch() function."""

    def test_getCurrentGitBranch_non_git(self, versioncheck_config):
        """getCurrentGitBranch should return 'NON GIT INSTALL' for non-git installs."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'win'
        result = versioncheck.getCurrentGitBranch()
        assert result == 'NON GIT INSTALL'

    def test_getCurrentGitBranch_package(self, versioncheck_config):
        """getCurrentGitBranch should return 'NON GIT INSTALL' for package installs."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'package'
        result = versioncheck.getCurrentGitBranch()
        assert result == 'NON GIT INSTALL'


class TestRunGit:
    """Tests for runGit() function."""

    def test_runGit_version(self, versioncheck_config):
        """runGit should execute git --version successfully."""
        output, err = versioncheck.runGit('--version')
        if output:
            assert 'git version' in output.lower()

    def test_runGit_invalid_command(self, versioncheck_config):
        """runGit should handle invalid git commands."""
        output, err = versioncheck.runGit('invalid-command-xyz')
        # May return None or error message depending on system


class TestGetLatestVersion:
    """Tests for getLatestVersion() function."""

    def test_getLatestVersion_unknown_install(self, versioncheck_config):
        """getLatestVersion should return 'UNKNOWN INSTALL' when type not set."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = ''
        result = versioncheck.getLatestVersion()
        assert result == 'UNKNOWN INSTALL'

    def test_getLatestVersion_win_install(self, versioncheck_config):
        """getLatestVersion should return 'WINDOWS INSTALL' for Windows."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'win'
        result = versioncheck.getLatestVersion()
        assert result == 'WINDOWS INSTALL'

    @patch('lazylibrarian.versioncheck.requests.get')
    def test_getLatestVersion_package_install(self, mock_get, versioncheck_config):
        """getLatestVersion should fetch from git for package install."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'package'
        # Mock a successful git API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'sha': 'abc123def456'}
        mock_get.return_value = mock_response
        result = versioncheck.getLatestVersion()
        # Should return the commit hash from the API
        assert result is not None


class TestGetLatestVersionFromGit:
    """Tests for getLatestVersion_FromGit() function."""

    def test_getLatestVersion_FromGit_windows(self, versioncheck_config):
        """getLatestVersion_FromGit should return 'WINDOWS INSTALL' for Windows."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'win'
        result = versioncheck.getLatestVersion_FromGit()
        assert result == 'WINDOWS INSTALL'

    @patch('lazylibrarian.versioncheck.requests.get')
    def test_getLatestVersion_FromGit_package(self, mock_get, versioncheck_config):
        """getLatestVersion_FromGit should fetch from git for package install."""
        lazylibrarian.CONFIG['INSTALL_TYPE'] = 'package'
        # Mock a successful git API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'sha': 'abc123def456'}
        mock_get.return_value = mock_response
        result = versioncheck.getLatestVersion_FromGit()
        # Should return the commit hash from the API
        assert result is not None


class TestLogmsg:
    """Tests for logmsg() function."""

    def test_logmsg_when_not_initialized(self, versioncheck_config):
        """logmsg should print when not initialized."""
        original_initialized = lazylibrarian.__INITIALIZED__
        lazylibrarian.__INITIALIZED__ = False

        # Should not raise an exception
        versioncheck.logmsg('debug', 'test message')
        versioncheck.logmsg('info', 'test message')
        versioncheck.logmsg('warn', 'test message')
        versioncheck.logmsg('error', 'test message')

        lazylibrarian.__INITIALIZED__ = original_initialized
