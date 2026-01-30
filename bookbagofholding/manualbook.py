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


import bookbagofholding
from bookbagofholding import logger, database
from bookbagofholding.formatter import getList, unaccented_str, plural
from bookbagofholding.providers import IterateOverRSSSites, IterateOverTorrentSites, IterateOverNewzNabSites, \
    IterateOverDirectSites
from fuzzywuzzy import fuzz
from urllib.parse import quote_plus


def searchItem(item=None, bookid=None, cat=None, min_score=40):
    """
    Call all active search providers to search for item
    return a list of results, each entry in list containing percentage_match, title, provider, size, url
    item = searchterm to use for general search
    bookid = link to data for book/audio searches
    cat = category to search [general, book, audio]
    min_score = minimum fuzzy match score to include result (default 40, use 0 for interactive search)
    """
    results = []

    if not item:
        return results

    book = {}
    searchterm = unaccented_str(item)

    book['searchterm'] = searchterm
    if bookid:
        book['bookid'] = bookid
    else:
        book['bookid'] = searchterm

    if cat in ['book', 'audio']:
        myDB = database.DBConnection()
        cmd = 'SELECT authorName,bookName,bookSub from books,authors WHERE books.AuthorID=authors.AuthorID'
        cmd += ' and bookID=?'
        match = myDB.match(cmd, (bookid,))
        if match:
            book['authorName'] = match['authorName']
            book['bookName'] = match['bookName']
            book['bookSub'] = match['bookSub']
        else:
            logger.debug('Forcing general search')
            cat = 'general'

    nprov = bookbagofholding.USE_NZB() + bookbagofholding.USE_TOR() + bookbagofholding.USE_RSS() + bookbagofholding.USE_DIRECT()
    logger.debug('Searching %s provider%s (%s) for %s' % (nprov, plural(nprov), cat, searchterm))

    if bookbagofholding.USE_NZB():
        resultlist, nprov = IterateOverNewzNabSites(book, cat)
        if nprov:
            results += resultlist
    if bookbagofholding.USE_TOR():
        resultlist, nprov = IterateOverTorrentSites(book, cat)
        if nprov:
            results += resultlist
    if bookbagofholding.USE_DIRECT():
        resultlist, nprov = IterateOverDirectSites(book, cat)
        if nprov:
            results += resultlist
    if bookbagofholding.USE_RSS():
        resultlist, nprov, dltypes = IterateOverRSSSites()
        if nprov and dltypes != 'M':
            results += resultlist

    # reprocess to get consistent results
    searchresults = []
    for item in results:
        provider = ''
        title = ''
        url = ''
        size = ''
        date = ''
        mode = ''
        if 'dispname' in item:
            provider = item['dispname']
        elif 'nzbprov' in item:
            provider = item['nzbprov']
        elif 'tor_prov' in item:
            provider = item['tor_prov']
        elif 'rss_prov' in item:
            provider = item['rss_prov']
        if 'nzbtitle' in item:
            title = item['nzbtitle']
        if 'nzburl' in item:
            url = item['nzburl']
        if 'nzbsize' in item:
            size = item['nzbsize']
        if 'nzbdate' in item:
            date = item['nzbdate']
        if 'nzbmode' in item:
            mode = item['nzbmode']
        if 'tor_title' in item:
            title = item['tor_title']
        if 'tor_url' in item:
            url = item['tor_url']
        if 'tor_size' in item:
            size = item['tor_size']
        if 'tor_date' in item:
            date = item['tor_date']
        if 'tor_type' in item:
            mode = item['tor_type']

        if title and provider and mode and url:
            # Not all results have a date or a size
            if not date:
                date = 'Fri, 01 Jan 1970 00:00:00 +0100'
            if not size:
                size = '1000'

            if mode == 'torznab':
                if url.startswith('magnet'):
                    mode = 'magnet'

            # calculate match percentage - torrents might have words_with_underscore_separator
            score = fuzz.token_set_ratio(searchterm, title.replace('_', ' '))
            # lose a point for each extra word in the title so we get the closest match
            words = len(getList(searchterm))
            words -= len(getList(title))
            score -= abs(words)
            if score >= min_score:  # ignore wildly wrong results (min_score=0 for interactive search)
                result = {'score': score, 'title': title, 'provider': provider, 'size': size, 'date': date,
                          'url': quote_plus(url), 'mode': mode}

                searchresults.append(result)

    logger.debug('Found %s %s results for %s' % (len(searchresults), cat, searchterm))
    return searchresults
