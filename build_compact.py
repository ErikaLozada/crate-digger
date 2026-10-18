"""Builds data/compact.json from the raw downloads in data/releases, data/masters and data/itunes.

The server's Refresh runs this after fetching new records. To run it by hand after fetch_discogs.sh:
  python3 build_compact.py      then press Refresh in the app (or restart the service)
"""
import json, os

D = 'data/'

def ids(folder):
    return sorted(f[:-5] for f in os.listdir(D + folder) if f.endswith('.json'))

def raw(folder, i):
    r = json.load(open('%s%s/%s.json' % (D, folder, i), encoding='utf-8'))
    return None if r.get('missing') else r

def release(r, compact):
    c = compact(r)
    c['videos'] = c['videos'][:3]          # nvideos keeps the full count
    c['series'] = [[s['id'], s['name']] for s in r.get('series', [])]
    c['companies'] = [[x['id'], x['name'], x['entity_type_name']] for x in r.get('companies', [])]
    c['rating'] = {k: r['community']['rating'][k] for k in ('count', 'average')}
    return c

def master(m):
    return {'id': m['id'], 'title': m['title'], 'year': m.get('year'), 'main_release': m.get('main_release'),
            'genres': m.get('genres', []), 'styles': m.get('styles', []), 'num_for_sale': m.get('num_for_sale'),
            'lowest_price': m.get('lowest_price'), 'artists': [[a['id'], a['name']] for a in m.get('artists', [])],
            'uri': m.get('uri')}

def itunes(r):
    return [{'artist': a.get('artistName'), 'name': a.get('collectionName'), 'year': (a.get('releaseDate') or '')[:4],
             'id': a.get('collectionId'), 'url': a.get('collectionViewUrl'), 'n': a.get('trackCount'),
             'genre': a.get('primaryGenreName')} for a in r.get('results', [])]

def build(compact):
    """compact: server.compact, which turns a Discogs API release into the shape engine.Rec reads."""
    out = {'releases': {}, 'masters': {}, 'itunes': {}}
    for i in ids('releases'):
        r = raw('releases', i)
        if r: out['releases'][i] = release(r, compact)
    for i in ids('masters'):
        m = raw('masters', i)
        if m: out['masters'][i] = master(m)
    for i in ids('itunes'):
        out['itunes'][i] = itunes(json.load(open('%situnes/%s.json' % (D, i), encoding='utf-8')))
    return out

def write(out):
    json.dump(out, open(D + 'compact.json.tmp', 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(D + 'compact.json.tmp', D + 'compact.json')

if __name__ == '__main__':
    from server import compact
    out = build(compact)
    write(out)
    print('compact.json: %d releases, %d masters, %d iTunes lookups' % tuple(len(out[k]) for k in out))
