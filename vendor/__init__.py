# Vendor directory for custom/modified third-party libraries
# These libraries are bundled because they have LazyLibrarian-specific modifications
# or require specific versions incompatible with modern pip packages.
#
# Libraries in this directory:
# - apscheduler: v2.0.0-rc2 (v3+ has breaking API changes)
# - cherrypy_cors: Custom CORS implementation for CherryPy
# - deluge_client: Modified to use LazyLibrarian's logging system
# - gntp: Growl notifications (unmaintained upstream)
# - httpagentparser: User agent parsing
# - magic: File type detection
# - mobi: MOBI file parsing
# - oauth2: Pinned version for Goodreads API compatibility
# - pynma: Notify My Android notifications
# - pythontwitter: Depends on pinned oauth2
# - tinytag: Modified with composer field + m4b support
# - unrar: RAR extraction
# - rfeed: RSS feed generation
