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

import string
import re
import json
import time
import cherrypy
import bookbagofholding
from bookbagofholding import logger, database
from bookbagofholding.formatter import unaccented, getList
from bookbagofholding.importer import addAuthorNameToDB, search_for, import_book
from bookbagofholding.librarysync import find_book_in_db
from fuzzywuzzy import fuzz
from bookbagofholding.common import runScript

# calibredb custom_columns
# calibredb add_custom_column label name bool
# calibredb remove_custom_column --force label
# calibredb set_custom label id value
# calibredb search "#label":"false"  # returns list of ids (slow)


def calibreList(col_read, col_toread):
    """ Get a list from calibre of all books in its library, including optional 'read' and 'toread' columns
        If success, return list of dicts {"title": "", "id": 0, "authors": ""}
        The "read" and "toread" columns are passed as column names so they can be per-user and may not be present.
        Can be true, false, or empty in which case not included in dict. We only use the "true" state
        If error, return error message (not a dict) """

    fieldlist = 'title,authors'
    if col_read:
        fieldlist += ',*' + col_read
    if col_toread:
        fieldlist += ',*' + col_toread
    res, err, rc = calibredb("list", "", ['--for-machine', '--fields', fieldlist])
    if rc:
        if res:
            return res
        return err
    else:
        return json.loads(res)


