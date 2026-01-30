#  This file is part of Bookbag of Holding.
#  Bookbag of Holding is free software':'you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Bookbag of Holding is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Bookbag of Holding.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import cherrypy
import cherrypy_cors
import bookbagofholding
from bookbagofholding import logger
from bookbagofholding.webServe import WebInterface

cp_ver = getattr(cherrypy, '__version__', None)
if cp_ver and int(cp_ver.split('.')[0]) >= 10:
    try:
        import portend
    except ImportError:
        portend = None


def initialize(options=None):
    if options is None:
        options = {}
    https_enabled = options['https_enabled']
    https_cert = options['https_cert']
    https_key = options['https_key']

    if https_enabled:
        if not (os.path.exists(https_cert) and os.path.exists(https_key)):
            logger.warn("Disabled HTTPS because of missing certificate and key.")
            https_enabled = False

    options_dict = {
        'log.screen': False,
        'server.thread_pool': 10,
        'server.socket_port': options['http_port'],
        'server.socket_host': options['http_host'],
        'engine.autoreload.on': False,
        'tools.encode.on': True,
        'tools.encode.encoding': 'utf-8',
        'tools.decode.on': True,
        'error_page.401': bookbagofholding.common.error_page_401,
    }

    if https_enabled:
        options_dict['server.ssl_certificate'] = https_cert
        options_dict['server.ssl_private_key'] = https_key
        protocol = "https"
    else:
        protocol = "http"

    logger.info("Starting Bookbag of Holding web server on %s://%s:%d/" %
                (protocol, options['http_host'], options['http_port']))
    cherrypy_cors.install()
    cherrypy.config.update(options_dict)

    conf = {
        '/': {
            # 'tools.staticdir.on': True,
            # 'tools.staticdir.dir': os.path.join(bookbagofholding.PROG_DIR, 'data'),
            'tools.staticdir.root': os.path.join(bookbagofholding.PROG_DIR, 'data'),
            'tools.proxy.on': options['http_proxy']  # pay attention to X-Forwarded-Proto header
        },
        '/api': {
            'cors.expose.on': True,
        },
        '/interfaces': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(bookbagofholding.PROG_DIR, 'data', 'interfaces')
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(bookbagofholding.PROG_DIR, 'data', 'images')
        },
        '/cache': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': bookbagofholding.CACHEDIR
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(bookbagofholding.PROG_DIR, 'data', 'css')
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(bookbagofholding.PROG_DIR, 'data', 'js')
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            # 'tools.staticfile.filename': "images/favicon.ico"
            'tools.staticfile.filename': os.path.join(bookbagofholding.PROG_DIR, 'data', 'images', 'favicon.ico')
        },
        '/opensearch.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearch.xml')
        },
        '/opensearchbooks.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearchbooks.xml')
        },
        '/opensearchgenres.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearchgenres.xml')
        },
        '/opensearchmagazines.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearchmagazines.xml')
        },
        '/opensearchseries.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearchseries.xml')
        },
        '/opensearchauthors.xml': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(bookbagofholding.CACHEDIR, 'opensearchauthors.xml')
        }
    }

    if bookbagofholding.CONFIG['PROXY_LOCAL']:
        conf['/'].update({
            # NOTE default if not specified is to use apache style X-Forwarded-Host
            # 'tools.proxy.local': 'X-Forwarded-Host'  # this is for apache2
            # 'tools.proxy.local': 'Host'  # this is for nginx
            # 'tools.proxy.local': 'X-Host'  # this is for lighthttpd
            'tools.proxy.local': bookbagofholding.CONFIG['PROXY_LOCAL']
        })
    if options['http_pass'] != "":
        logger.info("Web server authentication is enabled, username is '%s'" % options['http_user'])
        conf['/'].update({
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'Bookbag of Holding',
            'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict({
                options['http_user']: options['http_pass']
            })
        })
        conf['/api'].update({
            'tools.auth_basic.on': False,
        })
    if options['opds_authentication']:
        user_list = {}
        if len(options['opds_username']) > 0:
            user_list[options['opds_username']] = options['opds_password']
        if options['http_pass'] is not None and options['http_user'] != options['opds_username']:
            user_list[options['http_user']] = options['http_pass']
        conf['/opds'] = {'tools.auth_basic.on': True,
                         'tools.auth_basic.realm': 'Bookbag of Holding OPDS',
                         'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict(user_list)}
    else:
        conf['/opds'] = {'tools.auth_basic.on': False}

    opensearch = os.path.join(bookbagofholding.PROG_DIR, 'data', 'opensearch.template')
    if os.path.exists(opensearch):
        with open(opensearch, 'r') as s:
            data = s.read().splitlines()
        # (title, function)
        for item in [('Authors', 'Authors'),
                     ('Magazines', 'RecentMags'),
                     ('Books', 'RecentBooks'),
                     ('Genres', 'Genres'),
                     ('Series', 'Series')]:
            with open(os.path.join(bookbagofholding.CACHEDIR, 'opensearch%s.xml' % item[0].lower()), 'w') as t:
                for l in data:
                    t.write(l.replace('{label}', item[0]).replace(
                                      '{func}', 't=%s&amp;' % item[1]).replace(
                                      '{webroot}', options['http_root']))
                    t.write('\n')

    # Prevent time-outs (timeout_monitor was removed in newer CherryPy versions)
    try:
        cherrypy.engine.timeout_monitor.unsubscribe()
    except AttributeError:
        pass
    cherrypy.tree.mount(WebInterface(), str(options['http_root']), config=conf)

    if bookbagofholding.CHERRYPYLOG:
        cherrypy.config.update({
            'log.access_file': os.path.join(bookbagofholding.CONFIG['LOGDIR'], 'cherrypy.access.log'),
            'log.error_file': os.path.join(bookbagofholding.CONFIG['LOGDIR'], 'cherrypy.error.log'),
        })

    cherrypy.engine.autoreload.subscribe()

    try:
        if cp_ver and int(cp_ver.split('.')[0]) >= 10:
            portend.Checker().assert_free(str(options['http_host']), options['http_port'])
        else:
            cherrypy.process.servers.check_port(str(options['http_host']), options['http_port'])
        cherrypy.server.start()
    except Exception as e:
        print(str(e))
        print('Failed to start on port: %i. Is something else running?' % (options['http_port']))
        sys.exit(1)

    cherrypy.server.wait()
