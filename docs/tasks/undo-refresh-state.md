# Task: undo-refresh-state
Owner: codex worker
Agent: codex, model gpt-6-luna, effort high; leave work uncommitted, the lead commits it
Status: done
Branch: undo-refresh-state
Port: 8002
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 457ce24
Reference: b1df184
Scope: static/index.html tests/decisions.test.cjs
Check: none

## Goal
After Undo, the card's ownership row and the Buy/Wishlist buttons reflect the account again (review finding 6, 2026-10-19): today `act()` re-reads only `decision` after a DELETE, so undoing a Wishlist on a reopened card leaves `r.wanted` true and the Wishlist button hidden; undoing a Buy leaves the ownership row and Buy hidden.

## Files
`static/index.html` (`act()` only), `tests/decisions.test.cjs`. Nothing else.

## Contracts
`GET /api/release/<id>` returns `decision`, `wanted`, `own` (unchanged API). The ownership row is `$('#own').innerHTML = ownership(r.own)`.
SAFETY: worktrees symlink `data/*` to the real files and `discogs_token.txt` is the real account. Any test server uses the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...); tests use temp dirs and mocks. Never make a real Discogs write, never write the real data files, never send requests to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/undo-refresh-state-decisions.json CD_HOST=127.0.0.1 CD_PORT=8002 python3 server.py

## Notes
Done =
- In `act()`, after a successful DELETE and the existing re-read of `/api/release/<id>`, copy `decision`, `wanted` and `own` from it into `r`, set `$('#own').innerHTML = ownership(r.own)`, then redraw `#decide` as today. Keep both `current()` guards.
- After a successful POST of `buy` or `wishlist`, do the same re-read (the server has refreshed by then) so the ownership row shows the record as owned/wanted; `explore` keeps today's behaviour (`r.decision = result.decision`, no re-read).
- Tests: reopened wishlisted card (wanted true, decision wishlist) -> Undo -> Wishlist button visible; buy -> ownership row updates from the re-read; undo buy -> Buy visible and ownership row back; hero/picks/samples/links still untouched. `make test` passes.
- Leave the work uncommitted and report `[undo-refresh-state] READY` with a short summary.
