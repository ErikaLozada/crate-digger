"""Crate Digger, Phase 0: matching rules.

Finds the closest records on the shelf to a given record and says why.
It does not score whether you will like a record.

Run    : python3 engine.py   (from the CrateDigger folder)
Inputs : data/compact.json (Discogs release and master details), data/collection.csv, data/wantlist.csv
Output : data/results.json (leave-one-out on the shelf, the wantlist run, ownership, samples)
"""
import csv, json, os, re, unicodedata, collections, difflib, random
import styles as ST

DATA = 'data/' if os.path.isdir('data') else ''

# ----------------------------------------------------------------------------
# Rules you can tune
# ----------------------------------------------------------------------------
# Labels too broad to say anything about the music. A match on these is ignored.
BROAD_LABELS = {
    'columbia', 'sony music', 'sony classical', 'atlantic', 'decca', 'epic', 'reprise records',
    'a&m records', 'polydor', 'philips', 'universal', 'elektra', 'warner bros. records',
    'warner records', 'parlophone', 'arista', 'rca', 'rca victor', 'capitol records', 'emi',
    'mercury', 'cbs/sony', 'cbs', 'victor', 'ume', 'universal music', 'universal music group',
    'world record club', "his master's voice", 'island records', 'virgin', 'geffen records',
    'interscope records', 'mca records', 'wea', 'warner music', 'sony', 'bmg', 'casablanca',
    'craft recordings', 'universal music australia', 'sony music entertainment', 'legacy',
    'warner music france', 'wea records ltd.', 'ariola', 'go! beat', 'laface records',
    'united artists records', 'london records', 'cbs records', 'emi classics', 'rhino records',
    'not on label', 'music on vinyl', 'waxtime in color', 'waxtime',
}
ERA_YEARS = 10          # two records are "same era" when their original years are this close
BIG_LINEUP = 12         # above this many credited players, only featured players count
FAMILIAR_STYLE = 3      # shelf records in the same main style needed for "familiar"
LIBRARY_FAMILIAR = 20   # library albums in the matching genre that, with one shelf record, make it "familiar"
LIBRARY_NEARBY = 10     # library albums in the matching genre needed for "nearby"
LISTEN_PLAYS = 5        # plays of an artist in Apple Music that count as "you listen to them"
MAX_MATCHES = 5

NON_MUSICAL = re.compile(
    r'engineer|photo|liner|design|record(ed|ing)|mix|master|manag|executive|art direction|artwork|'
    r'lacquer|promot|coordinat|supervis|edit|product|^other|contractor|a&r|cover|crew|directed|'
    r'project|illustrat|reissue|technic|copyist|booklet|compil|layout|creative|graphic|advisor|'
    r'legal|sleeve|assist|transfer|translat|research|typograph|thanks|concept|remix|score editor|'
    r'programmed|production|public|press|librar|sequenc|restor|digit|tape|studio|booking|'
    r'film|video|styl|hair|make-up|text|notes|interview|adapt', re.I)
WRITER = re.compile(r'compos|written|music by|lyrics|words by|songwriter|libretto', re.I)
PRODUCER = re.compile(r'^(co-)?producer', re.I)

VARIOUS = 194

# ----------------------------------------------------------------------------
def clean_name(s):
    s = (s or '').split(' = ')[0]
    return re.sub(r'\s*\(\d+\)$', '', s).strip()

def split_roles(role):
    return [re.sub(r'\s*\[.*?\]', '', x).strip() for x in re.split(r',\s*(?![^\[]*\])', role or '') if x.strip()]

def fmt_of(rel):
    names = [f['name'] for f in rel['formats']]
    d = [x for f in rel['formats'] for x in f['d']]
    kind = 'Vinyl' if 'Vinyl' in names else ('CD' if any(n in ('CD', 'SACD', 'CDr') for n in names) else (names[0] if names else '?'))
    reissue = any(x in d for x in ('Reissue', 'Repress', 'Remastered'))
    qty = sum(int(f['qty'] or 1) for f in rel['formats'] if f['name'] in ('Vinyl', 'CD', 'SACD'))
    return kind, reissue, qty

