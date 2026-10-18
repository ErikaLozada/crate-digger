"""Crate Digger prototype: local backend for the iPhone web app.

  python3 server.py            then open http://<this Mac>.local:8000 on the iPhone (same Wi-Fi)

Serves static/index.html and a small JSON API. The Discogs token (discogs_token.txt) and the
model keys stay here; the browser never sees them. The inspected release is looked up live on
Discogs; if that fails, the copy saved by fetch_discogs.sh is used and the card says so.
"""
import csv, json, os, re, socket, sys, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import engine, library, harness
import styles as ST

PORT = int(os.environ.get('CD_PORT', 8000))
HOST = os.environ.get('CD_HOST', '0.0.0.0')   # 127.0.0.1 when only tailscale serve should reach it
UA = 'CrateDiggerPrototype/0.1 (personal collection)'
TOKEN = open('discogs_token.txt').read().strip() if os.path.exists('discogs_token.txt') else os.environ.get('DISCOGS_TOKEN', '')

# ----------------------------------------------------------------------------
# Snapshots, loaded once at start and again on Refresh
def load():
    global D, SHELF, SHELF_IDS, LIB, H
    D = json.load(open('data/compact.json'))
    col = list(csv.DictReader(open('data/collection.csv', encoding='utf-8-sig')))
    missing = [r['release_id'] for r in col if r['release_id'] not in D['releases']]
    if missing: print('no saved details for shelf releases %s; run fetch_discogs.sh' % ', '.join(missing))
    SHELF = [engine.Rec(D['releases'][r['release_id']], D['masters'], 'shelf', r) for r in col if r['release_id'] in D['releases']]
    SHELF_IDS = {t.id for t in SHELF}
    LIB = library.load('data/Library.xml')
    H = harness.load_snapshots()           # shelf, want, lib, recs in the harness's own shape
    print('snapshots: %d shelf records, %d library albums' % (len(SHELF), len(LIB)))

# ----------------------------------------------------------------------------
# Outside services
def get(url, discogs=False, timeout=10):
    h = {'User-Agent': UA}
    if discogs and TOKEN: h['Authorization'] = 'Discogs token=' + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return json.load(r)

def compact(raw):
    """A Discogs API release in the shape compact.json uses, so engine.Rec can read it."""
    tracks = [t for t in raw.get('tracklist', []) if t.get('type_') == 'track']
    tc = []
    for tr in tracks:
        for a in tr.get('extraartists', []): tc.append([a['id'], a['name'], a['role'], tr['position']])
        for a in tr.get('artists', []): tc.append([a['id'], a['name'], '__track_artist__', tr['position']])
    vids = [[v['uri'], v['title']] for v in raw.get('videos', [])]
    return {'id': raw['id'], 'title': raw['title'], 'year': raw.get('year'), 'released': raw.get('released'),
            'country': raw.get('country'), 'genres': raw.get('genres', []), 'styles': raw.get('styles', []),
            'master_id': raw.get('master_id'), 'artists_sort': raw.get('artists_sort'),
            'artists': [[a['id'], a['name'], a['anv'], a['join']] for a in raw.get('artists', [])],
            'extra': [[a['id'], a['name'], a['role'], a['tracks']] for a in raw.get('extraartists', [])],
            'track_credits': tc, 'ntracks': len(tracks),
            'labels': [[l['id'], l['name'], l['catno'], l.get('entity_type_name')] for l in raw.get('labels', [])],
            'formats': [{'name': f['name'], 'qty': f['qty'], 'd': f.get('descriptions', []), 'text': f.get('text')}
                        for f in raw.get('formats', [])],
            'have': raw['community']['have'], 'want': raw['community']['want'],
            'num_for_sale': raw.get('num_for_sale'), 'lowest_price': raw.get('lowest_price'),
            'barcodes': [i['value'] for i in raw.get('identifiers', []) if i['type'] == 'Barcode'],
            'videos': vids, 'nvideos': len(vids), 'uri': raw['uri'],
            'tracks': [t['title'] for t in tracks][:40]}

