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
import re
import time

from urllib.parse import quote_plus, quote, urlencode

import bookbagofholding
from bookbagofholding import logger, database
from bookbagofholding.cache import fetchURL, gb_json_request
from bookbagofholding.common import proxyList
from bookbagofholding.formatter import safe_unicode, plural, cleanName, unaccented, formatAuthorName, \
    check_int, replace_all, check_year, getList
from fuzzywuzzy import fuzz

import requests


def setAllBookAuthors():
    myDB = database.DBConnection()
    myDB.action('drop table if exists bookauthors')
    myDB.action('create table bookauthors (AuthorID TEXT, BookID TEXT, Role TEXT, UNIQUE (AuthorID, BookID, Role))')
    books = myDB.select('SELECT AuthorID,BookID from books')
    for item in books:
        myDB.action('insert into bookauthors (AuthorID, BookID, Role) values (?, ?, ?)',
                    (item['AuthorID'], item['BookID'], ''), suppress='UNIQUE')
    totalauthors = 0
    totalrefs = 0
    books = myDB.select('select bookid,bookname,authorid from books where workpage is not null and workpage != ""')
    for book in books:
        newauthors, newrefs = setBookAuthors(book)
        totalauthors += newauthors
        totalrefs += newrefs
    msg = "Added %s new authors to database, %s new bookauthors" % (totalauthors, totalrefs)
    logger.debug(msg)
    return totalauthors, totalrefs


def setBookAuthors(book):
    myDB = database.DBConnection()
    newauthors = 0
    newrefs = 0
    try:
        authorlist = getBookAuthors(book['bookid'])
        for author in authorlist:
            role = ''
            # librarything data source
            authorname = formatAuthorName(author['name'])
            exists = myDB.match('select authorid from authors where authorname=?', (authorname,))
            if 'type' in author:
                authtype = author['type']
                if authtype in ['primary author', 'main author', 'secondary author']:
                    role = authtype
                elif author['role'] in ['Author', '&mdash;'] and author['work'] == 'all editions':
                    role = 'Author'
            if exists:
                authorid = exists['authorid']
            else:
                # try to add new author to database by name
                authorname, authorid, new = bookbagofholding.importer.addAuthorNameToDB(authorname, False, False)
                if new and authorid:
                    newauthors += 1
            if authorid:
                myDB.action('INSERT into bookauthors (AuthorID, BookID, Role) VALUES (?, ?, ?)',
                            (authorid, book['bookid'], role), suppress='UNIQUE')
                newrefs += 1
    except Exception as e:
        logger.error("Error parsing authorlist for %s: %s %s" % (book['bookname'], type(e).__name__, str(e)))
    return newauthors, newrefs


def setStatus(bookid=None, default=None):
    """ Set the status of a book according to author/newbook/newauthor preferences
        return default if unchanged, default is passed in as newbook or newauthor status """
    myDB = database.DBConnection()
    if not bookid:
        return default

    match = myDB.match('SELECT Status,AuthorID,BookName from books WHERE BookID=?', (bookid,))
    if not match:
        return default

    # Don't update status if we already have the book
    current_status = match['Status']
    if current_status in ['Have', 'Open']:
        return current_status

    new_status = ''
    authorid = match['AuthorID']
    bookname = match['BookName']

    # Author we want or don't want?
    match = myDB.match('SELECT Status from authors where AuthorID=?', (authorid,))
    if match:
        if match['Status'] in ['Paused', 'Ignored']:
            new_status = 'Skipped'
            logger.debug('Marking %s as %s, author %s' % (bookname, new_status, match['Status']))
        if match['Status'] == 'Wanted':
            new_status = 'Wanted'
            logger.debug('Marking %s as %s, author %s' % (bookname, new_status, match['Status']))

    # If none of these, leave default "newbook" or "newauthor" status
    if new_status:
        myDB.action('UPDATE books SET Status=? WHERE BookID=?', (new_status, bookid))
        return new_status

    return default