class Rec:
    def __init__(self, rel, masters, source, csvrow):
        self.id = rel['id']; self.rel = rel; self.source = source
        self.title = clean_name(rel['title'])
        self.master = rel['master_id']
        m = masters.get(str(self.master)) if self.master else None
        self.year = rel['year'] or None
        self.oyear = (m and m['year']) or self.year            # original year of the album
        self.genres = set(rel['genres']); self.styles = set(rel['styles'])
        if m: self.styles |= set(m['styles'])
        self.family, self.family_how = ST.main_family(self.styles, self.genres, self.id)
        self.kind, self.reissue, self.qty = fmt_of(rel)
        self.main = {a[0]: clean_name(a[1]) for a in rel['artists'] if a[0] and a[0] != VARIOUS}
        self.artist = clean_name(rel['artists_sort']) if rel['artists_sort'] else ', '.join(self.main.values())
        self.labels = {}
        for lid, name, catno, _ in rel['labels']:
            if lid: self.labels[lid] = clean_name(name)
        self.catno = next((l[2] for l in rel['labels'] if l[2] and l[2].lower() != 'none'), '')
        # people
        players = collections.defaultdict(set)   # id -> roles
        writers = collections.Counter(); producers = {}
        names = dict(self.main)
        ntr = max(rel['ntracks'], 1)
        for pid, name, role, _ in rel['extra']:
            if not pid: continue
            names[pid] = clean_name(name)
            for r in split_roles(role):
                if PRODUCER.search(r): producers[pid] = names[pid]
                elif WRITER.search(r): writers[pid] += ntr
                elif NON_MUSICAL.search(r): pass
                else: players[pid].add(r)
        seen = set()
        for pid, name, role, pos in rel['track_credits']:
            if not pid or pid == VARIOUS: continue
            names[pid] = clean_name(name)
            if role == '__track_artist__':
                players[pid].add('Performer'); continue
            for r in split_roles(role):
                if PRODUCER.search(r): producers[pid] = names[pid]
                elif WRITER.search(r):
                    if (pid, pos) not in seen: writers[pid] += 1; seen.add((pid, pos))
                elif NON_MUSICAL.search(r): pass
                else: players[pid].add(r)
        big = len(players) > BIG_LINEUP
        FEATURED = re.compile(r'conductor|orchestra|leader|soloist|featuring|choir|chorus|ensemble|band', re.I)
        self.players = {}
        for pid, roles in players.items():
            if pid in self.main: continue
            if big and not any(FEATURED.search(r) for r in roles): continue
            self.players[pid] = sorted(roles)[:2]
        self.writers = {pid for pid, n in writers.items() if n * 2 >= ntr and pid not in self.main}
        self.producers = {pid: n for pid, n in producers.items() if pid not in self.main}
        self.names = names
        self.csv = csvrow

    def decade(self):
        return f"{(self.oyear // 10) * 10}s" if self.oyear else None

def is_specific(label_name):
    return label_name.lower() not in BROAD_LABELS

def link(t, o):
    """Why is owned record o close to target t? Returns None when there is no real link."""
    out = {'artist': [], 'people': [], 'label': [], 'producer': [], 'writer': [], 'styles': [], 'era': False}
    out['artist'] = [t.main[i] for i in t.main if i in o.main]
    tp = {**{i: None for i in t.main}, **t.players}; op = {**{i: None for i in o.main}, **o.players}
    for i in tp:
        if i in op and not (i in t.main and i in o.main):
            lead = i in t.main or i in o.main
            role = (t.players.get(i) or o.players.get(i) or [''])[0]
            out['people'].append({'name': t.names.get(i) or o.names.get(i), 'role': role, 'lead': lead})
    out['label'] = [n for i, n in t.labels.items() if i in o.labels and is_specific(n)]
    out['producer'] = [n for i, n in t.producers.items() if i in o.producers]
    out['writer'] = [t.names[i] for i in t.writers if i in o.writers or i in o.main]
    era = bool(t.oyear and o.oyear and abs(t.oyear - o.oyear) <= ERA_YEARS)
    if t.family and t.family == o.family:          # one main style each, and it is the same one
        out['styles'] = [t.family]; out['era'] = era
    npeople = sum(2 if p['lead'] else 1 for p in out['people'])
    style_score = (2 if era else 1) if out['styles'] else 0
    key = (1 if out['artist'] else 0, npeople, 1 if out['label'] else 0,
           1 if (out['producer'] or out['writer']) else 0, style_score)
    if not any(key): return None
    out['key'] = key
    return out

