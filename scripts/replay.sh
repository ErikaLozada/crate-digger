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
sed -e 's/^Status: .*/Status: working/' -e 's/^Lead: .*/Lead: none/' -e '/^Reference: /d' -e "s/^Branch: .*/Branch: $RUN/" "$B" > "$D/TASK.md"

bash scripts/start-worker.sh "$RUN" "$KIND" "replay" "$MODEL" "$EFFORT"
start=$SECONDS
herdr agent prompt "$RUN" "[lead] You are a worker on Crate Digger. Your task is in TASK.md in this folder; read AGENTS.md, then TASK.md, and follow the ship-feature skill's worker path. This is a replay run: do not commit, leave your work in the working tree. Start every message to me with [$RUN]. If the contract seems wrong, stop and ask, starting the line with QUESTION:. When done, end your final message with: [$RUN] READY, plus a two-line summary." --wait --timeout 1800000 >/dev/null || true
state="$(herdr agent get "$RUN" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['agent']['agent_status'])" 2>/dev/null || echo unknown)"
echo "Worker $RUN finished as '$state' after $((SECONDS - start)) s."
if [ "$state" = blocked ]; then echo "It is waiting for an approval in its pane: answer there, then run: python3 scripts/grade.py run $TASK $D"; exit 0; fi
python3 scripts/grade.py run "$TASK" "$D"
echo "Blind review: python3 scripts/grade.py diff $D   then   python3 scripts/grade.py review $(basename "$D") pass|fail \"note\""