def setWorkPages():
    """ Set the workpage link for any books that don't already have one """

    myDB = database.DBConnection()
    cmd = 'select BookID,AuthorName,BookName from books,authors where length(WorkPage) < 4'
    cmd += ' and books.AuthorID = authors.AuthorID'
    books = myDB.select(cmd)
    if books:
        logger.debug('Setting WorkPage for %s book%s' % (len(books), plural(len(books))))
        counter = 0
        for book in books:
            bookid = book['BookID']
            worklink = getWorkPage(bookid)
            if worklink:
                controlValueDict = {"BookID": bookid}
                newValueDict = {"WorkPage": worklink}
                myDB.upsert("books", newValueDict, controlValueDict)
                counter += 1
            else:
                logger.debug('No WorkPage found for %s: %s' % (book['AuthorName'], book['BookName']))
        msg = 'Updated %s page%s' % (counter, plural(counter))
        logger.debug("setWorkPages complete: " + msg)
    else:
        msg = 'No missing WorkPages'
        logger.debug(msg)
    return msg


def setWorkID(books=None):
    """ WorkID was a Goodreads-specific feature that is no longer available
        since Goodreads API has been deprecated """
    msg = 'WorkID feature not available (requires deprecated Goodreads API)'
    logger.debug(msg)
    return msg


def librarything_wait():
    """ Wait for a second between librarything api calls """
    time_now = time.time()
    delay = time_now - bookbagofholding.LAST_LIBRARYTHING
    if delay < 1.0:
        sleep_time = 1.0 - delay
        bookbagofholding.LT_SLEEP += sleep_time
        logger.debug("LibraryThing sleep %.3f, total %.3f" % (sleep_time, bookbagofholding.LT_SLEEP))
        time.sleep(sleep_time)
    bookbagofholding.LAST_LIBRARYTHING = time_now


# Feb 2018 librarything have disabled "whatwork"
# might only be temporary, but for now disable looking for new workpages
# and do not expire cached ones
ALLOW_NEW = False
LAST_NEW = 0


