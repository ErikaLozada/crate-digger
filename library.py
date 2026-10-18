"""Crate Digger, Phase 0: read the Apple Music library export (Library.xml)
and match Discogs records to it."""
import plistlib, re, unicodedata, difflib, collections, os, hashlib

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)
    s = re.sub(r'\b(remaster(ed)?|deluxe|edition|expanded|version|the|ep|single|feat|featuring|and|with|trio|quartet|quintet|his|y)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def load(path):
    L = plistlib.load(open(path, 'rb'))
    liked = set()
    for p in L['Playlists']:
        if p.get('Name') == 'Liked songs':
            liked.update(str(i['Track ID']) for i in p.get('Playlist Items', []))
    # The export does not have a separate Favourite playlist; Music.app/iTunes
    # records favourites on the track itself. Keep the union of both signals.
    liked.update(str(tid) for tid, t in L['Tracks'].items()
                 if t.get('Loved') or t.get('Favorited'))
    alb = {}
    for tid, t in L['Tracks'].items():
        tid = str(tid)
        if tid not in liked:
            continue
        aa = t.get('Album Artist') or t.get('Artist') or ''
        a = alb.setdefault((aa, t.get('Album') or ''), {
            'artist': aa, 'album': t.get('Album') or '', 'year': t.get('Year'), 'genre': t.get('Genre'),
            'tracks': 0, 'plays': 0, 'liked': 0, 'saved': 0, 'track_artists': set()})
        a['tracks'] += 1
        a['saved'] += 0 if t.get('Playlist Only') else 1
        a['plays'] += t.get('Play Count', 0)
        a['liked'] += 1
        a['track_artists'].add(t.get('Artist') or '')
    out = []
    for i, a in enumerate(sorted(alb.values(), key=lambda a: (a['artist'].lower(), a['album'].lower()))):
        a['i'] = i
        # an id that stays the same when the library changes, so saved ratings keep pointing at the same album
        a['k'] = str(int(hashlib.md5((a['artist'] + '|' + a['album']).encode('utf-8')).hexdigest(), 16) % 90000000 + 10000000)
        a['n_artist'] = norm(a['artist'] + ' ' + ' '.join(sorted(a['track_artists'])))
        a['n_album'] = norm(a['album'])
        a['track_artists'] = sorted(a['track_artists'])
        out.append(a)
    return out

def find_album(lib, artist_names, titles):
    """The library album that is this record, or None."""
    toks, compact = set(), set()
    for n in artist_names:
        toks |= {w for w in norm(n).split() if len(w) > 2}
        compact.add(re.sub(r'[^a-z0-9]', '', norm(n)))
    best = None
    for a in lib:
        if not a['n_album']: continue
        at = set(a['n_artist'].split())
        ac = a['n_artist'].replace(' ', '')
        if not (toks & at) and not any(c and len(c) >= 3 and c in ac for c in compact): continue
        for t in titles:
            nt = norm(t)
            if not nt: continue
            r = difflib.SequenceMatcher(None, nt, a['n_album']).ratio()
            if len(nt) >= 5 and (a['n_album'].startswith(nt) or nt.startswith(a['n_album'])): r = max(r, 0.9)
            if r >= 0.86 and (best is None or r > best[0]): best = (r, a)
    return best[1] if best else None

def by_artist(lib, artist_names):
    """Everything in the library by any of these artists."""
    hits = []
    for n in artist_names:
        nn = norm(n)
        if len(nn) < 4: continue
        for a in lib:
            if re.search(r'\b' + re.escape(nn) + r'\b', a['n_artist']) and a not in hits: hits.append(a)
    return hits
