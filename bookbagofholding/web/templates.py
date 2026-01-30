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
Template rendering utilities for Bookbag of Holding web interface.

This module provides template rendering with authentication and permission checking.
"""

import os
import threading
from typing import Any

import bookbagofholding
from bookbagofholding import logger
from bookbagofholding.web.auth import get_current_user, PERM_ADMIN, PERM_GUEST
from mako import exceptions
from mako.lookup import TemplateLookup


def get_template_lookup() -> TemplateLookup:
    """Get the Mako template lookup configured for the modern theme.

    Returns:
        TemplateLookup instance for the modern interface
    """
    interface_dir = os.path.join(str(bookbagofholding.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), 'modern')

    return TemplateLookup(directories=[template_dir], input_encoding='utf-8')


def serve_template(templatename: str, **kwargs: Any) -> str:
    """Render a template with simplified Radarr-style authentication.

    AUTH_METHOD options:
    - None: No authentication, everyone has admin access
    - Forms: Login page with username/password
    - Basic: HTTP Basic Auth (handled by CherryPy)
    - External: Trust reverse proxy header (AUTH_HEADER config)

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
        if bookbagofholding.UPDATE_MSG:
            template = _hplookup.get_template("dbupdate.html")
            return template.render(
                perm=0,
                message="Database upgrade in progress, please wait...",
                title="Database Upgrade",
                timer=5
            )

        # Simplified Radarr-style auth
        auth_method = bookbagofholding.CONFIG.get('AUTH_METHOD', 'None')

        # Initialize auth variables
        username = ''
        fullname = ''
        perm = 0
        role = ''
        authenticated = False

        # No auth - grant admin permissions to everyone
        if auth_method == 'None':
            authenticated = True
            username = 'admin'
            fullname = 'Admin'
            perm = PERM_ADMIN
            role = 'admin'
        else:
            # Get current user from session
            user = get_current_user()
            if user:
                authenticated = True
                username = user['UserName'] if user['UserName'] else 'admin'
                fullname = user['Name'] if user['Name'] else username
                perm = user['Perms'] if user['Perms'] else PERM_ADMIN
                role = user['Role'] if user['Role'] else 'admin'

        # Check if user is logged in (except for login and response pages)
        if not authenticated and templatename not in ["login.html", "response.html"]:
            templatename = "login.html"

        # Debug logging
        if bookbagofholding.LOGLEVEL & bookbagofholding.log_admin:
            logger.debug("User %s: %s %s" % (username, perm, templatename))

        # Render the template
        template = _hplookup.get_template(templatename)
        if templatename == "login.html":
            return template.render(perm=0, title="Redirected")
        else:
            # Remove any conflicting keys from kwargs
            kwargs.pop('user', None)
            kwargs.pop('perm', None)
            kwargs.pop('role', None)
            kwargs.pop('fullname', None)
            return template.render(perm=perm, user=username, fullname=fullname, role=role, **kwargs)

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
