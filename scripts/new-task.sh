#!/bin/bash
# Starts a task in its own worktree and branch, beside this folder: make task NAME=fix-search [OWNER="Codex"]
# Untracked files the code needs (data, keys) are symlinked in; tracked ones come from the branch.
set -e
cd "$(dirname "$0")/.."
NAME="$1"; OWNER="${2:-unassigned}"
LINKS="data/* discogs_token.txt"            # untracked files a worktree needs; tracked ones are checked out
OWN="data/recommendations.json data/deploys.log"   # written by the live app: each worktree keeps its own
[ -n "$NAME" ] || { echo "usage: make task NAME=<short-name> [OWNER=<agent>]"; exit 1; }
[ "$(git branch --show-current)" = main ] || { echo "Run from the main worktree."; exit 1; }
MAIN="$PWD"; WT="$(dirname "$MAIN")/$(basename "$MAIN")-$NAME"

git worktree add -q -b "$NAME" "$WT" main
for f in $LINKS; do
  [[ " $OWN " == *" $f "* ]] && continue
  [ -e "$f" ] && ! git ls-files --error-unmatch "$f" >/dev/null 2>&1 && [ ! -e "$WT/$f" ] && ln -s "$MAIN/$f" "$WT/$f"
done

used="$(cat "$(dirname "$MAIN")"/"$(basename "$MAIN")"-*/TASK.md 2>/dev/null | sed -n 's/^Port: *//p')"
PORT=8001; while echo "$used" | grep -qx "$PORT" || ss -ltn | grep -q ":$PORT "; do PORT=$((PORT+1)); done

cat > "$WT/TASK.md" <<EOF
# Task: $NAME
Owner: $OWNER
Status: working
Branch: $NAME
Port: $PORT
Lead: none (make worker fills this in)
Base: $(git rev-parse --short main)
Scope: (files this task may change, space-separated; checked when the task is replayed)
Check: (optional: release ids whose links output must match on replay)

## Goal
(what done looks like, and the requirement or decision it serves)

## Files
(files this task changes; tell peers before touching anything else)

## Contracts
(anything other work depends on: a changed prompt, data format, API, command)

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_HOST=127.0.0.1 CD_PORT=$PORT python3 server.py

## Notes
EOF
echo "Task $NAME: $WT (branch $NAME, test port $PORT). Fill in TASK.md; finish with: make finish NAME=$NAME"
