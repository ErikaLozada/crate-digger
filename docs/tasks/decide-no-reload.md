# Task: decide-no-reload
Owner: codex worker
Agent: codex, model gpt-6-luna, effort high; leave work uncommitted, the lead commits it
Status: done
Branch: decide-no-reload
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 9cf30fc
Reference: be7c532
Scope: static/index.html tests/decisions.test.cjs
Check: none

## Goal
After Buy, Pass, Explore later, Wishlist or Undo succeeds, only the decision section updates; the rest of the card (picks, samples, links) stays as it is. Today `act()` in static/index.html calls `card(id)`, which redraws the whole card (user: "the page refreshes for some reason").

## Files
`static/index.html` (`act()` only, plus what it needs), `tests/decisions.test.cjs`. Nothing else.

## Contracts
API unchanged: POST `/api/decision/<id>` and DELETE `/api/decision/<entry_id>` both answer `{"decision": entry}` (after DELETE the entry has `undone` set).
SAFETY: any test server uses the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...). Never send requests to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/decide-no-reload-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done =
- On success, `act()` sets `r.decision` to the returned entry (POST) or to null (DELETE), then calls `decisions(id, r, current)` to redraw just `#decide`; no `card(id)` call. Keep the existing `current()` guard and the error path unchanged.
- Update the tests in tests/decisions.test.cjs that expected a card reload: after success there is no second `/api/release` fetch, the saved line ("Passed on ...") shows, and after Undo the four buttons (minus any hidden by `own`/`wanted`) show again.
- `make test` passes. Leave the work uncommitted and report `[decide-no-reload] READY` with a short summary.