def getBookWork(bookID=None, reason=None):
    """ return the contents of the LibraryThing workpage for the given bookid
        preferably from the cache. If not already cached cache the results
        Return None if no workpage available """
    global ALLOW_NEW, LAST_NEW
    if not bookID:
        logger.error("getBookWork - No bookID")
        return None

    if not reason:
        reason = ""

    myDB = database.DBConnection()
    cmd = 'select BookName,AuthorName,BookISBN from books,authors where bookID=?'
    cmd += ' and books.AuthorID = authors.AuthorID'
    cacheLocation = "WorkCache"
    item = myDB.match(cmd, (bookID,))
    if item:
        cacheLocation = os.path.join(bookbagofholding.CACHEDIR, cacheLocation)
        workfile = os.path.join(cacheLocation, str(bookID) + '.html')

        # does the workpage need to expire? For now only expire if it was an error page (small file)
        if os.path.isfile(workfile):
            if os.path.getsize(workfile) < 500:
                cache_modified_time = os.stat(workfile).st_mtime
                time_now = time.time()
                expiry = bookbagofholding.CONFIG['CACHE_AGE'] * 24 * 60 * 60  # expire cache after this many seconds
                if cache_modified_time < time_now - expiry:
                    # Cache entry is too old, delete it
                    if ALLOW_NEW:
                        os.remove(workfile)

        if os.path.isfile(workfile):
            # use cached file if possible to speed up refreshactiveauthors and librarysync re-runs
            bookbagofholding.CACHE_HIT = int(bookbagofholding.CACHE_HIT) + 1
            if reason:
                logger.debug("getBookWork: Returning Cached entry for %s %s" % (bookID, reason))
            else:
                logger.debug("getBookWork: Returning Cached workpage for %s" % bookID)

            # noinspection PyArgumentList
            with open(workfile, "r", errors="backslashreplace") as cachefile:
                source = cachefile.read()
            return source
        else:
            bookbagofholding.CACHE_MISS = int(bookbagofholding.CACHE_MISS) + 1
            if not ALLOW_NEW:
                # don't nag. Show message no more than every 12 hrs
                timenow = int(time.time())
                if check_int(LAST_NEW, 0) + 43200 < timenow:
                    logger.warn("New WhatWork is disabled")
                    LAST_NEW = timenow
                return None
            title = safe_unicode(item['BookName'])
            author = safe_unicode(item['AuthorName'])
            URL = 'http://www.librarything.com/api/whatwork.php?author=%s&title=%s' % \
                  (quote_plus(author), quote_plus(title))

            librarything_wait()
            result, success = fetchURL(URL)
            if success:
                # noinspection PyBroadException
                try:
                    workpage = result.split('<link>')[1].split('</link>')[0]
                    librarything_wait()
                    result, success = fetchURL(workpage)
                except Exception:
                    try:
                        errmsg = result.split('<error>')[1].split('</error>')[0]
                    except IndexError:
                        errmsg = "Unknown Error"
                    # if no workpage link, try isbn instead
                    if item['BookISBN']:
                        URL = 'http://www.librarything.com/api/whatwork.php?isbn=' + item['BookISBN']
                        librarything_wait()
                        result, success = fetchURL(URL)
                        if success:
                            # noinspection PyBroadException
                            try:
                                workpage = result.split('<link>')[1].split('</link>')[0]
                                librarything_wait()
                                result, success = fetchURL(workpage)
                            except Exception:
                                # no workpage link found by isbn
                                try:
                                    errmsg = result.split('<error>')[1].split('</error>')[0]
                                except IndexError:
                                    errmsg = "Unknown Error"
                                # still cache if whatwork returned a result without a link, so we don't keep retrying
                                logger.debug("Librarything: [%s] for ISBN %s" % (errmsg, item['BookISBN']))
                                success = True
                    else:
                        # still cache if whatwork returned a result without a link, so we don't keep retrying
                        msg = "Librarything: [" + errmsg + "] for "
                        logger.debug(msg + item['AuthorName'] + ' ' + item['BookName'])
                        success = True
            if success:
                with open(workfile, "w") as cachefile:
                    cachefile.write(result)
                    logger.debug("getBookWork: Caching workpage for %s" % workfile)
                    # return None if we got an error page back
                    if '</request><error>' in result:
                        return None
                return result
            else:
                logger.debug("getBookWork: Unable to cache workpage, got %s" % result)
            return None
    else:
        logger.debug('Get Book Work - Invalid bookID [%s]' % bookID)
        return None


def getWorkPage(bookID=None):
    """ return the URL of the LibraryThing workpage for the given bookid
        or an empty string if no workpage available """
    if not bookID:
        logger.error("getWorkPage - No bookID")
        return ''
    work = getBookWork(bookID, "Workpage")
    if work:
        try:
            page = work.split('og:url')[1].split('="')[1].split('"')[0]
        except IndexError:
            return ''
        return page
    return ''


def getBookAuthors(bookid):
    """ Get a list of authors contributing to a book from the librarything bookwork file """
    authorlist = []
    data = getBookWork(bookid, "Authors")
    if data:
        try:
            data = data.split('otherauthors_container')[1].split('</table>')[0].split('<table')[1].split('>', 1)[1]
        except IndexError:
            data = ''

    if data and 'Work?' in data:
        try:
            rows = data.split('<tr')
            for row in rows[2:]:
                author = {}
                col = row.split('<td>')
                author['name'] = col[1].split('">')[1].split('<')[0]
                author['role'] = col[2].split('<')[0]
                author['type'] = col[3].split('<')[0]
                author['work'] = col[4].split('<')[0]
                author['status'] = col[5].split('<')[0]
                authorlist.append(author)
        except IndexError:
            logger.debug('Error parsing authorlist for %s' % bookid)
    return authorlist


