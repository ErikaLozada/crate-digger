# Task: explore-page
Owner: codex worker
Agent: codex, model gpt-6-luna, effort high; leave work uncommitted, the lead commits it
Status: done
Branch: explore-page
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: e872c46
Reference: 421a6d3
Scope: static/index.html tests/explore.test.cjs
Check: none

## Goal
A plain screen listing the Explore later entries, so artists saved at the bin can be dug into later (PRD F23: "a simple screen to read the list"; decisions.md 2026-10-19).

## Files
`static/index.html`, new `tests/explore.test.cjs` (node:test; reuse `tests/page-harness.cjs`, as `tests/decisions.test.cjs` does). Do not touch Python, other tests or data.

## Contracts
Existing API, already on main: `GET /api/explore` -> `{"entries": [entry...]}`, newest first. Entry fields: `id, release_id, action ('explore'), date (ISO), artist, title, price (str|null), tracks [str], note (str), discogs, undone`.
SAFETY: worktrees symlink `data/*` to the real files; any test server you start must use the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...). Never POST to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/explore-page-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done =
- Route `#/explore` (add it in `route()`), title "Explore Later", back button like the other views (see `chrome()`).
- A row on the home screen, below the search form, opens it: "Explore Later" with the entry count when the list is not empty (fetch `/api/explore` on home; on error show nothing).
- Each entry is a row in the existing iOS list style: artist (bold) and title, then the note if any, then liked tracks joined with " · ", then the date as "12 Oct" (reuse the page's existing `dayOf` helper; don't write a second one). Tapping the row opens `#/release/<release_id>`.
- Empty list: a short line "Nothing saved yet. Tap Explore later on a record card."
- Escape all text with the page's `esc`. A late response must not render into another view (use `viewGuard()` like the other views).
- Tests in tests/explore.test.cjs: rows render with fields escaped, empty state, home row count (and hidden when empty or on error), row links to the card, late-response guard. `make test` passes.
- Leave the work uncommitted (Codex) and report `[explore-page] READY` with a short summary.
