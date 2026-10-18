#!/bin/bash
# Deploys main to the live service: only a committed, tested tree, and logs what went live.
# Run with `make deploy`. Page-only changes don't need it; Python changes do.
{  # read the whole script before running any of it, so editing this file during a run cannot break that run
set -e
cd "$(dirname "$0")/.."
PORT="${CD_PORT:-8000}"

if [ "$(git branch --show-current)" != main ]; then echo "Refusing: deploy from main, not $(git branch --show-current)."; exit 1; fi
if [ -n "$(git status --porcelain)" ]; then echo "Refusing: uncommitted changes (the service runs this folder as it is):"; git status --short; exit 1; fi
make -s test

systemctl --user restart crate-digger
if ! curl -sf -o /dev/null --retry 15 --retry-connrefused --retry-delay 1 "http://127.0.0.1:$PORT/"; then
  echo "The service did not answer on port $PORT. Logs: journalctl --user -u crate-digger -n 30"; exit 1
fi
line="$(date '+%Y-%m-%d %H:%M') $(git rev-parse --short HEAD) $(git log -1 --format=%s)"
echo "$line" >> data/deploys.log
echo "Live: $line"
exit
}
