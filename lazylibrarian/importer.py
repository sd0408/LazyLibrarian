#  This file is part of Lazylibrarian.
#  Lazylibrarian is free software':'you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  Lazylibrarian is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with Lazylibrarian.  If not, see <http://www.gnu.org/licenses/>.

import threading
import traceback
from operator import itemgetter

import lazylibrarian
from lazylibrarian import logger, database
from lazylibrarian.images import getAuthorImage
from lazylibrarian.cache import cache_img
from lazylibrarian.formatter import today, unaccented, formatAuthorName, makeUnicode
from lazylibrarian.gb import GoogleBooks
from fuzzywuzzy import fuzz
import queue


def addAuthorNameToDB(author=None, refresh=False, addbooks=True):
    # get authors name in a consistent format, look them up in the database
    # if not in database, try to import them.
    # return authorname,authorid,new where new=False if author already in db, new=True if added
    # authorname returned is our preferred name, or empty string if not found or unable to add

    new = False
    if not author or len(author) < 2:
        logger.debug('Invalid Author Name [%s]' % author)
        return "", "", False

    author = formatAuthorName(author)
    myDB = database.DBConnection()

    # Check if the author exists, and import the author if not,
    check_exist_author = myDB.match('SELECT AuthorID FROM authors where AuthorName=?', (author,))

    # If no exact match, look for a close fuzzy match to handle misspellings, accents
    if not check_exist_author:
        match_name = author.lower()
        res = myDB.action('select AuthorID,AuthorName from authors')
        for item in res:
            aname = item['AuthorName']
            if aname:
                match_fuzz = fuzz.ratio(aname.lower(), match_name)
                if match_fuzz >= 95:
                    logger.debug("Fuzzy match [%s] %s%% for [%s]" % (item['AuthorName'], match_fuzz, author))
                    check_exist_author = item
                    author = item['AuthorName']
                    break

    if not check_exist_author and lazylibrarian.CONFIG['ADD_AUTHOR']:
        logger.debug('Author %s not found in database, trying to add' % author)
        # no match for supplied author, but we're allowed to add new ones
        # To save loading hundreds of books by unknown authors, ignore unknown
        if author != "Unknown":
            logger.info("Adding new author [%s]" % author)
            try:
                addAuthorToDB(authorname=author, refresh=refresh, addbooks=addbooks)
                check_exist_author = myDB.match('SELECT AuthorID FROM authors where AuthorName=?', (author,))
                if check_exist_author:
                    new = True
            except Exception as e:
                logger.error('Failed to add author [%s] to db: %s %s' % (author, type(e).__name__, str(e)))

    # check author exists in db, either newly loaded or already there
    if not check_exist_author:
        logger.debug("Failed to match author [%s] in database" % author)
        return "", "", False
    author = makeUnicode(author)
    return author, check_exist_author['AuthorID'], new


def addAuthorToDB(authorname=None, refresh=False, authorid=None, addbooks=True):
    """
    Add an author to the database by name or id, and optionally get a list of all their books
    If author already exists in database, refresh their details and optionally booklist
    Uses GoogleBooks API for book data.
    """
    threadname = threading.currentThread().name
    if "Thread-" in threadname:
        threading.currentThread().name = "AddAuthorToDB"
    # noinspection PyBroadException
    try:
        from lazylibrarian.formatter import md5_utf8
        myDB = database.DBConnection()
        authorimg = 'images/nophoto.png'
        new_author = not refresh
        entry_status = ''

        # If authorid provided without authorname, look up author by id first
        dbauthor = None
        if authorid:
            dbauthor = myDB.match("SELECT * from authors WHERE AuthorID=?", (authorid,))
            if dbauthor and not authorname:
                authorname = dbauthor['AuthorName']

        # Ensure authorname is valid before proceeding
        if not authorname:
            logger.error("addAuthorToDB called without authorname or valid authorid")
            return

        authorname = ' '.join(authorname.split())  # ensure no extra whitespace

        # Check if author already exists by name (if we didn't already find by id)
        if not dbauthor:
            dbauthor = myDB.match("SELECT * from authors WHERE AuthorName=?", (authorname,))

        if dbauthor:
            entry_status = dbauthor['Status']
            authorid = dbauthor['AuthorID']
            logger.debug("Updating author %s" % authorname)
            new_author = False
        else:
            # Generate a new author ID based on author name
            authorid = "GB:" + md5_utf8(authorname)
            logger.debug("Adding new author: %s to database" % authorname)
            entry_status = lazylibrarian.CONFIG['NEWAUTHOR_STATUS']
            new_author = True

        controlValueDict = {"AuthorID": authorid}
        newValueDict = {
            "AuthorName": authorname,
            "Status": "Loading",
            "DateAdded": today()
        }
        if new_author:
            newValueDict["AuthorImg"] = authorimg
        myDB.upsert("authors", newValueDict, controlValueDict)

        # Try to get an author image
        if new_author or refresh:
            match = myDB.match("SELECT Manual from authors WHERE AuthorID=?", (authorid,))
            if not match or not match['Manual']:
                newimg = getAuthorImage(authorid)
                if newimg:
                    authorimg = newimg
                    # cache the image
                    if authorimg.startswith('http'):
                        cached, success, _ = cache_img("author", authorid, authorimg, refresh=refresh)
                        if success:
                            authorimg = cached
                    controlValueDict = {"AuthorID": authorid}
                    newValueDict = {"AuthorImg": authorimg}
                    myDB.upsert("authors", newValueDict, controlValueDict)

        if addbooks:
            if new_author:
                bookstatus = lazylibrarian.CONFIG['NEWAUTHOR_STATUS']
                audiostatus = lazylibrarian.CONFIG['NEWAUTHOR_AUDIO']
            else:
                bookstatus = lazylibrarian.CONFIG['NEWBOOK_STATUS']
                audiostatus = lazylibrarian.CONFIG['NEWAUDIO_STATUS']

            if entry_status not in ['Active', 'Wanted', 'Ignored', 'Paused']:
                entry_status = 'Active'  # default for invalid/unknown or "loading"

            # process books using GoogleBooks
            if lazylibrarian.CONFIG['GB_API']:
                book_api = GoogleBooks()
                book_api.get_author_books(authorid, authorname, bookstatus=bookstatus,
                                          audiostatus=audiostatus, entrystatus=entry_status,
                                          refresh=refresh)

            update_totals(authorid)
        else:
            # if we're not loading any books, mark author as ignored
            entry_status = 'Ignored'

        controlValueDict = {"AuthorID": authorid}
        newValueDict = {"Status": entry_status}
        myDB.upsert("authors", newValueDict, controlValueDict)

        msg = "[%s] Author update complete, status %s" % (authorname, entry_status)
        logger.info(msg)
        return msg
    except Exception:
        msg = 'Unhandled exception in addAuthorToDB: %s' % traceback.format_exc()
        logger.error(msg)
        return msg


