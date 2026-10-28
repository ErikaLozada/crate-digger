"""Download complete Discogs account lists into the local CSV caches.
Only GET requests; a failed download leaves the previous cache available."""
import csv, datetime, io, json, math, os, tempfile, time, urllib.parse
import discogs_write as dw

STATUS_PATH = 'data/discogs-sync.json'
COL_HEADER = ['Catalog#', 'Artist', 'Title', 'Label', 'Format', 'Rating', 'Released', 'release_id',
              'CollectionFolder', 'Date Added', 'Collection Media Condition', 'Collection Sleeve Condition', 'Collection Notes']
WANT_HEADER = ['Catalog#', 'Artist', 'Title', 'Label', 'Format', 'Rating', 'Released', 'release_id', 'Notes', 'Date Added']
EXTRA = ['master_id', 'Genres', 'Styles']


def status():
    try:
        with open(STATUS_PATH, encoding='utf-8') as f: d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get('synced_at'), str): return None
        if any(type(d.get(k)) is not int or d[k] < 0 for k in ('collection', 'wantlist')): return None
        return {k: d[k] for k in ('collection', 'wantlist', 'synced_at')}
    except (OSError, ValueError): return None


def _get(path):
    for attempt in range(3):
        try: return dw._call('GET', path)
        except dw.DiscogsError as e:
            if attempt == 2 or e.status not in (None, 429, 500, 502, 503, 504): raise
            try: delay = min(60, max(1, float(e.retry_after)))
            except (ValueError, TypeError): delay = 2 ** (attempt + 1)
            time.sleep(delay)


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum: raise ValueError('invalid integer')
    return value


def _pages(path, key):
    rows, expected = [], None
    for page in range(1, 10001):
        if page > 1: time.sleep(1.1)
        d = _get(path + '?per_page=100&page=%d' % page)
        p = d['pagination']; values = d[key]
        current = (_integer(p['pages']), _integer(p['items']), _integer(p['per_page'], 1))
        pages, items, per_page = current
        if not isinstance(values, list) or _integer(p['page'], 1) != page: raise ValueError('invalid page')
        if pages not in (max(1, math.ceil(items / per_page)), 0 if items == 0 else -1): raise ValueError('invalid page count')
        if expected is not None and current != expected: raise ValueError('list changed during download')
        expected = current
        if len(values) != min(per_page, max(0, items - len(rows))): raise ValueError('incomplete page')
        rows.extend(values)
        if page >= pages:
            if len(rows) != items: raise ValueError('incomplete list')
            return rows
    raise ValueError('too many pages')


def _header(path, default, extra):
    try:
        with open(path, newline='', encoding='utf-8-sig') as f: h = next(csv.reader(f))
        if 'release_id' not in h or len(set(h)) != len(h): raise ValueError('invalid cache header')
    except FileNotFoundError: h = list(default)
    for name in extra:
        if name not in h: h.append(name)
    return h


def _rows(items, header, folders=None):
    out, seen = [header], set()
    for item in items:
        r = item['basic_information']
        rid = _integer(r['id'], 1)
        if not isinstance(r['title'], str) or not isinstance(r['artists'], list): raise ValueError('invalid release')
        extra = {'Rating': item.get('rating', ''), 'Date Added': item.get('date_added', ''),
                 'master_id': r.get('master_id') or '', 'Genres': json.dumps(r.get('genres') or []),
                 'Styles': json.dumps(r.get('styles') or [])}
        identity = rid
        if folders is not None:
            instance = _integer(item['instance_id'], 1); folder = _integer(item['folder_id'], 1)
            if folder not in folders: raise ValueError('unknown collection folder')
            identity = instance
            extra.update(instance_id=instance, folder_id=folder, CollectionFolder=folders[folder])
            notes = {n['field_id']: n['value'] for n in item.get('notes', [])}
            for field, name in [(1, 'Collection Media Condition'), (2, 'Collection Sleeve Condition'), (3, 'Collection Notes')]:
                extra[name] = notes.get(field, '')
        else: extra['Notes'] = item.get('notes', '')
        if identity in seen: raise ValueError('duplicate page item')
        seen.add(identity)
        out.append(dw._row(r, header, extra))
    return out


def _csv_bytes(rows):
    out = io.StringIO(newline=''); csv.writer(out).writerows(rows)
    return out.getvalue().encode('utf-8')


def _stage(path, data):
    fd, temp = tempfile.mkstemp(prefix='.discogs-sync-', dir=os.path.dirname(path) or '.')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        return temp
    except BaseException:
        os.unlink(temp); raise


def _publish(files):
    """Stage all files before replacing; restore earlier files on a publication error."""
    staged, backups, done, preserve = {}, {}, [], set()
    try:
        for path, data in files:
            staged[path] = _stage(path, data)
            try:
                with open(path, 'rb') as f: backups[path] = _stage(path, f.read())
            except FileNotFoundError: backups[path] = None
        for path, _ in files:
            os.replace(staged[path], path); done.append(path)
    except BaseException:
        recovery_failed = False
        for path in reversed(done):
            try:
                if backups[path] is None: os.unlink(path)
                else: os.replace(backups[path], path)
            except OSError:
                recovery_failed = True
                if backups[path]: preserve.add(backups[path])
        if recovery_failed:
            raise dw.DiscogsError('Cache save and recovery failed; recovery files remain beside the caches') from None
        raise
    finally:
        for temp in list(staged.values()) + list(backups.values()):
            if temp and temp not in preserve and os.path.exists(temp): os.unlink(temp)


def sync():
    if dw.DRY: raise dw.DiscogsError('Discogs sync is disabled in dry-run mode')
    with dw.DATA_LOCK:
        try:
            if not dw._token(): raise dw.DiscogsError('No Discogs token configured')
            identity = _get('/oauth/identity')
            name = identity.get('username')
            if not isinstance(name, str) or not name: raise ValueError('missing username')
            user = urllib.parse.quote(name, safe='')
            time.sleep(1.1)
            folders = _get('/users/%s/collection/folders' % user)['folders']
            folders = {_integer(f['id']): f['name'] for f in folders}
            time.sleep(1.1)
            collection = _pages('/users/%s/collection/folders/0/releases' % user, 'releases')
            time.sleep(1.1)
            wantlist = _pages('/users/%s/wants' % user, 'wants')
            col = _rows(collection, _header(dw.COLLECTION_CSV, COL_HEADER, ['instance_id', 'folder_id'] + EXTRA), folders)
            want = _rows(wantlist, _header(dw.WANTLIST_CSV, WANT_HEADER, ['Date Added'] + EXTRA))
            result = {'collection': len(collection), 'wantlist': len(wantlist),
                      'synced_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
            _publish([(dw.COLLECTION_CSV, _csv_bytes(col)), (dw.WANTLIST_CSV, _csv_bytes(want)),
                      (STATUS_PATH, json.dumps(result).encode('utf-8'))])
            dw._username = name
            return result
        except dw.DiscogsError: raise
        except (KeyError, ValueError, TypeError, AttributeError, StopIteration):
            raise dw.DiscogsError('Discogs returned incomplete account data; previous cache kept') from None
        except OSError:
            raise dw.DiscogsError('Could not save Discogs account data') from None