def syncCalibreList(col_read=None, col_toread=None, userid=None):
    """ Get the bookbagofholding bookid for each read/toread calibre book so we can map our id to theirs,
        and sync current/supplied user's read/toread or supplied read/toread columns to calibre database.
        Return message giving totals """

    myDB = database.DBConnection()
    username = ''
    readlist = []
    toreadlist = []
    if not userid:
        cookie = cherrypy.request.cookie
        if cookie and 'll_uid' in list(cookie.keys()):
            userid = cookie['ll_uid'].value
    if userid:
        res = myDB.match('SELECT UserName,ToRead,HaveRead,CalibreRead,CalibreToRead,Perms from users where UserID=?',
                         (userid,))
        if res:
            username = res['UserName']
            if not col_read:
                col_read = res['CalibreRead']
            if not col_toread:
                col_toread = res['CalibreToRead']
            toreadlist = getList(res['ToRead'])
            readlist = getList(res['HaveRead'])
            # suppress duplicates (just in case)
            toreadlist = list(set(toreadlist))
            readlist = list(set(readlist))
        else:
            return "Error: Unable to get user column settings for %s" % userid

    if not userid:
        return "Error: Unable to find current userid"

    if not col_read and not col_toread:
        return "User %s has no calibre columns set" % username

    # check user columns exist in calibre and create if not
    res = calibredb('custom_columns')
    columns = res[0].split('\n')
    custom_columns = []
    for column in columns:
        if column:
            custom_columns.append(column.split(' (')[0])

    if col_read not in custom_columns:
        added = calibredb('add_custom_column', [col_read, col_read, 'bool'])
        if "column created" not in added[0]:
            return added
    if col_toread not in custom_columns:
        added = calibredb('add_custom_column', [col_toread, col_toread, 'bool'])
        if "column created" not in added[0]:
            return added

    nomatch = 0
    readcol = ''
    toreadcol = ''
    map_ctol = {}
    map_ltoc = {}
    if col_read:
        readcol = '*' + col_read
    if col_toread:
        toreadcol = '*' + col_toread

    calibre_list = calibreList(col_read, col_toread)
    if not isinstance(calibre_list, list):
        # got an error message from calibredb
        return '"%s"' % calibre_list

    for item in calibre_list:
        if toreadcol and toreadcol in item or readcol and readcol in item:
            authorname, authorid, added = addAuthorNameToDB(item['authors'], refresh=False, addbooks=False)
            if authorname:
                if authorname != item['authors']:
                    logger.debug("Changed authorname for [%s] from [%s] to [%s]" %
                                 (item['title'], item['authors'], authorname))
                    item['authors'] = authorname
                bookid, mtype = find_book_in_db(authorname, item['title'], ignored=False, library='eBook')
                if bookid and mtype == "Ignored":
                    logger.warn("Book %s by %s is marked Ignored in database, importing anyway" %
                                (item['title'], authorname))
                if not bookid:
                    searchterm = "%s <ll> %s" % (item['title'], authorname)
                    results = search_for(unaccented(searchterm))
                    if results:
                        result = results[0]
                        if result['author_fuzz'] > bookbagofholding.CONFIG['MATCH_RATIO'] \
                                and result['book_fuzz'] > bookbagofholding.CONFIG['MATCH_RATIO']:
                            logger.debug("Found (%s%% %s%%) %s: %s" % (result['author_fuzz'], result['book_fuzz'],
                                                                       result['authorname'], result['bookname']))
                            bookid = result['bookid']
                            import_book(bookid)
                if bookid:
                    # NOTE: calibre bookid is always an integer, bookbagofholding bookid is a string
                    # (goodreads could be used as an int, but googlebooks can't as it's alphanumeric)
                    # so convert all dict items to strings for ease of matching.
                    map_ctol[str(item['id'])] = str(bookid)
                    map_ltoc[str(bookid)] = str(item['id'])
                else:
                    logger.warn('Calibre Book [%s] by [%s] is not in bookbagofholding database' %
                                (item['title'], authorname))
                    nomatch += 1
            else:
                logger.warn('Calibre Author [%s] not matched in bookbagofholding database' % (item['authors']))
                nomatch += 1

    # Now check current users bookbagofholding read/toread against the calibre library, warn about missing ones
    # which might be books calibre doesn't have, or might be minor differences in author or title

    for idlist in [("Read", readlist), ("To_Read", toreadlist)]:
        booklist = idlist[1]
        for bookid in booklist:
            cmd = "SELECT AuthorID,BookName from books where BookID=?"
            book = myDB.match(cmd, (bookid,))
            if not book:
                logger.error('Error finding bookid %s' % bookid)
            else:
                cmd = "SELECT AuthorName from authors where AuthorID=?"
                author = myDB.match(cmd, (book['AuthorID'],))
                if not author:
                    logger.error('Error finding authorid %s' % book['AuthorID'])
                else:
                    match = False
                    high = 0
                    highname = ''
                    for item in calibre_list:
                        if item['authors'] == author['AuthorName'] and item['title'] == book['BookName']:
                            logger.debug("Exact match for %s [%s]" % (idlist[0], book['BookName']))
                            map_ctol[str(item['id'])] = str(bookid)
                            map_ltoc[str(bookid)] = str(item['id'])
                            match = True
                            break
                    if not match:
                        highid = ''
                        for item in calibre_list:
                            if item['authors'] == author['AuthorName']:
                                n = fuzz.token_sort_ratio(item['title'], book['BookName'])
                                if n > high:
                                    high = n
                                    highname = item['title']
                                    highid = item['id']

                        if high > 95:
                            logger.debug("Found ratio match %s%% [%s] for %s [%s]" %
                                         (high, highname, idlist[0], book['BookName']))
                            map_ctol[str(highid)] = str(bookid)
                            map_ltoc[str(bookid)] = str(highid)
                            match = True

                    if not match:
                        logger.warn("No match for %s %s by %s in calibre database, closest match %s%% [%s]" %
                                    (idlist[0], book['BookName'], author['AuthorName'], high, highname))
                        nomatch += 1

    logger.debug("BookID mapping complete, %s match %s, nomatch %s" % (username, len(map_ctol), nomatch))

    # now sync the lists
    if not userid:
        msg = "No userid found"
    else:
        last_read = []
        last_toread = []
        calibre_read = []
        calibre_toread = []

        cmd = 'select SyncList from sync where UserID=? and Label=?'
        res = myDB.match(cmd, (userid, col_read))
        if res:
            last_read = getList(res['SyncList'])
        res = myDB.match(cmd, (userid, col_toread))
        if res:
            last_toread = getList(res['SyncList'])

        for item in calibre_list:
            if toreadcol and toreadcol in item and item[toreadcol]:  # only if True
                if str(item['id']) in map_ctol:
                    calibre_toread.append(map_ctol[str(item['id'])])
                else:
                    logger.warn("Calibre to_read book %s:%s has no bookbagofholding bookid" %
                                (item['authors'], item['title']))
            if readcol and readcol in item and item[readcol]:  # only if True
                if str(item['id']) in map_ctol:
                    calibre_read.append(map_ctol[str(item['id'])])
                else:
                    logger.warn("Calibre read book %s:%s has no bookbagofholding bookid" %
                                (item['authors'], item['title']))

        logger.debug("Found %s calibre read, %s calibre toread" % (len(calibre_read), len(calibre_toread)))
        logger.debug("Found %s lazylib read, %s lazylib toread" % (len(readlist), len(toreadlist)))

        added_to_ll_toread = list(set(toreadlist) - set(last_toread))
        removed_from_ll_toread = list(set(last_toread) - set(toreadlist))
        added_to_ll_read = list(set(readlist) - set(last_read))
        removed_from_ll_read = list(set(last_read) - set(readlist))
        logger.debug("bookbagofholding changes to copy to calibre: %s %s %s %s" % (len(added_to_ll_toread),
                     len(removed_from_ll_toread), len(added_to_ll_read), len(removed_from_ll_read)))

        added_to_calibre_toread = list(set(calibre_toread) - set(last_toread))
        removed_from_calibre_toread = list(set(last_toread) - set(calibre_toread))
        added_to_calibre_read = list(set(calibre_read) - set(last_read))
        removed_from_calibre_read = list(set(last_read) - set(calibre_read))
        logger.debug("calibre changes to copy to bookbagofholding: %s %s %s %s" % (len(added_to_calibre_toread),
                     len(removed_from_calibre_toread), len(added_to_calibre_read), len(removed_from_calibre_read)))

        calibre_changes = 0
        for item in added_to_calibre_read:
            if item not in readlist:
                readlist.append(item)
                logger.debug("Bookbag of Holding marked %s as read" % item)
                calibre_changes += 1
        for item in added_to_calibre_toread:
            if item not in toreadlist:
                toreadlist.append(item)
                logger.debug("Bookbag of Holding marked %s as to_read" % item)
                calibre_changes += 1
        for item in removed_from_calibre_read:
            if item in readlist:
                readlist.remove(item)
                logger.debug("Bookbag of Holding removed %s from read" % item)
                calibre_changes += 1
        for item in removed_from_calibre_toread:
            if item in toreadlist:
                toreadlist.remove(item)
                logger.debug("Bookbag of Holding removed %s from to_read" % item)
                calibre_changes += 1
        if calibre_changes:
            myDB.action('UPDATE users SET ToRead=?,HaveRead=? WHERE UserID=?',
                        (', '.join(toreadlist), ', '.join(readlist), userid))
        ll_changes = 0
        for item in added_to_ll_toread:
            if item in map_ltoc:
                res, err, rc = calibredb('set_custom', [col_toread, map_ltoc[item], 'true'], [])
                if rc:
                    msg = "calibredb set_custom error: "
                    if err:
                        logger.error(msg + err)
                    elif res:
                        logger.error(msg + res)
                    else:
                        logger.error(msg + str(rc))
                else:
                    ll_changes += 1
            else:
                logger.warn("Unable to set calibre %s true for %s" % (col_toread, item))
        for item in removed_from_ll_toread:
            if item in map_ltoc:
                res, err, rc = calibredb('set_custom', [col_toread, map_ltoc[item], ''], [])
                if rc:
                    msg = "calibredb set_custom error: "
                    if err:
                        logger.error(msg + err)
                    elif res:
                        logger.error(msg + res)
                    else:
                        logger.error(msg + str(rc))
                else:
                    ll_changes += 1
            else:
                logger.warn("Unable to clear calibre %s for %s" % (col_toread, item))

        for item in added_to_ll_read:
            if item in map_ltoc:
                res, err, rc = calibredb('set_custom', [col_read, map_ltoc[item], 'true'], [])
                if rc:
                    msg = "calibredb set_custom error: "
                    if err:
                        logger.error(msg + err)
                    elif res:
                        logger.error(msg + res)
                    else:
                        logger.error(msg + str(rc))
                else:
                    ll_changes += 1
            else:
                logger.warn("Unable to set calibre %s true for %s" % (col_read, item))

        for item in removed_from_ll_read:
            if item in map_ltoc:
                res, err, rc = calibredb('set_custom', [col_read, map_ltoc[item], ''], [])
                if rc:
                    msg = "calibredb set_custom error: "
                    if err:
                        logger.error(msg + err)
                    elif res:
                        logger.error(msg + res)
                    else:
                        logger.error(msg + str(rc))
                else:
                    ll_changes += 1
            else:
                logger.warn("Unable to clear calibre %s for %s" % (col_read, item))

        # store current sync list as comparison for next sync
        controlValueDict = {"UserID": userid, "Label": col_read}
        newValueDict = {"Date": str(time.time()), "Synclist": ', '.join(readlist)}
        myDB.upsert("sync", newValueDict, controlValueDict)
        controlValueDict = {"UserID": userid, "Label": col_toread}
        newValueDict = {"Date": str(time.time()), "Synclist": ', '.join(toreadlist)}
        myDB.upsert("sync", newValueDict, controlValueDict)

        msg = "%s sync updated: %s calibre, %s bookbagofholding" % (username, ll_changes, calibre_changes)
    return msg


