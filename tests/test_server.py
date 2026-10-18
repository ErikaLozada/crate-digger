import csv, io, json, os, tempfile, unittest, urllib.error
from unittest import mock

import build_compact, engine, harness, server


def raw_release(i, master=None):
    """The fields of a Discogs API release that compact() and build_compact read."""
    return {'id': i, 'title': 'Title %d' % i, 'year': 1970, 'master_id': master, 'artists_sort': 'Artist (2)',
            'artists': [{'id': 1, 'name': 'Artist', 'anv': '', 'join': ''}], 'tracklist': [], 'labels': [], 'formats': [],
            'community': {'have': 1, 'want': 2, 'rating': {'count': 3, 'average': 4.5}}, 'uri': 'https://discogs/%d' % i}


class InTempData(unittest.TestCase):
    """Runs each test in an empty folder with a data/ tree, since the code uses relative paths."""
    def setUp(self):
        self.addCleanup(os.chdir, os.getcwd())
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); os.chdir(tmp.name)
        for d in ('data/releases', 'data/masters', 'data/itunes'): os.makedirs(d)

    def write(self, path, data):
        with open(path, 'w') as f: json.dump(data, f)

    def read(self, path):
        with open(path) as f: return f.read()


class RefreshTests(InTempData):
    def setUp(self):
        super().setUp()
        with open('data/collection.csv', 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['Catalog#', 'Artist', 'Title', 'release_id']); w.writerows([['a', 'b', 'c', '1'], ['a', 'b', 'c', '2']])
        with open('data/wantlist.csv', 'w', newline='') as f:
            csv.writer(f).writerows([['h'] * 8, ['', '', '', '', '', '', '', '3'], ['', '', '', '', '', '', '', '1']])
        self.write('data/releases/1.json', raw_release(1))
        self.calls = []
        def get(url, discogs=False, timeout=10):
            self.calls.append(url)
            if '/releases/3' in url: raise urllib.error.HTTPError(url, 404, 'Not Found', {}, io.BytesIO())
            return {'id': 20, 'title': 'Master'} if '/masters/' in url else raw_release(2, master=20)
        patches = [mock.patch.object(server, 'get', get), mock.patch.object(server.time, 'sleep')]
        for p in patches: p.start(); self.addCleanup(p.stop)

    def test_fetches_only_records_without_details(self):
        added, failed = server.fetch_new()
        self.assertEqual(added, ['2'])
        self.assertFalse(any('/releases/1' in u for u in self.calls))
        self.assertTrue(os.path.exists('data/releases/2.json') and os.path.exists('data/masters/20.json'))
        self.assertEqual(self.read('release_ids.txt'), '2\n')

    def test_no_apple_lookup(self):
        server.fetch_new()
        self.assertFalse(any('itunes' in u for u in self.calls))

    def test_record_missing_on_discogs_is_saved_and_reported(self):
        added, failed = server.fetch_new()
        self.assertEqual(json.loads(self.read('data/releases/3.json')), {'missing': True})
        self.assertTrue(failed and failed[0].startswith('3 '))

    def test_second_refresh_fetches_nothing(self):
        server.fetch_new(); self.calls.clear()
        self.assertEqual(server.fetch_new(), ([], []))
        self.assertEqual(self.calls, [])


class BuildCompactTests(InTempData):
    def test_skips_missing_and_keeps_old_shape(self):
        r = raw_release(1, master=10); r['videos'] = [{'uri': 'v%d' % n, 'title': ''} for n in range(5)]
        r['series'] = [{'id': 7, 'name': 'Series', 'catno': 'S1'}]
        self.write('data/releases/1.json', r)
        self.write('data/releases/2.json', {'missing': True})
        self.write('data/masters/10.json', {'id': 10, 'title': 'M', 'artists': [{'id': 1, 'name': 'Artist'}]})
        out = build_compact.build(server.compact)
        self.assertEqual(list(out['releases']), ['1'])
        rel = out['releases']['1']
        self.assertEqual((len(rel['videos']), rel['nvideos']), (3, 5))
        self.assertEqual(rel['series'], [[7, 'Series']])
        self.assertEqual(out['masters']['10']['artists'], [[1, 'Artist']])