def fetch_release(rid):
    """(raw release, raw master or {}, live?)"""
    try:
        raw, live = get('https://api.discogs.com/releases/%d?curr_abbr=AUD' % rid, True), True
    except Exception:
        p = 'data/releases/%d.json' % rid
        if not os.path.exists(p): raise
        raw, live = json.load(open(p)), False
    m = {}
    if raw.get('master_id'):
        p = 'data/masters/%d.json' % raw['master_id']
        try: m = get('https://api.discogs.com/masters/%d' % raw['master_id'], True) if live else json.load(open(p))
        except Exception: m = json.load(open(p)) if os.path.exists(p) else {}
    return raw, m, live

# ----------------------------------------------------------------------------
# API
def search(q):
    """Editions matching a barcode, catalogue number or artist/title."""
    kind, text = next(((k, q[k][0]) for k in ('barcode', 'catno', 'q') if q.get(k)), (None, ''))
    if not kind: return {'results': []}
    try:
        if not TOKEN: raise RuntimeError('no Discogs token')
        d = get('https://api.discogs.com/database/search?' + urllib.parse.urlencode(
            {kind: text, 'type': 'release', 'per_page': 50}), True)
        rows = [{'id': r['id'], 'title': r['title'], 'year': r.get('year'), 'country': r.get('country'),
                 'format': ', '.join(r.get('format', [])), 'label': (r.get('label') or [''])[0], 'catno': r.get('catno'),
                 'thumb': r.get('thumb'), 'owned': r['id'] in SHELF_IDS} for r in d['results']]
        return {'results': rows, 'source': 'discogs'}
    except Exception as e:
        return {'results': local_search(kind, text), 'source': 'local', 'note': 'Discogs search failed (%s); showing your shelf and wantlist only' % e}

def local_search(kind, text):
    n = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    want = n(text); out = []
    for rid, r in D['releases'].items():
        lab = r['labels'][0] if r['labels'] else [0, '', '', '']
        if kind == 'barcode': hit = any(n(b) == want for b in r['barcodes'])
        elif kind == 'catno': hit = any(n(l[2]) == want for l in r['labels'])
        else: hit = all(w in n(r['artists_sort'] + r['title']) for w in re.findall(r'\w+', text.lower()))
        if hit:
            k, _, q = engine.fmt_of(r)
            out.append({'id': r['id'], 'title': '%s - %s' % (engine.clean_name(r['artists_sort']), r['title']), 'year': r['year'],
                        'country': r['country'], 'format': ', '.join([f['name'] for f in r['formats']] + r['formats'][0]['d'] if r['formats'] else []),
                        'label': engine.clean_name(lab[1]), 'catno': lab[2], 'thumb': None, 'owned': r['id'] in SHELF_IDS})
    return out[:50]

def release(rid):
    raw, m, live = fetch_release(rid)
    rel = compact(raw)
    masters = {str(rel['master_id']): {'year': m.get('year'), 'styles': m.get('styles', [])}} if m else {}
    t = engine.Rec(rel, masters, 'shelf' if rid in SHELF_IDS else 'inspected', None)
    lf = engine.library_facts(t, LIB, library.find_album, library.by_artist)
    res = engine.match(t, [o for o in SHELF if o.id != rid] + ([next(o for o in SHELF if o.id == rid)] if rid in SHELF_IDS else []), lf)
    own = res['own']
    if own:
        o = next(x for x in SHELF if x.id == own['rec'])
        own = {'kind': own['kind'], 'format': o.kind, 'year': o.year, 'country': o.rel['country'],
               'label': next(iter(o.labels.values()), ''), 'reissue': o.reissue}
    elif lf['album']:
        own = {'kind': 'apple', **lf['album']}
    return {'id': rid, 'live': live, 'artist': t.artist, 'title': t.title, 'year': t.year, 'oyear': t.oyear,
            'decade': None if t.family in ST.NO_PERIOD else t.decade(),
            'format': t.kind, 'qty': t.qty, 'reissue': t.reissue, 'country': rel['country'],
            'label': next(iter(t.labels.values()), ''), 'catno': t.catno,
            'formats': ', '.join(d for f in rel['formats'] for d in [f['name']] + f['d']),
            'image': (raw.get('images') or [{}])[0].get('uri') or raw.get('thumb'),
            'style': t.family, 'own': own, 'facts': res['facts'], 'territory': res['territory'], 'why': res['why'],
            'market': {'low': rel['lowest_price'], 'have': rel['have'], 'want': rel['want'], 'for_sale': rel['num_for_sale']},
            'videos': rel['videos'][:3], 'uri': rel['uri'], 'tracks': rel['tracks']}