def reason_text(t, o, l):
    parts = []
    if l['artist']: parts.append('Same artist: ' + ', '.join(l['artist'][:2]))
    for p in sorted(l['people'], key=lambda p: -p['lead'])[:2]:
        role = (p['role'] or '').lower()
        if 'arrang' in role or 'orchestrated' in role: parts.append(f"{p['name']} arranged both")
        elif 'conduct' in role: parts.append(f"{p['name']} conducts on both")
        else: parts.append(f"{p['name']} plays on both" + (f" ({role})" if role and role != 'performer' else ''))
    if len(l['people']) > 2:
        n = len(l['people']) - 2
        parts.append(f"+{n} more shared musician{'s' if n > 1 else ''}")
    if l['label']: parts.append('Same label: ' + l['label'][0])
    if l['producer'] and not l['label']: parts.append('Same producer: ' + l['producer'][0])
    if l['writer'] and not l['artist']: parts.append(l['writer'][0] + ' is credited on both')
    if l['styles']:
        if l['styles'][0] in ST.NO_PERIOD: parts.append('Same main style: ' + l['styles'][0])
        else: parts.append('Same main style: ' + l['styles'][0] + (f", {o.decade()}" if o.decade() else '') + ('' if l['era'] else ' (a different era)'))
    return parts

