import sys, os, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import report


def run(*picks_per_record):
    return {'model': 'm', 'rows': [
        {'id': i, 'artist': 'A', 'title': str(i), 'seconds': 5.0, 'cost': 0.001,
         'result': {'style': 'Pop rock', 'picks': [{'id': 'L1', 'reason': r} for r in picks]}}
        for i, picks in enumerate(picks_per_record)]}

def review(false, *picks_per_record):
    return [{'model': 'm', 'id': i, 'false_match': i in false, 'picks': ['X — Y [library] — %s' % r for r in picks]}
            for i, picks in enumerate(picks_per_record)]


class ReportTests(unittest.TestCase):
    labels = {0: {'expected_style': 'Pop rock'}, 1: {'expected_style': 'Folk & country', 'close_match_known': False}}

    def test_review_matched_to_its_run_by_picks(self):
        r = run(['close'], ['loose'])
        name, verdicts = report.reviewed_by(r, [('old.json', review({0}, ['other'], ['loose'])), ('new.json', review({1}, ['close'], ['loose']))])
        self.assertEqual(name, 'new.json')
        self.assertTrue(verdicts[1]['false_match'])

    def test_unreviewed_run_has_no_false_match_count(self):
        s = report.score(run(['close'], ['loose']), self.labels, [('r.json', review(set(), ['different'], ['loose']))])
        self.assertIsNone(s['false'])

    def test_scores(self):
        s = report.score(run(['close'], []), self.labels, [('r.json', review(set(), ['close'], []))])
        self.assertEqual((s['right'], s['scored'], s['nothing_close'], s['no_close'], len(s['false'])), (1, 2, 1, 1, 0))

    def test_uncertain_style_is_left_out_of_accuracy(self):
        r = run(['close'], ['loose']); r['rows'][1]['result']['style'] = 'Other/uncertain'
        s = report.score(r, self.labels, [])
        self.assertEqual((s['right'], s['scored'], s['specific']), (1, 1, 1))


if __name__ == '__main__':
    unittest.main()
