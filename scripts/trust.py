"""Marks a replay clone as trusted for Claude Code and Codex, or removes that mark (decided by the user, 2026-10-18).

  python3 scripts/trust.py add|remove <folder>

Only folders named ~/lab/CrateDigger-replay-* are accepted: each is a clone of this repo made by replay.sh.
"""
import json, os, re, sys

CLAUDE, CODEX = os.path.expanduser('~/.claude.json'), os.path.expanduser('~/.codex/config.toml')

def main(action, folder):
    folder = os.path.realpath(folder)
    if action not in ('add', 'remove') or not re.fullmatch(re.escape(os.path.expanduser('~/lab/CrateDigger-replay-')) + r'[a-z0-9-]+', folder):
        sys.exit('refused: only add|remove on ~/lab/CrateDigger-replay-* folders')
    d = json.load(open(CLAUDE, encoding='utf-8'))             # read-modify-write in one step: Claude Code also writes this file
    projects = d.setdefault('projects', {})
    if action == 'add': projects.setdefault(folder, {})['hasTrustDialogAccepted'] = True
    else: projects.pop(folder, None)
    tmp = CLAUDE + '.replay.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, indent=2)
    os.replace(tmp, CLAUDE)
    toml = open(CODEX, encoding='utf-8').read()
    block = '\n[projects."%s"]\ntrust_level = "trusted"\n' % folder
    toml = toml.replace(block, '')
    if action == 'add': toml = toml.rstrip('\n') + '\n' + block
    with open(CODEX + '.replay.tmp', 'w', encoding='utf-8') as f: f.write(toml)
    os.replace(CODEX + '.replay.tmp', CODEX)

if __name__ == '__main__':
    main(*sys.argv[1:3]) if len(sys.argv) == 3 else sys.exit(__doc__)