def match(t, shelf, lib=None):
    """Closest shelf records to t, the facts about where it sits, the territory line and the ownership answer.
    lib: what the Apple Music library says about t, from library_facts()."""
    lib = lib or {}
    own = None
    cands = []
    for o in shelf:
        if o.id == t.id:
            own = {'kind': 'same', 'rec': o.id}; continue
        if t.master and o.master == t.master:
            own = own or {'kind': 'other_edition', 'rec': o.id}; continue
        l = link(t, o)
        if l: cands.append((l['key'], o, l))
    cands.sort(key=lambda c: (c[0], -abs((c[1].oyear or 0) - (t.oyear or 0))), reverse=True)
    matches, seen_masters = [], set()
    for k, o, l in cands:                      # one row per album, even if you own two editions
        if o.master and o.master in seen_masters: continue
        if o.master: seen_masters.add(o.master)
        matches.append({'id': o.id, 'reasons': reason_text(t, o, l), 'key': list(k)})
        if len(matches) == MAX_MATCHES: break

    n_artist = sum(1 for k, o, l in cands if k[0])
    people = {p['name'] for k, o, l in cands for p in l['people']}
    # a lead artist of one record who plays on the other: as good as the same artist
    leads = collections.Counter(p['name'] for k, o, l in cands for p in l['people'] if p['lead'])
    labels = collections.Counter(n for k, o, l in cands for n in l['label'])
    fam_all = sum(1 for k, o, l in cands if l['styles'])
    fam_era = sum(1 for k, o, l in cands if l['styles'] and l['era'])
    lf = lib.get('family')            # {'n':…, 'genres':[…], 'top':[…], 'broad':bool}
    la, lb = lib.get('artist'), lib.get('album')
    who = next(iter(t.main.values()), t.artist) if len(t.main) == 1 else 'these artists'
    s = lambda n: '' if n == 1 else 's'

    if n_artist:
        terr, why = 'familiar', f"you own {n_artist} other record{s(n_artist)} by {who}"
    elif lb and (lb['plays'] or lb['liked']):
        terr, why = 'familiar', f"this album is in your Apple Music library ({lb['plays']} play{s(lb['plays'])}, {lb['liked']} liked)"
    elif la and (la['plays'] >= LISTEN_PLAYS or la['liked']):
        terr, why = 'familiar', f"you listen to {who} in Apple Music ({la['plays']} play{s(la['plays'])}, {la['liked']} liked)"
    elif labels:
        name, n = labels.most_common(1)[0]
        terr, why = 'familiar', f"you own {n} record{s(n)} on {name}"
    elif leads:
        name, n = leads.most_common(1)[0]
        terr, why = 'familiar', f"{name} plays on {n} record{s(n)} you own"
    elif len(people) >= 2:
        terr, why = 'familiar', f"{len(people)} musicians here play on records you own"
    elif fam_all >= FAMILIAR_STYLE:
        terr, why = 'familiar', f"you own {fam_all} {t.family} records" + ('' if t.family in ST.NO_PERIOD else f", {fam_era} from the same era" if fam_era else ", none from the same era")
    elif fam_all and lf and not lf['broad'] and lf['n'] >= LIBRARY_FAMILIAR:
        terr, why = 'familiar', f"you own {fam_all} {t.family} record{s(fam_all)} and have {lf['n']} albums of it in your library"
    elif fam_all:
        terr, why = 'nearby', f"you own {fam_all} {t.family} record{s(fam_all)}"
    elif lf and not lf['broad'] and lf['n'] >= LIBRARY_NEARBY:
        terr, why = 'nearby', f"nothing like it on your shelf, but {lf['n']} albums of {t.family} in your library"
    elif len(people) == 1:
        terr, why = 'nearby', f"{next(iter(people))} plays on a record you own"
    elif la or lb:
        n = (la or lb)['plays']
        terr, why = 'nearby', f"{who} is in your Apple Music library ({n} play{s(n)})"
    else:
        terr, why = 'new', 'nothing you own or listen to is close'

    facts = []
    period = t.family not in ST.NO_PERIOD
    facts.append(('Main style', (t.family + (f" · {t.decade()}" if period and t.decade() else '')) if t.family else 'Not clear from Discogs, so left blank'))
    if t.family:
        facts.append(('On your shelf', (f"{fam_all} record{s(fam_all)} in this style" + (f", {fam_era} from the same era" if period else '')) if fam_all else 'No records in this style'))
        if lf and lf['n'] and not lf['broad']:      # only when Apple's genre is about as narrow as the style
            facts.append(('In your library', f"{lf['n']} albums filed under {' or '.join(lf['genres'])}"
                          + (f"; most played: {', '.join(lf['top'])}" if lf['top'] else '')))
    for name, n in labels.most_common(2):
        facts.append(('Label', f"You own {n} record{s(n)} on {name}"))
    if people:
        ordered = [n for n, _ in leads.most_common()] + sorted(people - set(leads))
        facts.append(('Musicians', ', '.join(ordered[:4]) + (f" and {len(ordered) - 4} more" if len(ordered) > 4 else '') + f" play{'s' if len(ordered) == 1 else ''} on records you own"))
    return {'matches': matches, 'territory': terr, 'why': why, 'own': own, 'facts': facts,
            'counts': {'artist': n_artist, 'people': len(people), 'label': sum(labels.values()), 'style': fam_all, 'style_era': fam_era}}

def library_facts(t, lib_albums, find_album, by_artist):
    """What the Apple Music library says about record t."""
    titles = re.split(r'\s=\s', t.rel['title'] or '') + [t.title]
    a = find_album(lib_albums, list(t.main.values()) or [t.artist], titles)
    others = [x for x in by_artist(lib_albums, list(t.main.values())) if not a or x['i'] != a['i']]
    out = {'album': {'artist': a['artist'], 'album': a['album'], 'plays': a['plays'], 'liked': a['liked']} if a else None,
           'artist': {'albums': len(others), 'plays': sum(x['plays'] for x in others), 'liked': sum(x['liked'] for x in others)} if others else None,
           'family': None}
    if t.family and t.family in ST.APPLE_GENRES:
        gs = ST.APPLE_GENRES[t.family]
        hits = [x for x in lib_albums if x['genre'] in gs]
        present = [g for g in gs if any(x['genre'] == g for x in hits)]
        byart = collections.Counter()
        for x in hits: byart[x['artist']] += x['plays']
        out['family'] = {'n': len(hits), 'genres': present[:2], 'broad': t.family in ST.BROAD_APPLE,
                         'top': [n for n, p in byart.most_common(3) if p]}
    return out