def update_totals(AuthorID):
    myDB = database.DBConnection()
    # author totals needs to be updated every time a book is marked differently
    match = myDB.select('SELECT AuthorID from authors WHERE AuthorID=?', (AuthorID,))
    if not match:
        logger.debug('Update_totals - authorid [%s] not found' % AuthorID)
        return

    cmd = 'SELECT BookName, BookLink, BookDate, BookID from books WHERE AuthorID=?'
    cmd += ' AND Status != "Ignored" order by BookDate DESC'
    lastbook = myDB.match(cmd, (AuthorID,))

    cmd = "select sum(case status when 'Ignored' then 0 else 1 end) as unignored,"
    cmd += "sum(case when status == 'Have' then 1 when status == 'Open' then 1 "
    cmd += "when audiostatus == 'Have' then 1 when audiostatus == 'Open' then 1 "
    cmd += "else 0 end) as have, count(*) as total from books where authorid=?"
    totals = myDB.match(cmd, (AuthorID,))

    controlValueDict = {"AuthorID": AuthorID}
    newValueDict = {
        "TotalBooks": totals['total'],
        "UnignoredBooks": totals['unignored'],
        "HaveBooks": totals['have'],
        "LastBook": lastbook['BookName'] if lastbook else None,
        "LastLink": lastbook['BookLink'] if lastbook else None,
        "LastBookID": lastbook['BookID'] if lastbook else None,
        "LastDate": lastbook['BookDate'] if lastbook else None
    }
    myDB.upsert("authors", newValueDict, controlValueDict)

    cmd = "select series.seriesid as Series,sum(case books.status when 'Ignored' then 0 else 1 end) as Total,"
    cmd += "sum(case when books.status == 'Have' then 1 when books.status == 'Open' then 1"
    cmd += " when books.audiostatus == 'Have' then 1 when books.audiostatus == 'Open' then 1"
    cmd += " else 0 end) as Have from books,member,series,seriesauthors where member.bookid=books.bookid"
    cmd += " and member.seriesid = series.seriesid and seriesauthors.seriesid = series.seriesid"
    cmd += " and seriesauthors.authorid=? group by series.seriesid"
    res = myDB.select(cmd, (AuthorID,))
    if len(res):
        for series in res:
            myDB.action('UPDATE series SET Have=?, Total=? WHERE SeriesID=?',
                        (series['Have'], series['Total'], series['Series']))

    res = myDB.match('SELECT AuthorName from authors WHERE AuthorID=?', (AuthorID,))
    logger.debug('Updated totals for [%s]' % res['AuthorName'])


def import_book(bookid, ebook=None, audio=None, wait=False):
    """ search GoogleBooks for a bookid and import the book
        ebook/audio=None makes find_book use configured default """
    GB = GoogleBooks(bookid)
    if not wait:
        _ = threading.Thread(target=GB.find_book, name='GB-IMPORT', args=[bookid, ebook, audio]).start()
    else:
        GB.find_book(bookid, ebook, audio)


def search_for(searchterm):
    """ search GoogleBooks for a searchterm, return a list of results
    """
    GB = GoogleBooks(searchterm)
    myqueue = queue.Queue()
    search_api = threading.Thread(target=GB.find_results, name='GB-RESULTS', args=[searchterm, myqueue])
    search_api.start()
    search_api.join()
    searchresults = myqueue.get()
    sortedlist = sorted(searchresults, key=itemgetter('highest_fuzz', 'num_reviews'), reverse=True)
    return sortedlist