def calibreTest():
    # First check if calibredb is configured
    if not bookbagofholding.CONFIG['IMP_CALIBREDB']:
        return "calibredb not configured. Set 'Calibredb import program' in config."

    # Determine library path for display
    if bookbagofholding.CONFIG['CALIBRE_USE_SERVER']:
        lib_path = bookbagofholding.CONFIG['CALIBRE_SERVER']
    else:
        lib_path = bookbagofholding.CONFIG['CALIBRE_LIBRARY'] or bookbagofholding.DIRECTORY('eBook')

    logger.debug('Testing calibredb: %s with library: %s' % (bookbagofholding.CONFIG['IMP_CALIBREDB'], lib_path))

    res, err, rc = calibredb('--version')
    if rc:
        msg = "calibredb communication failed: "
        if err:
            return msg + err
        if res:
            return msg + res
        return msg + "Return code %s" % rc

    res = res.strip('\n')
    if '(calibre ' in res and res.endswith(')'):
        # extract calibredb version number
        res = res.split('(calibre ')[1]
        vernum = res[:-1]
        res = 'calibredb ok, version ' + vernum
        res = res + '\nLibrary: ' + lib_path
        # get a list of categories and counters from the database
        cats, lib_url, rc = calibredb('list_categories', ['-i'])
        cnt = 0
        if rc:
            res = res + '\nDatabase READ Failed (rc=%s)' % rc
            if cats:
                res = res + ': ' + cats[:100]
        elif not len(cats):
            res = res + '\nDatabase READ Failed (empty response)'
        else:
            for entry in cats.split('\n'):
                # Skip warning messages and empty lines
                if not entry.strip() or 'No write access' in entry or entry.startswith('category'):
                    continue
                words = entry.split()
                if not words:
                    continue
                # Calibre <7.0 uses "ITEMS", Calibre 7.0+ uses "count"
                if 'ITEMS' in words:
                    idx = words.index('ITEMS') + 1
                    if idx < len(words) and words[idx].isdigit():
                        cnt += int(words[idx])
                # For Calibre 7.0+ format: category tag_name count rating
                # Data rows look like: authors "Author Name" 5 0
                # The count is typically the 3rd or 2nd-to-last numeric column
                elif len(words) >= 3:
                    # Try to find a digit in position 2 (0-indexed) or later
                    for i in range(2, len(words)):
                        # Clean up bytes notation if present (b'value')
                        val = words[i].strip("b'\"")
                        if val.isdigit():
                            cnt += int(val)
                            break
        if cnt:
            res = res + '\nDatabase READ ok (%s items)' % cnt
            wrt, err, rc = calibredb('add', ['--authors', 'Bookbag of Holding', '--title', 'dummy', '--empty'], [])
            if 'Added book ids' not in wrt:
                res = res + '\nDatabase WRITE Failed'
            else:
                calibre_id = wrt.split("book ids: ", 1)[1].split("\n", 1)[0]
                if vernum.startswith('2'):
                    rmv, err, rc = calibredb('remove', [calibre_id], [])
                else:
                    rmv, err, rc = calibredb('remove', ['--permanent', calibre_id], [])
                if not rc:
                    res = res + '\nDatabase WRITE ok'
                else:
                    res = res + '\nDatabase WRITE2 Failed: '
        else:
            # cnt is 0 - either empty database or unexpected output format
            if cats:
                # Show first 200 chars of output to help debug
                res = res + '\nDatabase empty or unexpected format. Response: ' + cats[:200].replace('\n', ' | ')
    else:
        res = 'calibredb Failed'
    return res


