"""Crate Digger prototype: one-pass recommendation harness.

Takes fixed snapshots (Discogs shelf from data/results.json, Apple Music library from
data/Library.xml) and a list of records, asks the configured model for a style family and up
to three close matches, validates the answer, and reports coverage, accuracy, latency and
availability. No scanning, no web UI.

  python3 harness.py --dry-run                 build the request for the first record, call nothing
  python3 harness.py --model primary           run the records in data/eval_set.json
  python3 harness.py --model fallback --ids 12596028,4864049

data/eval_set.json: [{"id": 12596028, "expected_style": "Jazz-funk & fusion"}, ...]
(expected_style is optional; without it accuracy is not scored). Without that file the 25
wantlist records are used. Runs are written to data/runs/ for the manual false-match review.
"""
import argparse, collections, json, os, sys, time
import library, styles
from check_models import PRIMARY, FALLBACK, api_key, chat

TIMEOUT = 20
FAMILIES = list(styles.FAMILIES) + styles.NAMED_ONLY + ['Other/uncertain']
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['sentence', 'style', 'picks'], 'properties': {
    'sentence': {'type': 'string'},
    'style': {'type': 'string', 'enum': FAMILIES},
    'picks': {'type': 'array', 'maxItems': 3, 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['id', 'reason'],
        'properties': {'id': {'type': 'string'}, 'reason': {'type': 'string'}}}}}}
SYSTEM = ('You help a record collector decide on a record in a shop. Given the record, return: one sentence '
          '(25 words at most) on what it is; its main style, one of the allowed families or Other/uncertain if you '
          'are not sure; and up to three picks from the collector\'s SHELF (S ids) and APPLE MUSIC LIBRARY (L ids) that '
          'are closest in sound, same sub-style and not a neighbour, each with a short reason. Closest, not most '
          'played. Use only ids from the two lists. Return fewer than three, or none, if nothing is truly close. '
          'Never return the record itself.')

def load_snapshots():
    R = json.load(open('data/results.json'))
    shelf = {'S%s' % i: r for i, r in R['recs'].items() if r['source'] == 'shelf'}
    want = {int(i): R['recs'][str(i)] for i in R['want_order']}
    lib = {'L' + a['k']: a for a in library.load('data/Library.xml')}
    return shelf, want, lib, R['recs']

def lists_text(shelf, lib, skip=None):
    """Lists first, record last, so the long part is identical between requests."""
    s = ['%s | %s - %s (%s) | %s' % (k, r['artist'], r['title'], r['year'], r['family'] or ', '.join(r['styles']))
         for k, r in shelf.items() if k != skip]
    l = ['%s | %s - %s (%s) | %s | %d plays, %d liked' % (k, a['artist'], a['album'], a['year'], a['genre'], a['plays'], a['liked'])
         for k, a in lib.items()]
    return 'FAMILIES: ' + '; '.join(FAMILIES) + '\n\nSHELF\n' + '\n'.join(s) + '\n\nAPPLE MUSIC LIBRARY\n' + '\n'.join(l)

def record_text(r):
    return 'RECORD\n%s - %s (%s), %s, %s. Genres: %s. Discogs styles: %s.' % (
        r['artist'], r['title'], r['year'], r['label'], r['country'], ', '.join(r['genres']), ', '.join(r['styles']) or 'none')

def ask(model, system, lists, record):
    """One model call -> parsed dict. Raises on timeout, HTTP error or bad JSON."""
    st, d = chat(model, [{'role': 'system', 'content': system}, {'role': 'user', 'content': lists + '\n\n' + record}], SCHEMA, TIMEOUT)
    if st != 200: raise RuntimeError('HTTP %s %s' % (st, d.get('error')))
    ans = json.loads(d['choices'][0]['message']['content'])
    ans['_usage'] = d.get('usage') or {}
    return ans

def clean(ans, valid, self_id):
    """Drop ids that are not in the snapshots, the record itself, repeats, and anything past three."""
    picks, seen = [], set()
    for p in ans['picks']:
        if p['id'] in valid and p['id'] != self_id and p['id'] not in seen:
            seen.add(p['id']); picks.append(p)
    picks = picks[:3]
    return {'sentence': ans['sentence'], 'style': ans['style'], 'picks': picks,
            'dropped': len(ans['picks']) - len(picks), 'usage': ans.get('_usage', {})}

