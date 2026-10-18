import os, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import grade


class GradeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.dir = tmp.name
        for k, v in {'TASKS': self.dir, 'LOG': os.path.join(self.dir, 'replays.md')}.items():
            p = mock.patch.object(grade, k, v); p.start(); self.addCleanup(p.stop)

    def test_brief_fields(self):
        with open(os.path.join(self.dir, 't.md'), 'w') as f:
            f.write('# Task: t\nBase: abc123\nReference: r1 r2\nScope: a.py tests/b.py\nCheck:\n\n## Goal\nScope: not this\n')
        self.assertEqual(grade.brief('t'), {'base': 'abc123', 'refs': ['r1', 'r2'], 'scope': {'a.py', 'tests/b.py'}, 'check': []})

    def test_review_fills_only_its_row(self):
        with open(grade.LOG, 'w') as f:
            f.write('| Run | Task | Agent | T | R | S | Review | Tokens |\n'
                    '| run-a | t | codex | pass | — | pass | pending | — |\n| run-b | t | claude | pass | — | pass | pending | — |\n')
        grade.review('run-b', 'fail', 'drops the edition dedupe')
        rows = open(grade.LOG).read().splitlines()
        self.assertIn('| pending |', rows[1])
        self.assertIn('| fail (drops the edition dedupe) |', rows[2])


if __name__ == '__main__':
    unittest.main()