def calibreImportBook(filepath, bookid, authorname, bookname):
    """
    Import a single book file into Calibre database.
    Called when manually matching files to books.
    Returns (success, message)
    """
    if not bookbagofholding.CONFIG['IMP_CALIBREDB']:
        return True, 'Calibre not configured, skipping import'

    import os
    if not os.path.isfile(filepath):
        return False, 'File does not exist: %s' % filepath

    logger.debug('Importing %s into calibre for book %s' % (filepath, bookid))

    try:
        # Check if the file is already in Calibre by searching for the book
        # First, try to add the file
        res, err, rc = calibredb('add', ['-1', '-d'], [filepath])

        if rc:
            return False, 'calibredb add failed: %s' % (err or res)

        if 'already exist' in err or 'already exist' in res:
            logger.debug('Book already exists in Calibre library')
            return True, 'Book already in Calibre'

        if 'Added book ids' not in res:
            return False, 'Calibre failed to import: no book ids returned'

        calibre_id = res.split("book ids: ", 1)[1].split("\n", 1)[0]
        logger.debug('Calibre ID: %s' % calibre_id)

        # Set metadata if we have it
        if bookid.isdigit():
            identifier = "goodreads:%s" % bookid
        else:
            identifier = "google:%s" % bookid

        # Set author, title, and identifier
        _, _, rc = calibredb('set_metadata', ['--field', 'authors:%s' % unaccented(authorname)], [calibre_id])
        if rc:
            logger.warn("calibredb unable to set author")

        _, _, rc = calibredb('set_metadata', ['--field', 'title:%s' % unaccented(bookname)], [calibre_id])
        if rc:
            logger.warn("calibredb unable to set title")

        _, _, rc = calibredb('set_metadata', ['--field', 'identifiers:%s' % identifier], [calibre_id])
        if rc:
            logger.warn("calibredb unable to set identifier")

        logger.info('Successfully imported %s into Calibre (ID: %s)' % (bookname, calibre_id))
        return True, 'Imported to Calibre (ID: %s)' % calibre_id

    except Exception as e:
        logger.error('calibreImportBook error: %s' % str(e))
        return False, 'Calibre import failed: %s' % str(e)