def recommend(model, lists, record, valid, self_id, ask=ask):
    """One run; two more only if the first style is Other/uncertain. Majority style wins.
    Returns (chosen run or None, all runs)."""
    first = clean(ask(model, SYSTEM, lists, record), valid, self_id)
    if first['style'] != 'Other/uncertain': return first, [first]
    runs = [first] + [clean(ask(model, SYSTEM, lists, record), valid, self_id) for _ in range(2)]
    top, count = collections.Counter(r['style'] for r in runs).most_common(1)[0]
    if count < 2: return None, runs
    return next(r for r in runs if r['style'] == top), runs

def run_one(model, rid, shelf, want, lib, recs, ask=ask):
    r = recs[str(rid)]
    own = 'S%s' % rid if 'S%s' % rid in shelf else None
    lists = lists_text(shelf, lib, own)
    valid = set(k for k in shelf if k != own) | set(lib)
    t0 = time.time()
    try:
        rec, runs = recommend(model, lists, record_text(r), valid, own, ask)
        status = 'ok' if rec else 'unavailable: no majority style'
    except Exception as e:
        rec, runs, status = None, [], 'unavailable: %s' % e
    used = [x.pop('usage') for x in runs]
    return {'id': rid, 'artist': r['artist'], 'title': r['title'], 'status': status, 'attempts': max(len(runs), 1),
            'seconds': round(time.time() - t0, 1), 'result': rec,
            'cost': round(sum(u.get('cost') or 0 for u in used), 5),
            'tokens': {'prompt': sum(u.get('prompt_tokens') or 0 for u in used),
                       'completion': sum(u.get('completion_tokens') or 0 for u in used),
                       'cached': sum((u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0 for u in used)}}

def report(rows, expected):
    n = len(rows)
    ok = [x for x in rows if x['result']]
    specific = [x for x in ok if x['result']['style'] != 'Other/uncertain']
    scored = [x for x in specific if x['id'] in expected]
    right = [x for x in scored if x['result']['style'] == expected[x['id']]]
    secs = sorted(x['seconds'] for x in rows)
    print('\nrecords %d | recommendations available %d | specific style %d (target 18 of 20)' % (n, len(ok), len(specific)))
    if scored: print('style accuracy %d of %d (target 90%%)' % (len(right), len(scored)))
    else: print('style accuracy: no expected_style labels, not scored')
    print('no matches returned %d | median %.1fs | max %.1fs (timeout %ds)' % (
        sum(1 for x in ok if not x['result']['picks']), secs[len(secs) // 2], secs[-1], TIMEOUT))
    print('cost US$%.4f total, US$%.4f per record' % (sum(x['cost'] for x in rows), sum(x['cost'] for x in rows) / n))
    print('false close matches need your judgement: review the picks in the run file')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', choices=['primary', 'fallback'], default='primary')
    ap.add_argument('--ids'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    shelf, want, lib, recs = load_snapshots()
    es = json.load(open('data/eval_set.json')) if os.path.exists('data/eval_set.json') else [{'id': i} for i in want]
    ids = [int(i) for i in a.ids.split(',')] if a.ids else [e['id'] for e in es]
    expected = {e['id']: e['expected_style'] for e in es if e.get('expected_style')}
    model = PRIMARY if a.model == 'primary' else FALLBACK
    if a.dry_run:
        lists = lists_text(shelf, lib); r = recs[str(ids[0])]
        print('model %s | %d shelf, %d library | request %d chars\n\n%s\n\n%s' % (
            model, len(shelf), len(lib), len(lists), record_text(r), lists[:600] + ' ...')); return
    if not api_key(): sys.exit('No OpenRouter key. Add it with: security add-generic-password -a "$USER" -s crate-digger-openrouter -w')
    rows = []
    for rid in ids:
        x = run_one(model, rid, shelf, want, lib, recs); rows.append(x)
        print('%-9s %-40.40s %-32s %5.1fs %s' % (rid, x['artist'] + ' - ' + x['title'],
              x['result']['style'] if x['result'] else '-', x['seconds'], x['status']))
    report(rows, expected)
    os.makedirs('data/runs', exist_ok=True)
    path = 'data/runs/%s-%s.json' % (model.replace('/', '_'), time.strftime('%Y%m%d-%H%M%S'))
    json.dump({'model': model, 'rows': rows}, open(path, 'w'), ensure_ascii=False, indent=1)
    print('saved', path)

if __name__ == '__main__':
    main()
