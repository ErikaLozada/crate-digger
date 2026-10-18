"""Grades a replayed task against its reviewed reference (docs/tasks/<task>.md), for choosing worker models.

  python3 scripts/grade.py golden <task>                 save the reference's links output for the brief's Check ids
  python3 scripts/grade.py run <task> <folder>           gates 1-4 on a replay folder; appends to docs/tasks/replays.md
  python3 scripts/grade.py diff <folder>                 the change to review, without saying who made it (gate 5)
  python3 scripts/grade.py review <run> pass|fail "note" record the blind review

Gates: 1 hidden tests (the reference's test files) pass, 2 the whole suite passes, 3 links output equals the golden
file, 4 only files in Scope changed, 5 a blind review finds no correctness bug. Cost and size are measured, not gated.
"""
import glob, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS, LOG = os.path.join(ROOT, 'docs', 'tasks'), os.path.join(ROOT, 'docs', 'tasks', 'replays.md')
OWN = {'recommendations.json', 'deploys.log'}             # written by the live app; never shared
SNIPPET = r'''
import json, sys, server
def offline(*a, **k): raise OSError("offline")             # saved Discogs data only, so runs are repeatable
server.get = offline
server.load()
print(json.dumps({i: server.release(int(i)).get("links") for i in sys.argv[1:]}, sort_keys=True))
'''

def sh(*cmd, cwd=ROOT, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode: sys.exit('failed: %s\n%s' % (' '.join(cmd), r.stdout + r.stderr))
    return r

def brief(task):
    text = open(os.path.join(TASKS, task + '.md'), encoding='utf-8').read()
    field = lambda k: (re.search(r'^%s:[ \t]*(.*)$' % k, text, re.M) or [None, ''])[1].split()
    return {'base': field('Base')[0], 'refs': field('Reference'), 'scope': set(field('Scope')), 'check': field('Check'),
            'hidden': (field('Hidden') or ['yes'])[0] != 'none'}

def link_data(folder):
    """Symlink the main copy's untracked data into a checkout, as make task does."""
    os.makedirs(os.path.join(folder, 'data'), exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'data')):
        dst = os.path.join(folder, 'data', f)
        if f not in OWN and not os.path.exists(dst): os.symlink(os.path.join(ROOT, 'data', f), dst)
    tok = os.path.join(ROOT, 'discogs_token.txt')
    if os.path.exists(tok) and not os.path.exists(os.path.join(folder, 'discogs_token.txt')):
        os.symlink(tok, os.path.join(folder, 'discogs_token.txt'))

def links_output(folder, ids):
    r = sh(sys.executable, '-c', SNIPPET, *ids, cwd=folder, check=False)
    lines = r.stdout.strip().splitlines()
    try: return json.loads(lines[-1])
    except (IndexError, ValueError): return {'error': (r.stderr or r.stdout)[-300:]}

def same_links(gold, out):
    """Equal, except that records sharing an original year may come in either order: briefs say "oldest first"
    without a tie rule, so which of two same-year albums fills the last slot is not part of the contract."""
    shape = lambda d: {rid: {k: [{**e, 'records': [r['year'] for r in e['records']]} for e in es] for k, es in v.items()}
                       for rid, v in d.items()} if isinstance(d, dict) and 'error' not in d else d
    return shape(gold) == shape(out)

def golden(task):
    b = brief(task)
    if not b['check']: print('%s has no Check ids: nothing to save' % task); return
    with tempfile.TemporaryDirectory() as tmp:
        ref = os.path.join(tmp, 'ref')
        sh('git', 'worktree', 'add', '-q', '--detach', ref, b['refs'][-1])
        try:
            link_data(ref); out = links_output(ref, b['check'])
        finally:
            sh('git', 'worktree', 'remove', '--force', ref)
    if 'error' in out: sys.exit('reference failed: %s' % out['error'])
    os.makedirs(os.path.join(TASKS, 'golden'), exist_ok=True)
    json.dump(out, open(os.path.join(TASKS, 'golden', task + '.json'), 'w'), indent=1, sort_keys=True, ensure_ascii=False)
    print('saved docs/tasks/golden/%s.json for %s' % (task, ', '.join(b['check'])))

def changed_files(folder, base):
    tracked = sh('git', 'diff', '--name-only', base, cwd=folder).stdout.split()
    new = [l[3:] for l in sh('git', 'status', '--porcelain', cwd=folder).stdout.splitlines() if l.startswith('?? ')]
    return {f for f in tracked + new if f != 'TASK.md' and not os.path.islink(os.path.join(folder, f.rstrip('/')))}

