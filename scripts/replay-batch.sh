#!/bin/bash
# Replays every archived task twice per setup, cheapest setup first; skips the last (most expensive) setup when a
# cheaper one passed all automatic gates on every run. Blind reviews (gate 5) come afterwards, by hand.
#   bash scripts/replay-batch.sh claude "claude-haiku-5-5:high claude-sonnet-5-5:medium claude-opus-5-5:medium"
cd "$(dirname "$0")/.."
exec 3>&1                                                   # BLOCKED lines go straight to the summary log
KIND="$1"; read -r -a SETUPS <<< "$2"; TASKS="shelf-links-api shelf-links-page artist-links"; RUNS=2
passed_cheaper=""
# workers run in this stream's own herdr tab, split beside the tab's first pane, so the lead's pane stays readable
SPLIT_PANE="$(herdr tab create --label "replays-$KIND" --cwd "$PWD" --no-focus | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['root_pane']['pane_id'])")"
export SPLIT_PANE; echo "TAB replays-$KIND (pane $SPLIT_PANE)"
for i in "${!SETUPS[@]}"; do
  model="${SETUPS[$i]%%:*}"; effort="${SETUPS[$i]##*:}"
  if [ "$i" -eq $((${#SETUPS[@]} - 1)) ] && [ -n "$passed_cheaper" ]; then
    echo "SKIP $KIND $model $effort: $passed_cheaper already passed every run"; continue
  fi
  ok=0; n=0
  for task in $TASKS; do
    for r in $(seq $RUNS); do
      n=$((n + 1)); echo "START $KIND $model $effort $task run $r"
      res="$(bash scripts/replay.sh "$task" "$KIND" "$model" "$effort" 2>&1 | tee -a "data/replay-$KIND.detail.log" \
             | grep --line-buffered -E '^(RESULT|BLOCKED)' | while read -r l; do [[ "$l" == BLOCKED* ]] && echo "$l" >&3; echo "$l"; done | grep '^RESULT' | tail -1)"
      if [[ "$res" == *" nostart "* ]]; then echo "$res"; echo "STOP $KIND: a worker never received its brief; fix that before spending more runs"; break 3; fi
      [[ "$res" == *" pass" ]] && ok=$((ok + 1))
      echo "${res:-RESULT none fail (replay did not finish)}"
    done
  done
  echo "TIER $KIND $model $effort: $ok/$n passed the automatic gates"
  [ "$ok" -eq "$n" ] && [ -z "$passed_cheaper" ] && passed_cheaper="$model ($effort)"
done
herdr tab close "$(herdr pane get "$SPLIT_PANE" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['pane']['tab_id'])")" >/dev/null 2>&1 || true
echo "DONE $KIND"
