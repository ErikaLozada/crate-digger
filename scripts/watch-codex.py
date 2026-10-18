"""Send a message to a Codex session and/or wait for its reply. Uses no model: it only reads Codex's session file.

  python3 scripts/watch-codex.py --send "message"     queue a message, print Codex's reply when its turn ends
  python3 scripts/watch-codex.py --follow             print every reply until stopped (for a Claude Monitor)

The session defaults to the newest Codex session started in this folder; pass --thread <id> to pick one.
Prints one line per reply ("CODEX: ..."). Problems are printed too ("WATCH ERROR/TIMEOUT: ..."), never silence:
the session file is Codex's internal format and may change with a Codex update.
"""
import argparse, glob, json, os, subprocess, sys, time

SESSIONS = os.path.expanduser('~/.codex/sessions')

def meta(path):
    with open(path, encoding='utf-8') as f:
        first = json.loads(f.readline() or '{}')
    return first.get('payload', {}) if first.get('type') == 'session_meta' else {}

def find_session(thread=None, cwd=None, root=SESSIONS):
    """Path of the session file for a thread id, or of the newest session whose folder is cwd."""
    files = sorted(glob.glob(os.path.join(root, '**', 'rollout-*.jsonl'), recursive=True), key=os.path.getmtime, reverse=True)
    for p in files:
        if (thread and p.endswith('-%s.jsonl' % thread)) or (not thread and meta(p).get('cwd') == cwd):
            return p
    return None

def replies(path, offset, timeout, follow, poll=1.0, out=print):
    """Report each turn Codex finishes after byte offset. Returns 0 on a reply, 1 on timeout, 2 on an unreadable file."""
    end, buf = time.time() + timeout, ''
    while time.time() < end:
        with open(path, encoding='utf-8') as f:
            f.seek(offset); chunk = f.read(); offset = f.tell()
        buf += chunk
        *lines, buf = buf.split('\n')                     # the last piece may be a line still being written
        for line in filter(None, lines):
            try:
                x = json.loads(line)
            except ValueError:
                out('WATCH ERROR: a line in %s is not JSON; the Codex file format may have changed' % path); return 2
            p = x.get('payload') or {}
            if x.get('type') == 'event_msg' and p.get('type') == 'task_complete':
                out('CODEX: %s' % (p.get('last_agent_message') or '(turn ended without a message)'))
                if not follow: return 0
        time.sleep(poll)
    out('WATCH TIMEOUT: Codex finished no turn in %d s. Is its session idle in a terminal? It may need a keypress there.' % timeout)
    return 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--thread'); ap.add_argument('--send'); ap.add_argument('--follow', action='store_true')
    ap.add_argument('--timeout', type=int, default=600)
    a = ap.parse_args()
    path = find_session(a.thread, os.getcwd())
    if not path: print('WATCH ERROR: no Codex session found for %s' % (a.thread or os.getcwd())); return 2
    thread = a.thread or meta(path).get('id')
    offset = os.path.getsize(path)                        # mark the end BEFORE sending, so a fast reply can't be missed
    if a.send:
        r = subprocess.run(['codex', 'queue', '--thread', thread, '--message', a.send], capture_output=True, text=True)
        if r.returncode: print('WATCH ERROR: codex queue failed: %s' % (r.stderr or r.stdout).strip()); return 2
    sys.stdout.reconfigure(line_buffering=True)
    return replies(path, offset, a.timeout, a.follow)

if __name__ == '__main__':
    sys.exit(main())