def tokens(folder):
    """What the worker spent, read from its agent's own session files."""
    folder = os.path.realpath(folder)
    for p in sorted(glob.glob(os.path.expanduser('~/.codex/sessions/**/rollout-*.jsonl'), recursive=True), key=os.path.getmtime, reverse=True):
        rows = [json.loads(l) for l in open(p, encoding='utf-8')]
        if rows and rows[0].get('payload', {}).get('cwd') == folder:
            last = [r['payload']['info'] for r in rows if r.get('payload', {}).get('type') == 'token_count' and r['payload'].get('info')]
            u = last[-1]['total_token_usage'] if last else {}
            return {'input': u.get('input_tokens', 0), 'cached': u.get('cached_input_tokens', 0), 'output': u.get('output_tokens', 0)}
    t = {'input': 0, 'cached': 0, 'output': 0}
    for p in glob.glob(os.path.expanduser('~/.claude/projects/%s/*.jsonl' % re.sub(r'[^A-Za-z0-9]', '-', folder))):
        for l in open(p, encoding='utf-8'):
            u = (json.loads(l).get('message') or {}).get('usage') if '"usage"' in l else None
            if isinstance(u, dict):
                t['input'] += u.get('input_tokens', 0) + u.get('cache_creation_input_tokens', 0)
                t['cached'] += u.get('cache_read_input_tokens', 0); t['output'] += u.get('output_tokens', 0)
    return t if any(t.values()) else None

def run(task, folder):
    b, folder = brief(task), os.path.abspath(folder)
    with tempfile.TemporaryDirectory() as tmp:                # gates 1-2 on a copy with the hidden tests put in
        work = os.path.join(tmp, 'w')
        shutil.copytree(folder, work, symlinks=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        hidden = [] if not b['hidden'] else sorted({f for c in b['refs'] for f in sh('git', 'diff', '--name-only', c + '^', c).stdout.split() if f.startswith('tests/')})
        for f in hidden:
            r = sh('git', 'show', '%s:%s' % (b['refs'][-1], f), check=False)
            if r.returncode == 0: open(os.path.join(work, f), 'w', encoding='utf-8').write(r.stdout)
        t = subprocess.run(['bash', '-c', 'python3 -W ignore::ResourceWarning -m unittest discover tests 2>&1 | tail -3; '
                            'exit ${PIPESTATUS[0]}'], cwd=work, capture_output=True, text=True)
        n = subprocess.run(['bash', '-c', 'node --test tests/*.test.cjs 2>&1 | grep -E "^. (pass|fail) "; exit ${PIPESTATUS[0]}'],
                           cwd=work, capture_output=True, text=True) if glob.glob(os.path.join(work, 'tests', '*.test.cjs')) else None
    tests_ok = t.returncode == 0 and (n is None or n.returncode == 0)
    gold_path = os.path.join(TASKS, 'golden', task + '.json')
    if b['check']:
        gold = json.load(open(gold_path, encoding='utf-8')) if os.path.exists(gold_path) else None
        golden_ok = gold is not None and same_links(gold, links_output(folder, b["check"]))
    else:
        golden_ok = None
    outside = sorted(changed_files(folder, b['base']) - b['scope'])
    agent = next((l.split(':', 1)[1].split(';')[0].strip() for l in open(os.path.join(folder, 'TASK.md'), encoding='utf-8')
                  if l.startswith('Agent:')), 'reference') if os.path.exists(os.path.join(folder, 'TASK.md')) else 'reference'
    tok = tokens(folder)
    mark = lambda ok: '—' if ok is None else ('pass' if ok else 'FAIL')
    row = [os.path.basename(folder), task, agent, mark(tests_ok), mark(golden_ok), mark(not outside), 'pending',
           ('%(input)d in, %(cached)d cached, %(output)d out' % tok) if tok else '—']
    if not os.path.exists(LOG):
        open(LOG, 'w').write('# Replays\n\nGenerated by `scripts/grade.py`. Review is filled in by `grade.py review` after a blind look at `grade.py diff`.\n\n'
                             '| Run | Task | Agent | Tests (gates 1-2) | Real data (3) | Scope (4) | Review (5) | Tokens |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n')
    open(LOG, 'a').write('| ' + ' | '.join(row) + ' |\n')
    print('tests: %s\n%s%s' % (mark(tests_ok), t.stdout.strip(), ('\n' + n.stdout.strip()) if n else ''))
    print('real data: %s | scope: %s%s | tokens: %s' % (mark(golden_ok), mark(not outside), (' (outside: %s)' % ', '.join(outside)) if outside else '', row[-1]))

def diff(folder):
    base = next(l.split(':', 1)[1].strip() for l in open(os.path.join(folder, 'TASK.md'), encoding='utf-8') if l.startswith('Base:'))
    sh('git', 'add', '-N', '.', cwd=folder, check=False)      # show new files too, without staging them
    print(sh('git', 'diff', base, '--', '.', ':(exclude)TASK.md', cwd=folder).stdout)

def review(run_id, verdict, note=''):
    lines = open(LOG, encoding='utf-8').read().splitlines()
    for i, l in enumerate(lines):
        cells = l.split(' | ')
        if l.startswith('| %s |' % run_id) and len(cells) == 8:
            cells[6] = verdict + (' (%s)' % note if note else ''); lines[i] = ' | '.join(cells)
            open(LOG, 'w', encoding='utf-8').write('\n'.join(lines) + '\n'); print('recorded'); return
    sys.exit('no run %s in %s' % (run_id, LOG))

if __name__ == '__main__':
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ('', [])
    {'golden': golden, 'run': run, 'diff': diff, 'review': review}.get(cmd, lambda *a: sys.exit(__doc__))(*args)