def calibredb(cmd=None, prelib=None, postlib=None):
    """ calibre-server needs to be started with --enable-auth and needs user/password to add/remove books
        only basic features are available without auth. calibre_server should look like  http://address:port/#library
        default library is used if no #library in the url
        or calibredb can talk to the database file as long as there is no running calibre """

    if not bookbagofholding.CONFIG['IMP_CALIBREDB']:
        return "No calibredb set in config", '', 1

    params = [bookbagofholding.CONFIG['IMP_CALIBREDB'], cmd]
    if bookbagofholding.CONFIG['CALIBRE_USE_SERVER']:
        dest_url = bookbagofholding.CONFIG['CALIBRE_SERVER']
        if bookbagofholding.CONFIG['CALIBRE_USER'] and bookbagofholding.CONFIG['CALIBRE_PASS']:
            params.extend(['--username', bookbagofholding.CONFIG['CALIBRE_USER'],
                           '--password', bookbagofholding.CONFIG['CALIBRE_PASS']])
    else:
        # Use explicit CALIBRE_LIBRARY if set, otherwise fall back to eBook directory
        dest_url = bookbagofholding.CONFIG['CALIBRE_LIBRARY'] or bookbagofholding.DIRECTORY('eBook')
    if prelib:
        params.extend(prelib)

    if cmd != "--version":
        params.extend(['--with-library', '%s' % dest_url])
    if postlib:
        params.extend(postlib)

    rc, res, err = runScript(params)
    logger.debug("calibredb rc %s" % rc)
    wsp = re.escape(string.whitespace)
    nres = re.sub(r'['+wsp+']', ' ', res)
    nerr = re.sub(r'['+wsp+']', ' ', err)
    logger.debug("calibredb res %d[%s]" % (len(nres), nres))
    logger.debug("calibredb err %d[%s]" % (len(nerr), nerr))

    if rc:
        if 'Errno 111' in err:
            logger.warn("calibredb returned Errno 111: Connection refused")
        elif 'Errno 13' in err:
            logger.warn("calibredb returned Errno 13: Permission denied")
        elif cmd == 'list_categories' and len(res):
            rc = 0  # false error return of 1 on v2.xx calibredb
    if 'already exist' in err:
        dest_url = err

    if rc:
        return res, err, rc
    else:
        return res, dest_url, 0