# ----------------------------------------------------------------------------
def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)
    s = re.sub(r'\b(remaster(ed)?|deluxe|edition|expanded|version|original|motion picture|soundtrack|the|music from|ep|single|bonus track|anniversary)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def apple_match(t, results):
    """Is this album in Apple's catalogue? Compares title and artist loosely."""
    best = None
    titles = {norm(x) for x in re.split(r'\s=\s', t.rel['title'] or '')} | {norm(t.title)}
    titles = {x for x in titles if x}
    ta = set(norm(' '.join(t.main.values()) or t.artist).split())
    for x in results:
        nt = norm(x['name'])
        if not nt or re.search(r'karaoke|tribute|in the style of|originally performed|made famous', x['name'] + ' ' + x['artist'], re.I): continue
        xa = set(norm(x['artist']).split())
        artist_ok = not ta or bool(ta & xa) or bool(ta & set(nt.split()))
        for tt in titles:
            ratio = difflib.SequenceMatcher(None, tt, nt).ratio()
            contains = len(tt) >= 4 and (tt in nt or nt in tt)
            score = max(ratio, 0.9 if contains else 0)
            exact_long = tt == nt and len(tt) >= 8      # the search already included the artist
            if ((artist_ok and score >= 0.72) or exact_long) and (best is None or score > best[0]):
                best = (score, x)
    return best[1] if best else None

def describe(t):
    return {'id': t.id, 'artist': t.artist, 'title': t.title, 'year': t.year, 'oyear': t.oyear,
            'kind': t.kind, 'qty': t.qty, 'reissue': t.reissue, 'country': t.rel['country'],
            'genres': sorted(t.genres), 'styles': sorted(t.rel['styles']) or sorted(t.styles),
            'label': next(iter(t.labels.values()), ''), 'catno': t.catno, 'family': t.family,
            'have': t.rel['have'], 'want': t.rel['want'], 'for_sale': t.rel['num_for_sale'],
            'low': t.rel['lowest_price'], 'uri': t.rel['uri'], 'source': t.source}

def main():
    D = json.load(open(DATA + 'compact.json'))
    col = list(csv.DictReader(open(DATA + 'collection.csv', encoding='utf-8-sig')))
    wl = list(csv.reader(open(DATA + 'wantlist.csv', encoding='utf-8-sig')))[1:]
    shelf = [Rec(D['releases'][r['release_id']], D['masters'], 'shelf', r) for r in col]
    want = [Rec(D['releases'][r[7]], D['masters'], 'wantlist', r) for r in wl]
    recs = {t.id: describe(t) for t in shelf + want}

    lib_albums, LF = None, {}
    path = DATA + 'Library.xml' if os.path.exists(DATA + 'Library.xml') else ('Library.xml' if os.path.exists('Library.xml') else None)
    if path:
        import library
        lib_albums = library.load(path)
        LF = {t.id: library_facts(t, lib_albums, library.find_album, library.by_artist) for t in shelf + want}
    loo = {}
    for t in shelf:
        loo[t.id] = match(t, [o for o in shelf if o.id != t.id], LF.get(t.id))
    wres = {t.id: match(t, shelf, LF.get(t.id)) for t in want}

    # ownership: albums held in more than one edition
    by_master = collections.defaultdict(list)
    for t in shelf:
        if t.master: by_master[t.master].append(t.id)
    pairs = [ids for ids in by_master.values() if len(ids) > 1]

    # samples
    samples = {}
    for t in shelf + want:
        a = apple_match(t, D['itunes'].get(str(t.id), []))
        samples[t.id] = {'apple': ({'name': a['name'], 'artist': a['artist'], 'url': a['url']} if a else None),
                         'video': (t.rel['videos'][0][0] if t.rel['videos'] else None), 'nvideos': t.rel['nvideos']}

    random.seed(7)
    order = [t.id for t in shelf]; random.shuffle(order)
    json.dump({'recs': recs, 'loo': loo, 'want': wres, 'pairs': pairs, 'samples': samples, 'libfacts': LF,
               'shelf_order': order, 'want_order': [t.id for t in want]},
              open(DATA + 'results.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return shelf, want, loo, wres, pairs, samples, recs

if __name__ == '__main__':
    main()