def samples(rid):
    raw, m, live = fetch_release(rid)
    t = engine.Rec(compact(raw), {}, 'inspected', None)
    out = {'tracks': [], 'apple_url': None, 'videos': [[v['uri'], v['title']] for v in raw.get('videos', [])][:3],
           'youtube': 'https://www.youtube.com/results?' + urllib.parse.urlencode({'search_query': t.artist + ' ' + t.title})}
    try:
        d = get('https://itunes.apple.com/search?' + urllib.parse.urlencode(
            {'term': t.artist + ' ' + t.title, 'entity': 'album', 'country': 'AU', 'limit': 5}))
        a = engine.apple_match(t, [{'name': x['collectionName'], 'artist': x['artistName'], 'id': x['collectionId'],
                                    'url': x['collectionViewUrl']} for x in d['results']])
        if a:
            songs = get('https://itunes.apple.com/lookup?id=%s&entity=song&country=AU' % a['id'])['results']
            out['apple_url'] = a['url']
            out['tracks'] = [{'name': s['trackName'], 'preview': s['previewUrl']} for s in songs if s.get('previewUrl')][:3]
    except Exception as e:
        out['error'] = str(e)
    return out

def recommend(rid):
    shelf, want, lib, recs = H
    model = harness.PRIMARY
    if not harness.api_key():
        return {'status': 'unavailable: no OpenRouter key on the backend', 'result': None}
    if str(rid) not in recs:
        raw, m, live = fetch_release(rid)
        masters = {str(raw.get('master_id')): {'year': m.get('year'), 'styles': m.get('styles', [])}} if m else {}
        recs = dict(recs, **{str(rid): engine.describe(engine.Rec(compact(raw), masters, 'inspected', None))})
    x = harness.run_one(model, rid, shelf, want, lib, recs)
    if x['result']:
        names = {**{k: '%s — %s' % (r['artist'], r['title']) for k, r in shelf.items()},
                 **{k: '%s — %s' % (a['artist'], a['album']) for k, a in lib.items()}}
        for p in x['result']['picks']:
            p['name'] = names[p['id']]; p['where'] = 'shelf' if p['id'][0] == 'S' else 'library'
            if p['id'][0] == 'L': p['plays'], p['liked'] = lib[p['id']]['plays'], lib[p['id']]['liked']
    return x

# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def route(self, method):
        u = urllib.parse.urlparse(self.path); p = u.path
        try:
            if method == 'GET' and p in ('/', '/index.html'):
                return self.send(200, open('static/index.html', 'rb').read(), 'text/html')
            if method == 'GET' and p == '/api/search': return self.send(200, search(urllib.parse.parse_qs(u.query)))
            m = re.fullmatch(r'/api/(release|samples|recommend)/(\d+)', p)
            if m and (method == 'POST') == (m.group(1) == 'recommend'):
                return self.send(200, {'release': release, 'samples': samples, 'recommend': recommend}[m.group(1)](int(m.group(2))))
            if method == 'POST' and p == '/api/refresh':
                load(); return self.send(200, {'shelf': len(SHELF), 'library': len(LIB)})
            self.send(404, {'error': 'not found'})
        except Exception as e:
            self.send(502, {'error': str(e)})

    def do_GET(self): self.route('GET')
    def do_POST(self): self.route('POST')
    def log_message(self, fmt, *a): sys.stderr.write('%s\n' % (fmt % a))

if __name__ == '__main__':
    load()
    print('open http://%s:%d on your iPhone (same Wi-Fi), or http://localhost:%d here' % (socket.gethostname(), PORT, PORT))
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
