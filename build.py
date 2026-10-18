"""Builds data/results.json with the library and the by-sound picks merged in, then the test page."""
import json, re, collections, os
import engine, library, sound_picks

shelf, want, loo, wres, pairs, samples, recs = engine.main()
D = engine.DATA
R = json.load(open(D + 'results.json', encoding='utf-8'))
R['want'] = {int(k): v for k, v in R['want'].items()}
lib = library.load(D + 'Library.xml' if os.path.exists(D + 'Library.xml') else 'Library.xml')
old_lib = library.load('Library_old.xml') if os.path.exists('Library_old.xml') else []   # the export the first ratings were made against
N = library.norm
g = shelf + want

def titles(t): return re.split(r'\s=\s', t.rel['title'] or '') + [t.title]
R['lib'], R['libArtist'] = {}, {}
for t in g:
    names = list(t.main.values()) or [t.artist]
    a = library.find_album(lib, names, titles(t))
    R['lib'][t.id] = {'k': a['k'], 'artist': a['artist'], 'album': a['album'], 'plays': a['plays'], 'liked': a['liked']} if a else None
    others = [x for x in library.by_artist(lib, list(t.main.values())) if not a or x['i'] != a['i']]
    R['libArtist'][t.id] = {'albums': len(others), 'plays': sum(x['plays'] for x in others), 'liked': sum(x['liked'] for x in others)} if others else None

def find_in(L, aq, bq):
    c = [a for a in L if N(aq) in a['n_artist'] or N(aq).replace(' ', '') in a['n_artist'].replace(' ', '')]
    if bq: c = [a for a in c if N(bq) in a['n_album'] or N(bq).replace(' ', '') in a['n_album'].replace(' ', '')]
    c.sort(key=lambda a: (-a['liked'], -a['plays']))
    return c[0] if c else None
def find_lib(aq, bq):
    """The pick as first shown (from the older export), refreshed from the current library when it is still there."""
    first = find_in(old_lib, aq, bq) if old_lib else None
    if first:
        now = next((a for a in lib if a['k'] == first['k']), None)
        return (now, False) if now else (first, True)
    a = find_in(lib, aq, bq)
    return (a, False) if a else (None, False)
def find_shelf(aq, bq):
    c = [t for t in shelf if N(aq) in N(t.artist) and (not bq or N(bq) in N(t.title) or N(bq).replace(' ', '') in N(t.title).replace(' ', ''))]
    return c[0] if c else None

# the whole library, for the prompt the smaller model gets: [index, artist, album, year, genre, plays, liked]
R['libList'] = [[a['k'], a['artist'], a['album'], a['year'], a['genre'], a['plays'], a['liked']] for a in lib]
R['sound'] = {}
for rid, (desc, sure, picks) in sound_picks.PICKS.items():
    out = []
    for where, aq, bq, why in picks:
        if where == 'L':
            a, gone = find_lib(aq, bq); assert a, (rid, aq, bq)
            n_alb = len({x['i'] for x in library.by_artist(lib, [a['artist']])}) if not bq else 1
            out.append({'k': f"A:L{a['k']}", 'where': 'Library', 'gone': gone, 'artist': a['artist'], 'album': a['album'] if bq else '',
                        'year': a['year'] if bq else None, 'why': why,
                        'plays': a['plays'] if bq else sum(x['plays'] for x in library.by_artist(lib, [a['artist']])),
                        'liked': a['liked'] if bq else sum(x['liked'] for x in library.by_artist(lib, [a['artist']])),
                        'n': n_alb})
        else:
            t = find_shelf(aq, bq); assert t, (rid, aq, bq)
            la = R['lib'].get(t.id)
            out.append({'k': f"A:S{t.id}", 'where': 'Shelf', 'artist': t.artist, 'album': t.title, 'year': t.oyear, 'why': why,
                        'plays': la['plays'] if la else None, 'liked': la['liked'] if la else None, 'fmt': t.kind})
    R['sound'][rid] = {'desc': desc, 'sure': sure, 'picks': out}

# One territory line per wantlist card: B's facts first; if they find nothing, fall back on what A found.
for t in want:
    w = R['want'][t.id] if t.id in R['want'] else R['want'][str(t.id)]
    w['terrB'] = w['territory']
    snd = R['sound'].get(t.id)
    if w['territory'] == 'new' and snd and snd['sure']:
        heard = [p for p in snd['picks'] if p['where'] == 'Shelf' or (p['plays'] or 0) + (p['liked'] or 0) > 0]
        if len(heard) >= 2:
            names = ', '.join(p['artist'].split(',')[0] for p in heard[:3])
            w['territory'], w['why'] = 'nearby', f"no label, musician or style link, but by sound it is close to {len(heard)} things you have: {names}"

def kind(k): return 'same artist' if k[0] else 'shared musician' if k[1] else 'same label' if k[2] else 'same producer or writer' if k[3] else 'style and era'
def top(res):
    c = collections.Counter(kind(v['matches'][0]['key']) for v in res.values() if v['matches'])
    return ', '.join(f"{k} {n}" for k, n in c.most_common())
tbm = [t for t in g if 'Three Blind Mice' in t.labels.values()]
by = {t.id: t for t in shelf}; pp = []; ok = 0
for ids in pairs:
    t = by[ids[0]]; r = engine.match(t, [o for o in shelf if o.id != t.id])
    ok += bool(r['own'] and r['own']['kind'] == 'other_edition')
    pp.append({'title': f"{t.artist}, {t.title}", 'eds': [f"{by[i].kind} {by[i].year}" + (f", {by[i].rel['country']}" if by[i].rel['country'] else '') for i in ids]})
R['auto'] = {'pairs': pp, 'pairs_ok': ok, 'total': len(g),
    'apple': sum(1 for t in g if samples[t.id]['apple']), 'video': sum(1 for t in g if samples[t.id]['video']),
    'either': sum(1 for t in g if samples[t.id]['apple'] or samples[t.id]['video']),
    'tbm': len(tbm), 'tbm_apple': sum(1 for t in tbm if samples[t.id]['apple']), 'tbm_video': sum(1 for t in tbm if samples[t.id]['video']),
    'top_shelf': top(loo), 'top_want': top(wres),
    'blank': sum(1 for t in g if not t.family), 'named': sum(1 for t in g if t.family_how == 'named' and t.family),
    'lib_albums': len(lib), 'lib_played': sum(1 for a in lib if a['plays'] or a['liked']),
    'lib_want': sum(1 for t in want if R['lib'][t.id]), 'lib_shelf': sum(1 for t in shelf if R['lib'][t.id]),
    'lib_artist_want': sum(1 for t in want if R['libArtist'][t.id] or R['lib'][t.id]),
    'lib_artist_shelf': sum(1 for t in shelf if R['libArtist'][t.id] or R['lib'][t.id]),
    'sound_picks': sum(len(v['picks']) for v in R['sound'].values()),
    'sound_lib': sum(1 for v in R['sound'].values() for p in v['picks'] if p['where'] == 'Library')}
json.dump(R, open(D + 'results.json', 'w', encoding='utf-8'), ensure_ascii=False)
if os.path.exists('page.tpl.html'):
    data = json.dumps(R, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    open('crate-digger-phase0.html', 'w', encoding='utf-8').write(open('page.tpl.html', encoding='utf-8').read().replace('__DATA__', data))
print({k: v for k, v in R['auto'].items() if k.startswith('lib') or k.startswith('sound')})
