#!/bin/bash
# Replays a finished task with a chosen agent, model and effort, then grades it (scripts/grade.py).
#   make replay TASK=artist-links KIND=codex|claude [MODEL=...] [EFFORT=low|medium|high]
#   make replay-clean RUN=replay-artist-links-1a2b          removes a replay folder once reviewed
# The worker gets a clone holding history only up to the task's Base, with no remote, so it cannot see the reference.
set -e
cd "$(dirname "$0")/.."
if [ "$1" = clean ]; then
  d="$(dirname "$PWD")/$(basename "$PWD")-$2"
  [[ "$2" == replay-* && -d "$d/.git" ]] || { echo "not a replay folder: $d"; exit 1; }
  rm -rf "$d"; echo "removed $d"; exit 0
fi
TASK="$1"; KIND="$2"; MODEL="$3"; EFFORT="$4"; B="docs/tasks/$TASK.md"
[ -f "$B" ] && [[ "$KIND" =~ ^(codex|claude)$ ]] || { echo "usage: make replay TASK=<archived task> KIND=codex|claude [MODEL=] [EFFORT=]"; exit 1; }
BASE="$(sed -n 's/^Base: *//p' "$B")"
RUN="replay-$TASK-$(head -c2 /dev/urandom | od -An -tx1 | tr -d ' \n')"; D="$(dirname "$PWD")/$(basename "$PWD")-$RUN"

git branch -q "tmp-$RUN" "$BASE"
git clone -q --no-local --single-branch --branch "tmp-$RUN" . "$D"
git branch -q -D "tmp-$RUN"
git -C "$D" checkout -q -b "$RUN"; git -C "$D" branch -q -D "tmp-$RUN"; git -C "$D" remote remove origin
python3 -c "import sys; sys.path.insert(0, 'scripts'); import grade; grade.link_data('$D')"
PORT=$([ "$KIND" = claude ] && echo 8101 || echo 8201)     # own range per agent, so a Claude and a Codex stream can run at once
while ss -ltn | grep -q ":$PORT " || grep -qsx "Port: $PORT" "$(dirname "$PWD")"/*-replay-*/TASK.md; do PORT=$((PORT+1)); done
sed -e 's/^Status: .*/Status: working/' -e 's/^Lead: .*/Lead: none/' -e '/^Reference: /d' -e "s/^Branch: .*/Branch: $RUN/" \
    -e "s/^Port: .*/Port: $PORT/" -e "s/CD_PORT=[0-9]*/CD_PORT=$PORT/g" -e "s/port 800[0-9]/port $PORT/g" "$B" > "$D/TASK.md"

bash scripts/start-worker.sh "$RUN" "$KIND" "replay" "$MODEL" "$EFFORT"
start=$SECONDS
herdr agent prompt "$RUN" "[lead] You are a worker on Crate Digger. Your task is in TASK.md in this folder; read AGENTS.md, then TASK.md, and follow the ship-feature skill's worker path. This is a replay run: do not commit, leave your work in the working tree. Start every message to me with [$RUN]. If the contract seems wrong, stop and ask, starting the line with QUESTION:. When done, end your final message with: [$RUN] READY, plus a two-line summary." --wait --timeout 1800000 >/dev/null || true
field() { herdr agent get "$RUN" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['agent']['$1'])" 2>/dev/null || echo unknown; }
PANE="$(field pane_id)"
while [ "$(field agent_status)" = blocked ]; do              # never grade half-done work: wait for the user's answer
  echo "BLOCKED $RUN: waiting for an approval in herdr pane $PANE"
  herdr agent wait "$RUN" --until working --timeout 3600000 >/dev/null 2>&1 || break
  herdr agent wait "$RUN" --timeout 3600000 >/dev/null 2>&1 || break
done
echo "Worker $RUN finished as '$(field agent_status)' after $((SECONDS - start)) s."
out="$(python3 scripts/grade.py run "$TASK" "$D")"; echo "$out"
[ "$PANE" != unknown ] && herdr pane close "$PANE" >/dev/null 2>&1 || true
if echo "$out" | grep -q '^tests: pass' && ! echo "$out" | grep -q 'FAIL'; then echo "RESULT $RUN pass"; else echo "RESULT $RUN fail"; fi
echo "Blind review: python3 scripts/grade.py diff $D   then   python3 scripts/grade.py review $(basename "$D") pass|fail \"note\""
