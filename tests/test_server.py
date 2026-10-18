import csv, io, json, os, tempfile, unittest, urllib.error
from unittest import mock

import build_compact, harness, server


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


if __name__ == '__main__':
    unittest.main()
