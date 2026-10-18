#!/bin/bash
# Starts a worker agent for a task: its worktree (make task), a herdr pane beside the caller, and the agent in it
# with the permissions the user chose for workers (decisions.md, 2026-10-18).
#   make worker NAME=fix-search KIND=codex|claude [OWNER=...] [MODEL=...] [EFFORT=low|medium|high]   DRY=1 prints the commands
# Codex: may write only its worktree, may use the network (local test server, herdr), asks for anything else; it cannot
# write git metadata, so it leaves its work uncommitted and the lead commits it. Claude: auto permission mode, commits itself.
set -e
cd "$(dirname "$0")/.."
NAME="$1"; KIND="$2"; OWNER="$3"; MODEL="$4"; EFFORT="$5"
case "${TIER:-}" in                                         # the user's model table (AGENTS.md); explicit values win
  simple)  KIND="${KIND:-codex}";  MODEL="${MODEL:-gpt-6-luna}";       EFFORT="${EFFORT:-high}" ;;
  medium)  KIND="${KIND:-claude}"; MODEL="${MODEL:-claude-haiku-5-5}"; EFFORT="${EFFORT:-high}" ;;
  complex) KIND="${KIND:-claude}"; MODEL="${MODEL:-claude-opus-5-5}";  EFFORT="${EFFORT:-high}" ;;
  "") ;;
  *) echo "TIER must be simple, medium or complex"; exit 1 ;;
esac
OWNER="${OWNER:-$KIND worker}"
[ -n "$NAME" ] && [[ "$KIND" =~ ^(codex|claude)$ ]] || { echo "usage: make worker NAME=<short-name> TIER=simple|medium|complex (or KIND=codex|claude) [OWNER=...] [MODEL=...] [EFFORT=...]"; exit 1; }
MAIN="$PWD"; WT="$(dirname "$MAIN")/$(basename "$MAIN")-$NAME"
case "$KIND" in
  codex)  ARGS=(--sandbox workspace-write --ask-for-approval on-request -c sandbox_workspace_write.network_access=true)
          [ -n "$MODEL" ] && ARGS+=(-m "$MODEL"); [ -n "$EFFORT" ] && ARGS+=(-c "model_reasoning_effort=$EFFORT") ;;
  claude) ARGS=(--permission-mode auto)
          [ -n "$MODEL" ] && ARGS+=(--model "$MODEL"); [ -n "$EFFORT" ] && ARGS+=(--effort "$EFFORT") ;;
esac
run() { if [ -n "$DRY" ]; then printf '%q ' "$@"; echo; else "$@"; fi; }

[ -d "$WT" ] || run bash scripts/new-task.sh "$NAME" "$OWNER"
NOTE=""; [ "$KIND" = codex ] && NOTE="; leave work uncommitted, the lead commits it"
[ -n "$DRY" ] || sed -i -e "s|^Lead: none.*|Lead: herdr pane ${HERDR_PANE_ID:-unknown} (report there; it merges and deploys)|" \
  -e "s|^Owner: .*|&\nAgent: $KIND, model ${MODEL:-default}, effort ${EFFORT:-default}$NOTE|" "$WT/TASK.md"
if [ "${HERDR_ENV:-}" != 1 ]; then
  echo "Not inside herdr: start it yourself with:  cd $WT && $KIND ${ARGS[*]}"; exit 0
fi
if [ -n "$DRY" ]; then
  echo "herdr pane split ${SPLIT_PANE:+--pane $SPLIT_PANE}$([ -z "$SPLIT_PANE" ] && echo --current) --direction right --cwd $WT --no-focus"
  run herdr agent start "$NAME" --kind "$KIND" --pane '<new pane>' -- "${ARGS[@]}"; exit 0
fi
PANE="$(herdr pane split ${SPLIT_PANE:+--pane "$SPLIT_PANE"} $([ -z "$SPLIT_PANE" ] && echo --current) --direction right --cwd "$WT" --no-focus | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['pane']['pane_id'])")"
herdr agent start "$NAME" --kind "$KIND" --pane "$PANE" --timeout 60000 -- "${ARGS[@]}" >/dev/null \
  || echo "Worker $NAME started but is not ready: it may be waiting for an approval in pane $PANE"
echo "Worker $NAME ($KIND) in pane $PANE, folder $WT. Brief it: herdr agent prompt $NAME \"...\" --wait"
