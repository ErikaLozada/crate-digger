import importlib.util, json, os, tempfile, unittest

spec = importlib.util.spec_from_file_location('watch_codex', os.path.join(os.path.dirname(__file__), '..', 'scripts', 'watch-codex.py'))
watch = importlib.util.module_from_spec(spec); spec.loader.exec_module(watch)


def rec(type_, **payload): return json.dumps({'type': type_, 'payload': payload}) + '\n'

class WatchCodexTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root = tmp.name
        os.makedirs(os.path.join(self.root, '2026', '10', '18'))
        self.path = os.path.join(self.root, '2026', '10', '18', 'rollout-2026-10-18T18-31-37-abc.jsonl')
        self.append(rec('session_meta', id='abc', cwd='/proj'), rec('event_msg', type='task_complete', last_agent_message='old'))
        self.out = []

    def append(self, *lines):
        with open(self.path, 'a', encoding='utf-8') as f: f.writelines(lines)

    def run_watch(self, offset, follow=False, timeout=0.05):
        return watch.replies(self.path, offset, timeout, follow, poll=0.01, out=self.out.append)

    def test_finds_session_by_folder_or_thread(self):
        self.assertEqual(watch.find_session(cwd='/proj', root=self.root), self.path)
        self.assertEqual(watch.find_session(thread='abc', root=self.root), self.path)
        self.assertIsNone(watch.find_session(cwd='/other', root=self.root))

    def test_reports_only_the_finished_turn_after_the_mark(self):
        mark = os.path.getsize(self.path)
        self.append(rec('response_item', type='message', role='assistant', content=[{'text': "I'll check"}]),
                    rec('response_item', type='custom_tool_call'), rec('event_msg', type='token_count'),
                    rec('event_msg', type='task_complete', last_agent_message='Acknowledged'))
        self.assertEqual(self.run_watch(mark), 0)
        self.assertEqual(self.out, ['CODEX: Acknowledged'])

    def test_fast_reply_written_before_watching_starts_is_not_missed(self):
        mark = os.path.getsize(self.path)              # marked before sending, as main() does
        self.append(rec('event_msg', type='task_complete', last_agent_message='fast'))
        self.run_watch(mark)
        self.assertEqual(self.out, ['CODEX: fast'])

    def test_silence_is_reported_as_timeout(self):
        self.assertEqual(self.run_watch(os.path.getsize(self.path)), 1)
        self.assertTrue(self.out[0].startswith('WATCH TIMEOUT'))

    def test_unreadable_line_is_reported(self):
        mark = os.path.getsize(self.path); self.append('not json\n')
        self.assertEqual(self.run_watch(mark), 2)
        self.assertTrue(self.out[0].startswith('WATCH ERROR'))

    def test_half_written_line_waits_for_the_rest(self):
        mark = os.path.getsize(self.path); line = rec('event_msg', type='task_complete', last_agent_message='done')
        self.append(line[:20]); self.run_watch(mark)
        self.assertEqual(self.out[-1][:13], 'WATCH TIMEOUT')

    def test_follow_reports_every_turn(self):
        mark = os.path.getsize(self.path)
        self.append(rec('event_msg', type='task_complete', last_agent_message='one'), rec('event_msg', type='task_complete', last_agent_message='two'))
        self.run_watch(mark, follow=True)
        self.assertEqual(self.out[:2], ['CODEX: one', 'CODEX: two'])


if __name__ == '__main__':
    unittest.main()
