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
Template rendering utilities for LazyLibrarian web interface.

This module provides template rendering with authentication and permission checking.
"""

import os
import threading
from typing import Any

import lazylibrarian
from lazylibrarian import logger
from lazylibrarian.web.auth import get_user_from_cookie, get_template_permission_for_page
from mako import exceptions
from mako.lookup import TemplateLookup


def get_template_lookup() -> TemplateLookup:
    """Get the Mako template lookup configured for the modern theme.

    Returns:
        TemplateLookup instance for the modern interface
    """
    interface_dir = os.path.join(str(lazylibrarian.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), 'modern')

    return TemplateLookup(directories=[template_dir], input_encoding='utf-8')


def serve_template(templatename: str, **kwargs: Any) -> str:
    """Render a template with authentication and permission checking.

    This function:
    1. Sets the current thread name to WEBSERVER
    2. Checks for database upgrade in progress
    3. Handles no user accounts mode
    4. Validates user permissions for the requested template
    5. Renders the template with appropriate context

    Args:
        templatename: The template file to render
        **kwargs: Additional context variables to pass to the template

    Returns:
        The rendered HTML string
    """
    threading.currentThread().name = "WEBSERVER"

    _hplookup = get_template_lookup()

    try:
        # Check for database upgrade in progress
        if lazylibrarian.UPDATE_MSG:
            template = _hplookup.get_template("dbupdate.html")
            return template.render(
                perm=0,
                message="Database upgrade in progress, please wait...",
                title="Database Upgrade",
                timer=5
            )

        # No user accounts - grant admin permissions
        if not lazylibrarian.CONFIG['USER_ACCOUNTS']:
            template = _hplookup.get_template(templatename)
            return template.render(perm=lazylibrarian.perm_admin, **kwargs)

        # Get current user from session
        username, perm = get_user_from_cookie()

        # Check if user is logged in (except for register and response pages)
        if perm == 0 and templatename not in ["register.html", "response.html"]:
            templatename = "login.html"
        else:
            # Check template-specific permissions
            templatename, _ = get_template_permission_for_page(templatename, username or '', perm)

        # Debug logging
        if lazylibrarian.LOGLEVEL & lazylibrarian.log_admin:
            logger.debug("User %s: %s %s" % (username, perm, templatename))

        # Render the template
        template = _hplookup.get_template(templatename)
        if templatename == "login.html":
            return template.render(perm=0, title="Redirected")
        else:
            return template.render(perm=perm, **kwargs)

    except Exception:
        return exceptions.html_error_template().render()


def render_response(message: str, title: str = "Response", timer: int = 0) -> str:
    """Render a simple response page.

    Args:
        message: The message to display
        title: The page title
        timer: Optional auto-redirect timer in seconds

    Returns:
        The rendered HTML string
    """
    _hplookup = get_template_lookup()
    try:
        template = _hplookup.get_template("response.html")
        return template.render(perm=0, message=message, title=title, timer=timer)
    except Exception:
        return exceptions.html_error_template().render()
