import csv, io, json, os, sys, tempfile, unittest, urllib.error
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discogs_write as dw

COL = 'Catalog#,Artist,Title,Label,Format,Rating,Released,release_id,CollectionFolder,Date Added,Collection Media Condition,Collection Sleeve Condition,Collection Notes\n'
WANT = 'Catalog#,Artist,Title,Label,Format,Rating,Released,release_id,Notes\n9012-1,E.S.T.,Seven Days,ACT,LP,,2018,5,,2026-07-05 23:13:30\n'
REL = {'id': 77, 'title': 'Return To Forever', 'year': 1972, 'artists': [{'name': 'Chick Corea'}],
       'labels': [{'name': 'ECM', 'catno': 'ECM 1022'}, {'name': 'ECM', 'catno': 'x'}],
       'formats': [{'name': 'LP', 'qty': '1', 'descriptions': ['Album']}]}

class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass

class T(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.col, self.want = os.path.join(d, 'c.csv'), os.path.join(d, 'w.csv')
        open(self.col, 'w').write(COL); open(self.want, 'w').write(WANT)
        self.calls = []
        for p in [mock.patch.object(dw, 'COLLECTION_CSV', self.col), mock.patch.object(dw, 'WANTLIST_CSV', self.want),
                  mock.patch.object(dw, 'DRY', False), mock.patch.object(dw, '_username', None),
                  mock.patch.object(dw, '_token', return_value='SECRET'), mock.patch('urllib.request.urlopen', self.urlopen)]:
            p.start(); self.addCleanup(p.stop)
        self.fail_on = None

    def urlopen(self, req, timeout=0):
        self.calls.append((req.get_method(), req.full_url.replace(dw.API, ''), req.headers))
        path = req.full_url
        if self.fail_on and self.fail_on in path: raise urllib.error.HTTPError(path, 403, 'x', {}, None)
        if path.endswith('/oauth/identity'): return Resp(b'{"username":"me"}')
        if '/releases/77' in path and req.get_method() == 'GET': return Resp(json.dumps(REL).encode())
        if req.get_method() == 'POST': return Resp(b'{"instance_id": 123}')
        return Resp(b'')

    def rows(self, p): return list(csv.reader(open(p)))

    def test_buy_adds_row_and_returns_instance(self):
        self.assertEqual(dw.buy(77), {'folder_id': 1, 'instance_id': 123})
        self.assertIn(('POST', '/users/me/collection/folders/1/releases/77'), [c[:2] for c in self.calls])
        r = self.rows(self.col)[-1]
        self.assertEqual(r[:5], ['ECM 1022', 'Chick Corea', 'Return To Forever', 'ECM', 'LP, Album'])
        self.assertEqual((r[6], r[7], r[8]), ('1972', '77', 'Uncategorized'))
        self.assertEqual(len(r), 13)
        self.assertEqual(self.calls[0][2]['Authorization'], 'Discogs token=SECRET')

    def test_buy_keeps_an_id_only_row_when_release_details_fail(self):
        def details_down(req, timeout=0):                   # the POST ends in /releases/77 too, so fail only the GET
            if req.get_method() == 'GET' and req.full_url.endswith('/releases/77'): raise urllib.error.URLError('down')
            return self.urlopen(req, timeout)
        with mock.patch('urllib.request.urlopen', details_down):
            self.assertEqual(dw.buy(77)['instance_id'], 123)
        r = self.rows(self.col)[-1]
        self.assertEqual((r[1], r[7], r[8]), ('', '77', 'Uncategorized'))

    def test_csv_failure_after_discogs_success_is_logged_not_raised(self):
        err = io.StringIO()
        dw.buy(77)                                          # a row to remove
        with mock.patch.object(dw, '_write', side_effect=OSError('disk full')), mock.patch.object(sys, 'stderr', err):
            self.assertEqual(dw.buy(77), {'folder_id': 1, 'instance_id': 123})
            self.assertEqual(dw.want(77), {})
            self.assertIsNone(dw.unbuy(77, 1, 123)); self.assertIsNone(dw.unwant(5))
        self.assertEqual(err.getvalue().count('disk full'), 4)

    def test_unbuy_removes_row(self):
        dw.buy(77); self.calls.clear()
        dw.unbuy(77, 1, 123)
        self.assertEqual(self.calls[-1][:2], ('DELETE', '/users/me/collection/folders/1/releases/77/instances/123'))
        self.assertEqual(len(self.rows(self.col)), 1)

    def test_want_and_unwant_keep_header_and_columns(self):
        dw.want(77)
        rows = self.rows(self.want)
        self.assertEqual(rows[0], WANT.split('\n')[0].split(','))
        self.assertEqual(rows[-1][:8], ['ECM 1022', 'Chick Corea', 'Return To Forever', 'ECM', 'LP, Album', '', '1972', '77'])
        self.assertEqual(len(rows[-1]), 10)
        self.assertIn(('PUT', '/users/me/wants/77'), [c[:2] for c in self.calls])
        dw.unwant(77)
        self.assertEqual(self.calls[-1][:2], ('DELETE', '/users/me/wants/77'))
        self.assertEqual([r[7] for r in self.rows(self.want)[1:]], ['5'])

    def test_username_cached(self):
        dw.buy(77); dw.want(77)
        self.assertEqual(sum(c[1] == '/oauth/identity' for c in self.calls), 1)

    def test_http_error_raises_without_token_and_leaves_files(self):
        self.fail_on = '/collection/'
        with self.assertRaises(dw.DiscogsError) as e: dw.buy(77)
        self.assertNotIn('SECRET', str(e.exception))
        self.assertEqual(len(self.rows(self.col)), 1)

    def test_network_failure(self):
        with mock.patch('urllib.request.urlopen', side_effect=urllib.error.URLError('down')):
            with self.assertRaises(dw.DiscogsError): dw.want(77)

    def test_no_token(self):
        with mock.patch.object(dw, '_token', return_value=''):
            with self.assertRaises(dw.DiscogsError): dw.buy(77)

    def test_dry_run_touches_nothing(self):
        with mock.patch.object(dw, 'DRY', True):
            b = dw.buy(77); dw.unbuy(77, 1, b['instance_id']); self.assertEqual(dw.want(77), {}); dw.unwant(77)
        self.assertEqual(self.calls, [])
        self.assertEqual(open(self.col).read(), COL)
        self.assertEqual(open(self.want).read(), WANT)

if __name__ == '__main__': unittest.main()
