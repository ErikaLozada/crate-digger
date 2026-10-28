import copy, csv, io, json, os, tempfile, threading, unittest, urllib.error, urllib.parse
from unittest import mock
import discogs_sync as sync
import discogs_write as dw


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def item(rid, instance=None, folder=1):
    d = {'basic_information': {'id': rid, 'title': 'Title %d' % rid, 'year': 1972,
         'artists': [{'name': 'Artist'}], 'labels': [{'name': 'Label', 'catno': 'ABC'}],
         'formats': [{'name': 'LP'}], 'master_id': 900, 'genres': ['Jazz'], 'styles': ['Fusion']},
         'rating': 4, 'date_added': '2026-10-01T12:00:00-07:00'}
    if instance is not None: d.update(instance_id=instance, folder_id=folder, notes=[{'field_id': 3, 'value': 'Note'}])
    else: d['notes'] = 'Wanted note'
    return d


class SyncTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        old = os.getcwd(); self.addCleanup(os.chdir, old); os.chdir(tmp.name); os.mkdir('data')
        self.col, self.want = 'data/collection.csv', 'data/wantlist.csv'
        with open(self.col, 'w', newline='') as f: csv.writer(f).writerows([sync.COL_HEADER, ['old'] * 7 + ['999']])
        with open(self.want, 'w', newline='') as f: csv.writer(f).writerows([sync.WANT_HEADER, ['old'] * 7 + ['998']])
        self.calls, self.failures = [], {}
        self.collection = [item(1, 11), item(1, 12, 2), item(2, 21)]
        self.wants = [item(3), item(4), item(5)]
        self.username = 'me'
        self.mutate = lambda path, data: data
        for p in [mock.patch.object(dw, 'COLLECTION_CSV', self.col), mock.patch.object(dw, 'WANTLIST_CSV', self.want),
                  mock.patch.object(sync, 'STATUS_PATH', 'data/discogs-sync.json'), mock.patch.object(dw, 'DRY', False),
                  mock.patch.object(dw, '_username', None), mock.patch.object(dw, '_token', return_value='SECRET'),
                  mock.patch('urllib.request.urlopen', self.urlopen), mock.patch.object(sync.time, 'sleep')]:
            p.start(); self.addCleanup(p.stop)

    def urlopen(self, req, timeout=0):
        path = urllib.parse.urlsplit(req.full_url).path
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
        self.calls.append((req.get_method(), req.full_url, req.headers))
        failure = self.failures.get(path)
        if isinstance(failure, list): failure = failure.pop(0) if failure else None
        if failure: raise failure
        if path == '/oauth/identity': d = {'username': self.username}
        elif path.endswith('/collection/folders'): d = {'folders': [{'id': 0, 'name': 'All'}, {'id': 1, 'name': 'Uncategorized'}, {'id': 2, 'name': 'Jazz'}]}
        else:
            key, rows = ('wants', self.wants) if path.endswith('/wants') else ('releases', self.collection)
            page = int(query['page'][0]); per = 2
            d = {'pagination': {'page': page, 'per_page': per, 'pages': max(1, (len(rows)+per-1)//per), 'items': len(rows)},
                 key: rows[(page-1)*per:page*per]}
        return Response(json.dumps(self.mutate(path, copy.deepcopy(d))).encode())

    def rows(self, path):
        with open(path, newline='') as f: return list(csv.DictReader(f))

    def files(self):
        return {p: open('data/'+p, 'rb').read() for p in os.listdir('data')}

    def test_all_pages_duplicates_folders_and_metadata(self):
        result = sync.sync()
        rows = self.rows(self.col)
        self.assertEqual([r['release_id'] for r in rows], ['1', '1', '2'])
        self.assertEqual([r['instance_id'] for r in rows], ['11', '12', '21'])
        self.assertEqual([r['CollectionFolder'] for r in rows], ['Uncategorized', 'Jazz', 'Uncategorized'])
        self.assertEqual(rows[0]['Collection Notes'], 'Note')
        self.assertEqual(json.loads(rows[0]['Genres']), ['Jazz'])
        self.assertEqual(json.loads(rows[0]['Styles']), ['Fusion'])
        self.assertEqual(rows[0]['master_id'], '900')
        self.assertEqual([r['release_id'] for r in self.rows(self.want)], ['3', '4', '5'])
        self.assertEqual(result['collection'], 3); self.assertEqual(result['wantlist'], 3)
        self.assertEqual(sync.status(), result)
        self.assertTrue(all(m == 'GET' and h['Authorization'] == 'Discogs token=SECRET' for m, _, h in self.calls))
        self.assertEqual(len([u for _, u, _ in self.calls if 'page=2' in u]), 2)
        self.assertNotIn('SECRET', json.dumps(result))

    def test_empty_lists_remove_previous_records(self):
        self.collection = []; self.wants = []
        result = sync.sync()
        self.assertEqual(self.rows(self.col), []); self.assertEqual(self.rows(self.want), [])
        self.assertEqual((result['collection'], result['wantlist']), (0, 0))

    def test_second_sync_reflects_remote_removals(self):
        sync.sync(); self.collection = self.collection[1:2]; self.wants = self.wants[:1]
        sync.sync()
        self.assertEqual([r['instance_id'] for r in self.rows(self.col)], ['12'])
        self.assertEqual(len(self.rows(self.want)), 1)

    def test_missing_caches_use_default_headers(self):
        os.unlink(self.col); os.unlink(self.want); sync.sync()
        self.assertEqual(self.rows(self.col)[0]['Title'], 'Title 1')
        self.assertEqual(self.rows(self.want)[0]['Date Added'], self.wants[0]['date_added'])

    def test_legacy_want_header_gains_named_date_column(self):
        with open(self.want, 'w') as f: f.write('release_id,Notes\n998,old\n')
        sync.sync()
        self.assertEqual(self.rows(self.want)[0]['Date Added'], self.wants[0]['date_added'])
        self.assertEqual(self.rows(self.want)[0]['Notes'], 'Wanted note')

    def test_failed_later_page_keeps_all_files_and_previous_status(self):
        sync.sync(); before = self.files()
        def fail_second(path, d):
            if path.endswith('/wants') and d['pagination']['page'] == 2: raise urllib.error.URLError('down')
            return d
        self.mutate = fail_second
        with self.assertRaises(dw.DiscogsError): sync.sync()
        self.assertEqual(self.files(), before)

    def test_invalid_token_does_not_retry_or_change_cache(self):
        before = self.files()
        self.failures['/oauth/identity'] = urllib.error.HTTPError('', 401, 'SECRET', {}, None)
        with self.assertRaises(dw.DiscogsError) as err: sync.sync()
        self.assertEqual(len(self.calls), 1); self.assertNotIn('SECRET', str(err.exception))
        self.assertEqual(self.files(), before)

    def test_missing_token_and_dry_run_have_no_side_effects(self):
        before = self.files()
        with mock.patch.object(dw, '_token', return_value=''):
            with self.assertRaises(dw.DiscogsError): sync.sync()
        with mock.patch.object(dw, 'DRY', True):
            with self.assertRaises(dw.DiscogsError): sync.sync()
        self.assertEqual(self.calls, []); self.assertEqual(self.files(), before)

    def test_rate_limit_retries_get_and_respects_retry_after(self):
        self.failures['/oauth/identity'] = [urllib.error.HTTPError('', 429, '', {'Retry-After': '3'}, None)]
        sync.sync()
        self.assertEqual(sum('/oauth/identity' in u for _, u, _ in self.calls), 2)
        sync.time.sleep.assert_any_call(3)

    def test_transient_retries_are_bounded_and_cache_is_unchanged(self):
        before = self.files(); self.failures['/oauth/identity'] = urllib.error.URLError('SECRET')
        with self.assertRaises(dw.DiscogsError) as err: sync.sync()
        self.assertEqual(len(self.calls), 3); self.assertEqual(self.files(), before)
        self.assertNotIn('SECRET', str(err.exception))

    def test_malformed_and_truncated_pages_leave_cache(self):
        for kind in ('missing', 'short', 'changed', 'duplicate', 'wrong-page'):
            before = self.files()
            def bad(path, d):
                if path.endswith('/wants'):
                    p = d['pagination']
                    if kind == 'missing': d.pop('pagination')
                    elif kind == 'short': d['wants'] = []
                    elif kind == 'changed' and p['page'] == 2: p['items'] += 1
                    elif kind == 'duplicate' and p['page'] == 2: d['wants'] = [self.wants[0]]
                    elif kind == 'wrong-page': p['page'] = 99
                return d
            self.mutate = bad
            with self.subTest(kind=kind), self.assertRaises(dw.DiscogsError): sync.sync()
            self.assertEqual(self.files(), before)

    def test_failed_cache_or_status_publication_rolls_back_pair(self):
        sync.sync()
        for failed_path in (self.want, sync.STATUS_PATH):
            before = self.files(); real_replace = os.replace; failed = []
            def replace(src, dst):
                if dst == failed_path and not failed:
                    failed.append(True); raise OSError('disk full')
                return real_replace(src, dst)
            with mock.patch.object(sync.os, 'replace', side_effect=replace):
                with self.assertRaises(dw.DiscogsError): sync.sync()
            self.assertEqual(self.files(), before)

    def test_failed_rollback_attempts_remaining_restores_and_keeps_recovery_file(self):
        sync.sync(); before = self.files(); self.collection = []; self.wants = []
        real_replace, calls = os.replace, {}
        def replace(src, dst):
            calls[dst] = calls.get(dst, 0) + 1
            if dst == sync.STATUS_PATH or dst == self.want and calls[dst] == 2:
                raise OSError('disk failure')
            return real_replace(src, dst)
        with mock.patch.object(sync.os, 'replace', side_effect=replace):
            with self.assertRaisesRegex(dw.DiscogsError, 'recovery failed'): sync.sync()
        self.assertEqual(open(self.col, 'rb').read(), before['collection.csv'])
        self.assertEqual(open(sync.STATUS_PATH, 'rb').read(), before['discogs-sync.json'])
        recovery = [p for p in os.listdir('data') if p.startswith('.discogs-sync-')]
        self.assertEqual(len(recovery), 1)
        self.assertEqual(open('data/' + recovery[0], 'rb').read(), before['wantlist.csv'])

    def test_failed_first_publication_does_not_create_empty_cache(self):
        os.unlink(self.col); os.unlink(self.want); before = self.files()
        with mock.patch.object(sync.os, 'replace', side_effect=OSError('disk full')):
            with self.assertRaises(dw.DiscogsError): sync.sync()
        self.assertEqual(self.files(), before)

    def test_malformed_status_returns_none(self):
        self.assertIsNone(sync.status())
        for data in ('{', '[]', '{"synced_at":"x","collection":true,"wantlist":0}'):
            with open(sync.STATUS_PATH, 'w') as f: f.write(data)
            self.assertIsNone(sync.status())

    def test_username_is_url_quoted(self):
        self.username = 'm\u00e9 /'; sync.sync()
        self.assertTrue(any('/users/m%C3%A9%20%2F/wants?' in u for _, u, _ in self.calls))

    def test_undo_after_sync_removes_exact_instance(self):
        sync.sync()
        with mock.patch.object(dw, '_call', return_value={}): dw.unbuy(1, 1, 11)
        self.assertEqual([r['instance_id'] for r in self.rows(self.col)], ['12', '21'])

    def test_buy_wishlist_and_undo_keep_synced_schema(self):
        sync.sync()
        def call(method, path, body=None):
            if path == '/oauth/identity': return {'username': 'me'}
            if method == 'POST': return {'instance_id': 100}
            if '/releases/' in path and method == 'GET': return item(77)['basic_information']
            return {}
        with mock.patch.object(dw, '_call', side_effect=call):
            dw.buy(77); dw.want(77)
            row = self.rows(self.col)[-1]; wanted = self.rows(self.want)[-1]
            self.assertEqual((row['instance_id'], row['folder_id']), ('100', '1'))
            self.assertTrue(wanted['Date Added']); self.assertNotIn(None, wanted)
            dw.unbuy(77, 1, 100); dw.unwant(77)
        self.assertEqual(len(self.rows(self.col)), 3); self.assertEqual(len(self.rows(self.want)), 3)

    def test_sync_waits_for_account_write_lock(self):
        entered, finished = threading.Event(), threading.Event()
        def run():
            entered.set(); sync.sync(); finished.set()
        with dw.DATA_LOCK:
            t = threading.Thread(target=run); t.start(); self.assertTrue(entered.wait(1))
            self.assertFalse(finished.wait(.03)); self.assertEqual(self.calls, [])
        t.join(2); self.assertTrue(finished.is_set())


if __name__ == '__main__': unittest.main()