def get_book_desc(isbn=None, author=None, title=None):
    """ Try to get missing book descriptions from googlebooks
        Return description, empty string if not found, None if error"""
    if not author or not title:
        return ''

    author = cleanName(author)
    title = cleanName(title)
    baseurl = 'https://www.googleapis.com/books/v1/volumes?q='

    urls = [baseurl + quote_plus('inauthor:%s intitle:%s' % (author, title))]
    if isbn:
        urls.insert(0, baseurl + quote_plus('isbn:' + isbn))

    for url in urls:
        if bookbagofholding.CONFIG['GB_API']:
            url += '&key=' + bookbagofholding.CONFIG['GB_API']
        if bookbagofholding.CONFIG['GB_COUNTRY'] and len(bookbagofholding.CONFIG['GB_COUNTRY'] == 2):
            url += '&country=' + bookbagofholding.CONFIG['GB_COUNTRY']
        results, cached = gb_json_request(url)
        if results is None:  # there was an error
            return None
        if results and not cached:
            time.sleep(1)
        if results and 'items' in results:
            for item in results['items']:
                # noinspection PyBroadException
                try:
                    auth = item['volumeInfo']['authors'][0]
                    book = item['volumeInfo']['title']
                    desc = item['volumeInfo']['description']
                    book_fuzz = fuzz.token_set_ratio(book, title)
                    auth_fuzz = fuzz.token_set_ratio(auth, author)
                    if book_fuzz > 98 and auth_fuzz > 80:
                        return desc
                except Exception:
                    pass
    return ''


def get_book_pubdate(bookid, refresh=False):
    """ Book publication date lookup was a Goodreads-specific feature
        that is no longer available since Goodreads API has been deprecated """
    return "0000", False


def thingLang(isbn):
    # try searching librarything for a language code using the isbn
    # if no language found, librarything return value is "invalid" or "unknown"
    # librarything returns plain text, not xml
    BOOK_URL = 'http://www.librarything.com/api/thingLang.php?isbn=' + isbn
    proxies = proxyList()
    booklang = ''
    try:
        librarything_wait()
        timeout = check_int(bookbagofholding.CONFIG['HTTP_TIMEOUT'], 30)
        r = requests.get(BOOK_URL, timeout=timeout, proxies=proxies)
        resp = r.text
        logger.debug("LibraryThing reports language [%s] for %s" % (resp, isbn))
        if 'invalid' not in resp and 'unknown' not in resp and '<' not in resp:
            booklang = resp
    except Exception as e:
        logger.error("%s finding language: %s" % (type(e).__name__, str(e)))
    finally:
        return booklang


def isbn_from_words(words):
    """ Use Google to get an ISBN for a book from words in title and authors name.
        Store the results in the database """
    myDB = database.DBConnection()
    res = myDB.match("SELECT ISBN from isbn WHERE Words=?", (words,))
    if res:
        logger.debug('Found cached ISBN for %s' % words)
        return res['ISBN']

    baseurl = "http://www.google.com/search?q=ISBN+"
    search_url = baseurl + quote(words.replace(' ', '+'))

    headers = {'User-Agent': 'w3m/0.5.3',
               'Content-Type': 'text/plain; charset="UTF-8"',
               'Content-Transfer-Encoding': 'Quoted-Printable',
               }
    content, success = fetchURL(search_url, headers=headers)
    # noinspection Annotator
    RE_ISBN13 = re.compile(r'97[89]{1}(?:-?\d){10,16}|97[89]{1}[- 0-9]{10,16}')
    RE_ISBN10 = re.compile(r'ISBN\x20(?=.{13}$)\d{1,5}([- ])\d{1,7}\1\d{1,6}\1(\d|X)$|[- 0-9X]{10,16}')

    # take the first valid looking answer
    res = RE_ISBN13.findall(content)
    logger.debug('Found %s ISBN13 for %s' % (len(res), words))
    for item in res:
        if len(item) > 13:
            item = item.replace('-', '').replace(' ', '')
        if len(item) == 13:
            myDB.action("INSERT into isbn (Words, ISBN) VALUES (?, ?)", (words, item))
            return item

    res = RE_ISBN10.findall(content)
    logger.debug('Found %s ISBN10 for %s' % (len(res), words))
    for item in res:
        if len(item) > 10:
            item = item.replace('-', '').replace(' ', '')
        if len(item) == 10:
            myDB.action("INSERT into isbn (Words, ISBN) VALUES (?, ?)", (words, item))
            return item

    logger.debug('No valid ISBN found for %s' % words)
    return None