class SavedAnswerTests(unittest.TestCase):
    shelf = {'S1': {'artist': 'A', 'title': 'T', 'year': 1970, 'family': 'Pop rock', 'styles': []}}
    lib = {'L1': {'artist': 'B', 'album': 'U', 'year': 1980, 'genre': 'Jazz', 'plays': 3, 'liked': 1}}
    recs = {'2': {'artist': 'C', 'title': 'V', 'year': 1990, 'label': 'L', 'country': 'AU', 'genres': [], 'styles': []}}

    def key(self, model='m', shelf=None, lib=None):
        return server.request_key(model, 2, shelf or self.shelf, lib or self.lib, self.recs)

    def test_same_request_same_key(self):
        self.assertEqual(self.key(), self.key())

    def test_any_change_asks_again(self):
        more = dict(self.lib, L2={**self.lib['L1'], 'album': 'W'})
        played = {'L1': {**self.lib['L1'], 'plays': 4}}
        self.assertEqual(len({self.key(), self.key(model='other'), self.key(lib=more), self.key(lib=played)}), 4)

    def test_prompt_change_asks_again(self):
        before = self.key()
        with mock.patch.object(harness, 'SYSTEM', harness.SYSTEM + ' changed'):
            self.assertNotEqual(self.key(), before)


class CleanPicksTests(unittest.TestCase):
    def test_drops_unknown_self_and_repeats_and_keeps_three(self):
        ans = {'sentence': 's', 'style': 'x', 'picks': [{'id': i, 'reason': ''} for i in ['L9', 'S1', 'L1', 'L1', 'L2', 'L3', 'L4']]}
        out = harness.clean(ans, {'S1', 'L1', 'L2', 'L3', 'L4'}, 'S1')
        self.assertEqual([p['id'] for p in out['picks']], ['L1', 'L2', 'L3'])


def rec(i, leader, players=(), labels=(), producers=(), master=None, year=1970):
    """A shelf Rec built through compact(): leader (id, name), players [(id, name, role)], labels [(id, name)]."""
    r = raw_release(i, master)
    r.update(year=year, title='Title %d' % i, artists_sort=leader[1],
             artists=[{'id': leader[0], 'name': leader[1], 'anv': '', 'join': ''}],
             extraartists=[{'id': p, 'name': n, 'role': role, 'tracks': ''} for p, n, role in players]
                          + [{'id': p, 'name': n, 'role': 'Producer', 'tracks': ''} for p, n in producers],
             labels=[{'id': l, 'name': n, 'catno': 'X%d' % i} for l, n in labels])
    return engine.Rec(server.compact(r), {}, 'shelf', None)


