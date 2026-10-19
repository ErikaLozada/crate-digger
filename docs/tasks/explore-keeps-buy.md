# Task: explore-keeps-buy
Owner: codex worker
Agent: codex, model gpt-6-luna, effort high; leave work uncommitted, the lead commits it
Status: done
Branch: explore-keeps-buy
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: b34f5d5
Reference: 0c75722
Scope: static/index.html tests/decisions.test.cjs
Check: none

## Goal
The card offers three actions, Buy, Explore later and Wishlist; Pass is removed (user: "no action is a pass"). After Explore later the card shows the saved line with Undo and still offers Buy and Wishlist below it; after Buy or Wishlist it shows only the saved line with Undo, as today.

## Files
`static/index.html` (`decisions()`, `act()`, the `.decide` CSS if the grid needs it), `tests/decisions.test.cjs`. Nothing else; the server is unchanged and still accepts `pass`.

## Contracts
API unchanged. `GET /api/release/<id>` → `decision` is the LATEST non-undone entry for the release (any action). POST `/api/decision/<id>` and DELETE `/api/decision/<entry_id>` answer `{"decision": entry}`.
SAFETY: any test server uses the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...). Never send requests to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/explore-keeps-buy-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done =
- No Pass button. A saved `pass` decision from old history still renders as "Passed on ..." with Undo and, like explore, keeps Buy and Wishlist offered.
- `decision.action` explore (or pass): saved line + Undo, then the sticker price field and the Buy / Wishlist buttons (same hiding rules: Buy hidden when `own.kind === 'same'`, Wishlist hidden when `wanted`). No Explore later button while an explore is saved.
- `decision.action` buy or wishlist: saved line + Undo only.
- No decision: price field and Buy, Explore later, Wishlist.
- Undo: after a successful DELETE, re-read the decision without redrawing the card: fetch `/api/release/<id>`, take only its `decision` into `r.decision`, then redraw `#decide` (an earlier explore may still be active under an undone wishlist). Keep the `current()` guard on both awaits. POST success keeps today's behaviour (`r.decision = result.decision`).
- Tests: three buttons and no Pass; explore state shows line + Undo + Buy + Wishlist; buy/wishlist state shows line + Undo only; old pass entry renders; undo of a wishlist made after an explore returns to the explore state; hero/picks/samples/links unchanged. `make test` passes.
- Leave the work uncommitted and report `[explore-keeps-buy] READY` with a short summary.
