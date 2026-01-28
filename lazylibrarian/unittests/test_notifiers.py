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
Unit tests for lazylibrarian.notifiers module.

Tests cover:
- Notification dispatch
- Individual notifier configuration
- Notifier enable/disable logic
"""

import pytest
from unittest.mock import patch, Mock, MagicMock

import lazylibrarian
from lazylibrarian import notifiers
from lazylibrarian.notifiers import email_notify, pushbullet, pushover, telegram, slack


@pytest.fixture
def notifier_config():
    """Set up configuration for notifier testing."""
    original_config = dict(lazylibrarian.CONFIG)

    # Set up all notifier configs to disabled by default
    lazylibrarian.CONFIG['USE_EMAIL'] = False
    lazylibrarian.CONFIG['USE_PUSHBULLET'] = False
    lazylibrarian.CONFIG['USE_PUSHOVER'] = False
    lazylibrarian.CONFIG['USE_TELEGRAM'] = False
    lazylibrarian.CONFIG['USE_SLACK'] = False
    lazylibrarian.CONFIG['USE_BOXCAR'] = False
    lazylibrarian.CONFIG['USE_PROWL'] = False
    lazylibrarian.CONFIG['USE_GROWL'] = False
    lazylibrarian.CONFIG['USE_NMA'] = False
    lazylibrarian.CONFIG['USE_ANDROIDPN'] = False
    lazylibrarian.CONFIG['USE_CUSTOM'] = False

    yield

    lazylibrarian.CONFIG.update(original_config)


class TestNotifiersModule:
    """Tests for the notifiers __init__ module."""

    def test_notifiers_module_imports(self):
        """Notifiers module should import successfully."""
        import lazylibrarian.notifiers
        assert lazylibrarian.notifiers is not None

    def test_notify_snatch_function_exists(self, notifier_config):
        """notify_snatch function should exist."""
        assert hasattr(notifiers, 'notify_snatch')
        assert callable(notifiers.notify_snatch)

    def test_notify_download_function_exists(self, notifier_config):
        """notify_download function should exist."""
        assert hasattr(notifiers, 'notify_download')
        assert callable(notifiers.notify_download)

    def test_notify_snatch_with_all_disabled(self, notifier_config):
        """notify_snatch should not crash when all notifiers disabled."""
        # All notifiers disabled by default in fixture
        # Should not raise
        notifiers.notify_snatch('Test Book')

    def test_notify_download_with_all_disabled(self, notifier_config):
        """notify_download should not crash when all notifiers disabled."""
        # All notifiers disabled by default in fixture
        # Should not raise
        notifiers.notify_download('Test Book')


class TestEmailNotifier:
    """Tests for email notifier module."""

    def test_email_module_imports(self):
        """Email notifier module should import successfully."""
        from lazylibrarian.notifiers import email_notify
        assert email_notify is not None

    def test_email_notifier_class_exists(self):
        """Email notifier should have EmailNotifier class."""
        from lazylibrarian.notifiers import email_notify
        assert hasattr(email_notify, 'EmailNotifier')

    def test_email_notifier_class_has_methods(self):
        """EmailNotifier class should have required methods."""
        from lazylibrarian.notifiers import email_notify
        notifier = email_notify.EmailNotifier()
        assert hasattr(notifier, 'notify_snatch')
        assert hasattr(notifier, 'notify_download')


class TestPushbulletNotifier:
    """Tests for Pushbullet notifier module."""

    def test_pushbullet_module_imports(self):
        """Pushbullet notifier module should import successfully."""
        from lazylibrarian.notifiers import pushbullet
        assert pushbullet is not None

    def test_pushbullet_class_exists(self):
        """Pushbullet notifier should have PushbulletNotifier class."""
        from lazylibrarian.notifiers import pushbullet
        assert hasattr(pushbullet, 'PushbulletNotifier')


class TestPushoverNotifier:
    """Tests for Pushover notifier module."""

    def test_pushover_module_imports(self):
        """Pushover notifier module should import successfully."""
        from lazylibrarian.notifiers import pushover
        assert pushover is not None

    def test_pushover_class_exists(self):
        """Pushover notifier should have PushoverNotifier class."""
        from lazylibrarian.notifiers import pushover
        assert hasattr(pushover, 'PushoverNotifier')


class TestTelegramNotifier:
    """Tests for Telegram notifier module."""

    def test_telegram_module_imports(self):
        """Telegram notifier module should import successfully."""
        from lazylibrarian.notifiers import telegram
        assert telegram is not None

    def test_telegram_class_exists(self):
        """Telegram notifier should have Telegram_Notifier class."""
        from lazylibrarian.notifiers import telegram
        assert hasattr(telegram, 'Telegram_Notifier')


class TestSlackNotifier:
    """Tests for Slack notifier module."""

    def test_slack_module_imports(self):
        """Slack notifier module should import successfully."""
        from lazylibrarian.notifiers import slack
        assert slack is not None

    def test_slack_class_exists(self):
        """Slack notifier should have SlackNotifier class."""
        from lazylibrarian.notifiers import slack
        assert hasattr(slack, 'SlackNotifier')


class TestBoxcarNotifier:
    """Tests for Boxcar notifier module."""

    def test_boxcar_module_imports(self):
        """Boxcar notifier module should import successfully."""
        from lazylibrarian.notifiers import boxcar
        assert boxcar is not None


class TestProwlNotifier:
    """Tests for Prowl notifier module."""

    def test_prowl_module_imports(self):
        """Prowl notifier module should import successfully."""
        from lazylibrarian.notifiers import prowl
        assert prowl is not None


class TestGrowlNotifier:
    """Tests for Growl notifier module."""

    def test_growl_module_imports(self):
        """Growl notifier module should import successfully."""
        from lazylibrarian.notifiers import growl
        assert growl is not None


class TestNmaNotifier:
    """Tests for NMA (Notify My Android) notifier module."""

    def test_nma_module_imports(self):
        """NMA notifier module should import successfully."""
        from lazylibrarian.notifiers import nma
        assert nma is not None


class TestAndroidpnNotifier:
    """Tests for AndroidPN notifier module."""

    def test_androidpn_module_imports(self):
        """AndroidPN notifier module should import successfully."""
        from lazylibrarian.notifiers import androidpn
        assert androidpn is not None


class TestCustomNotifier:
    """Tests for Custom notifier module."""

    def test_custom_module_imports(self):
        """Custom notifier module should import successfully."""
        from lazylibrarian.notifiers import custom_notify
        assert custom_notify is not None