class ShelfLinksTests(unittest.TestCase):
    BN = (5, 'Blue Note')

    def test_empty_when_nothing_shared(self):
        t = rec(1, (10, 'A'), [(11, 'B', 'Bass')])
        self.assertEqual(engine.shelf_links(t, [rec(2, (20, 'C'), [(21, 'D', 'Drums')])]),
                         {'artists': [], 'musicians': [], 'producers': [], 'labels': []})

    def test_artist_exclusions_dedupe_and_record_order(self):
        t = rec(1, (10, 'A'), master=100)
        shelf = [t, rec(2, (10, 'A'), master=100),
                 rec(3, (10, 'A'), master=200, year=1980),
                 rec(4, (10, 'A'), master=200, year=1990),
                 rec(5, (10, 'A'), year=1960), rec(6, (10, 'A'), year=1970),
                 rec(7, (10, 'A'), year=0),
                 rec(8, (20, 'Other'), [(10, 'A', 'Piano')])]
        shelf.append(shelf[4])
        out = engine.shelf_links(t, shelf)
        self.assertEqual(out['artists'], [{'name': 'A', 'count': 4, 'records': [
            {'id': 5, 'artist': 'A', 'title': 'Title 5', 'year': 1960},
            {'id': 6, 'artist': 'A', 'title': 'Title 6', 'year': 1970},
            {'id': 3, 'artist': 'A', 'title': 'Title 3', 'year': 1980}]}])
        self.assertEqual([r['id'] for r in out['musicians'][0]['records']], [8])

    def test_multiple_lead_artists_order_and_limit(self):
        t = rec(1, (10, 'Z'))
        t.main = {10: 'Z', 11: 'B', 12: 'A', 13: 'C'}
        shelf = []
        for i, name in t.main.items():
            shelf.extend(rec(i * 10 + j, (i, name)) for j in range(3 if name == 'Z' else 2))
        out = engine.shelf_links(t, shelf)
        self.assertEqual([(e['name'], e['count']) for e in out['artists']],
                         [('Z', 3), ('A', 2), ('B', 2)])
        self.assertEqual(out['musicians'], [])
        o = rec(99, (10, 'Z'))
        o.main = t.main.copy()
        self.assertEqual([e['name'] for e in engine.shelf_links(t, [o])['artists']], ['A', 'B', 'C'])

    def test_musician_role_and_record(self):
        t = rec(1, (10, 'Donald Byrd'), [(11, 'Herbie Hancock', 'Piano')])
        o = rec(2, (20, 'Wayne Shorter'), [(11, 'Herbie Hancock', 'Keyboards')], year=1966)
        m = engine.shelf_links(t, [o])['musicians']
        self.assertEqual(m, [{'name': 'Herbie Hancock', 'role': 'Piano', 'count': 1,
                              'records': [{'id': 2, 'artist': 'Wayne Shorter', 'title': 'Title 2', 'year': 1966}]}])

    def test_role_from_shelf_when_leader_of_inspected(self):
        t = rec(1, (10, 'Lee Morgan'))
        o = rec(2, (20, 'Art Blakey'), [(10, 'Lee Morgan', 'Trumpet')])
        self.assertEqual(engine.shelf_links(t, [o])['musicians'][0]['role'], 'Trumpet')

    def test_excludes_self_and_other_editions_and_dedupes_albums(self):
        p = [(11, 'B', 'Bass')]
        t = rec(1, (10, 'A'), p, labels=[self.BN], master=100)
        shelf = [t, rec(2, (10, 'A'), p, labels=[self.BN], master=100),           # same album, other edition
                 rec(3, (20, 'C'), p, labels=[self.BN], master=200, year=1960),
                 rec(4, (20, 'C'), p, labels=[self.BN], master=200, year=1990),   # second edition of album 200
                 rec(5, (30, 'D'), p, labels=[self.BN])]
        out = engine.shelf_links(t, shelf)
        self.assertEqual([(x['count'], [r['id'] for r in x['records']]) for x in out['musicians']], [(2, [3, 5])])
        self.assertEqual(out['labels'][0]['count'], 2)

    def test_ordering_and_limits(self):
        t = rec(1, (10, 'Leader'), [(10 + k, 'P%d' % k, 'Sax') for k in range(1, 9)],
                labels=[(5, 'L1'), (6, 'L2'), (7, 'L3'), (8, 'Columbia')], producers=[(90 + k, 'Pr%d' % k) for k in range(4)])
        shelf = []
        for j in range(4):    # P1 on 4 records, P2 on 3, ... ; leader 10 plays as sideman on record 2
            players = [(10 + k, 'P%d' % k, 'Sax') for k in range(1, 9) if k <= 4 - j or k > 4]
            if j == 0: players.append((10, 'Leader', 'Flute'))
            shelf.append(rec(2 + j, (50 + j, 'S%d' % j), players, labels=[(5, 'L1'), (6, 'L2'), (7, 'L3'), (8, 'Columbia')][:4 - j],
                             producers=[(90 + k, 'Pr%d' % k) for k in range(4)], year=1980 - j))
        out = engine.shelf_links(t, shelf)
        self.assertEqual([m['name'] for m in out['musicians']], ['Leader', 'P1', 'P5', 'P6', 'P7', 'P8'])
        self.assertEqual(out['musicians'][0]['role'], 'Flute')
        self.assertEqual([r['year'] for r in out['musicians'][1]['records']], [1977, 1978, 1979])
        self.assertEqual(len(out['producers']), 3)
        self.assertEqual([(l['name'], l['count']) for l in out['labels']], [('L1', 4), ('L2', 3)])

    def test_release_always_has_links(self):
        server.SHELF, server.SHELF_IDS, server.LIB = [], set(), []
        raw = raw_release(1)
        raw.update(images=[], videos=[], tracklist=[])
        with mock.patch.object(server, 'fetch_release', return_value=(raw, {}, True)):
            self.assertEqual(server.release(1)['links'], {'artists': [], 'musicians': [], 'producers': [], 'labels': []})


if __name__ == '__main__':
    unittest.main()
