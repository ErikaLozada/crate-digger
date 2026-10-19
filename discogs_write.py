"""Changes to the user's Discogs account: Buy adds to the collection, Wishlist to the wantlist, and both can be undone.
After a successful call the local export (data/collection.csv, data/wantlist.csv) is updated to match.
CD_DISCOGS_DRY=1: no network and no file changes; calls return made-up ids. Workers and tests must use it."""
import csv, json, os, random, sys, time, urllib.error, urllib.request

DRY = os.environ.get('CD_DISCOGS_DRY') == '1'
UA = 'CrateDiggerPrototype/0.1 (personal collection)'
API = 'https://api.discogs.com'
COLLECTION_CSV = 'data/collection.csv'
WANTLIST_CSV = 'data/wantlist.csv'
_username = None

class DiscogsError(Exception):
    """A Discogs call failed; the message is safe to show on the card."""

def _token():
    return open('discogs_token.txt').read().strip() if os.path.exists('discogs_token.txt') else os.environ.get('DISCOGS_TOKEN', '')

def _call(method, path, body=None):
    token = _token()
    if not token: raise DiscogsError('No Discogs token configured')
    h = {'User-Agent': UA, 'Authorization': 'Discogs token=' + token}
    if body is not None: h['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(), headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        msg = {401: 'Discogs rejected the token', 403: 'Discogs refused this change', 404: 'Discogs does not have that record',
               429: 'Discogs rate limit, try again in a minute'}.get(e.code, 'Discogs error %s' % e.code)
        raise DiscogsError(msg) from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise DiscogsError('Could not reach Discogs') from None
    try: return json.loads(raw) if raw else {}
    except ValueError: raise DiscogsError('Discogs sent an unreadable answer') from None

def _user():
    global _username
    if not _username:
        _username = _call('GET', '/oauth/identity').get('username')
        if not _username: raise DiscogsError('Could not find the Discogs username')
    return _username

def _release(rid):
    """Fields for the export row; just the id if Discogs can't be read, which is enough for Refresh to fetch the rest."""
    try: return _call('GET', '/releases/%s' % int(rid))
    except DiscogsError: return {'id': int(rid)}

def _format(r):
    parts = []
    for f in r.get('formats') or []:
        name = f.get('name', '')
        if str(f.get('qty', '1')) not in ('', '1'): name = '%sx%s' % (f['qty'], name)
        parts += [name] + (f.get('descriptions') or [])
    return ', '.join(p for p in parts if p)

def _row(r, header, extra):
    labels = r.get('labels') or []
    vals = {'Catalog#': next((l['catno'] for l in labels if l.get('catno')), ''),
            'Artist': ', '.join(a.get('name', '') for a in r.get('artists') or []) or r.get('artists_sort', ''),
            'Title': r.get('title', ''), 'Label': ', '.join(dict.fromkeys(l.get('name', '') for l in labels)),
            'Format': _format(r), 'Released': r.get('year') or '', 'release_id': r.get('id', '')}
    vals.update(extra)
    return [str(vals.get(c, '')) for c in header]

def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S')

def _read(path):
    with open(path, newline='', encoding='utf-8') as f: return list(csv.reader(f))

def _write(path, rows):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as f: csv.writer(f).writerows(rows)
    os.replace(tmp, path)

def _add_row(path, r, extra, tail=()):
    rows = _read(path)
    rows.append(_row(r, rows[0], extra) + list(tail))
    _write(path, rows)

def _drop_rows(path, rid, only_last=False):
    rows = _read(path); i = rows[0].index('release_id')
    hit = [n for n, row in enumerate(rows) if n and len(row) > i and row[i] == str(rid)]
    if only_last: hit = hit[-1:]
    if hit: _write(path, [row for n, row in enumerate(rows) if n not in hit])

def _local(fn, *a):
    """Updates the local export after Discogs has already changed; Discogs is the source of truth, so a failure here
    is logged and the next export fixes the CSV."""
    try: fn(*a)
    except (OSError, csv.Error, ValueError, IndexError) as e:
        print('Discogs was updated, but the local CSV could not be changed: %s' % e, file=sys.stderr)

def buy(rid):
    """Adds release rid to collection folder 1 (Uncategorized). Returns {'folder_id': 1, 'instance_id': int}."""
    if DRY: return {'folder_id': 1, 'instance_id': random.randint(10**8, 10**9)}
    d = _call('POST', '/users/%s/collection/folders/1/releases/%s' % (_user(), int(rid)))
    if not d.get('instance_id'): raise DiscogsError('Discogs did not confirm the purchase')
    _local(_add_row, COLLECTION_CSV, _release(rid), {'CollectionFolder': 'Uncategorized', 'Date Added': _now()})
    return {'folder_id': 1, 'instance_id': d['instance_id']}

def unbuy(rid, folder_id, instance_id):
    """Removes that collection instance again."""
    if DRY: return
    _call('DELETE', '/users/%s/collection/folders/%s/releases/%s/instances/%s' % (_user(), int(folder_id), int(rid), int(instance_id)))
    _local(_drop_rows, COLLECTION_CSV, rid, True)

def want(rid):
    """Adds release rid to the wantlist. Returns {}."""
    if DRY: return {}
    _call('PUT', '/users/%s/wants/%s' % (_user(), int(rid)))
    _local(_add_row, WANTLIST_CSV, _release(rid), {}, [_now()])
    return {}

def unwant(rid):
    """Removes release rid from the wantlist."""
    if DRY: return
    _call('DELETE', '/users/%s/wants/%s' % (_user(), int(rid)))
    _local(_drop_rows, WANTLIST_CSV, rid)
