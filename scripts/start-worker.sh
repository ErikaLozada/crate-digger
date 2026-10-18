#!/bin/bash
# Starts a worker agent for a task: its worktree (make task), a herdr pane beside the caller, and the agent in it
# with the permissions the user chose for workers (decisions.md, 2026-10-18).
#   make worker NAME=fix-search KIND=codex|claude [OWNER="Codex worker"]      DRY=1 prints the commands instead
# Codex: may write only its worktree and the repo's .git (worktree commits live there), may use the network
# (local test server, herdr), asks for anything else. Claude: auto permission mode.
set -e
cd "$(dirname "$0")/.."
NAME="$1"; KIND="$2"; OWNER="${3:-$KIND worker}"
[ -n "$NAME" ] && [[ "$KIND" =~ ^(codex|claude)$ ]] || { echo "usage: make worker NAME=<short-name> KIND=codex|claude [OWNER=...]"; exit 1; }
MAIN="$PWD"; WT="$(dirname "$MAIN")/$(basename "$MAIN")-$NAME"
case "$KIND" in
  codex)  ARGS=(--sandbox workspace-write --ask-for-approval on-request --add-dir "$MAIN/.git" -c sandbox_workspace_write.network_access=true) ;;
  claude) ARGS=(--permission-mode auto) ;;
esac
run() { if [ -n "$DRY" ]; then printf '%q ' "$@"; echo; else "$@"; fi; }

[ -d "$WT" ] || run bash scripts/new-task.sh "$NAME" "$OWNER"
[ -n "$DRY" ] || sed -i "s|^Lead: none.*|Lead: herdr pane ${HERDR_PANE_ID:-unknown} (report there; it merges and deploys)|" "$WT/TASK.md"
if [ "${HERDR_ENV:-}" != 1 ]; then
  echo "Not inside herdr: start it yourself with:  cd $WT && $KIND ${ARGS[*]}"; exit 0
fi
if [ -n "$DRY" ]; then
  echo "herdr pane split --current --direction right --cwd $WT --no-focus"
  run herdr agent start "$NAME" --kind "$KIND" --pane '<new pane>' -- "${ARGS[@]}"; exit 0
fi
PANE="$(herdr pane split --current --direction right --cwd "$WT" --no-focus | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['pane']['pane_id'])")"
herdr agent start "$NAME" --kind "$KIND" --pane "$PANE" --timeout 60000 -- "${ARGS[@]}" >/dev/null
echo "Worker $NAME ($KIND) in pane $PANE, folder $WT. Brief it: herdr agent prompt $NAME \"...\" --wait"
