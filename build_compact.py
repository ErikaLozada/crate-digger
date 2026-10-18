"""Builds data/compact.json from the raw downloads fetch_discogs.sh saves in data/releases, data/masters and data/itunes.

Run after fetch_discogs.sh, then restart the service (or press Refresh) to load it.
"""
import json, os
from server import compact

D = 'data/'

def ids(folder):
    return sorted(f[:-5] for f in os.listdir(D + folder) if f.endswith('.json'))

def raw(folder, i):
    r = json.load(open('%s%s/%s.json' % (D, folder, i), encoding='utf-8'))
    return None if r.get('missing') else r

def release(r):
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

out = {'releases': {}, 'masters': {}, 'itunes': {}}
for i in ids('releases'):
    r = raw('releases', i)
    if r: out['releases'][i] = release(r)
for i in ids('masters'):
    m = raw('masters', i)
    if m: out['masters'][i] = master(m)
for i in ids('itunes'):
    out['itunes'][i] = itunes(json.load(open('%situnes/%s.json' % (D, i), encoding='utf-8')))

if __name__ == '__main__':
    json.dump(out, open(D + 'compact.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('compact.json: %d releases, %d masters, %d iTunes lookups' % tuple(len(out[k]) for k in out))
