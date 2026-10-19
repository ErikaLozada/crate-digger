# Task: au-sellers-link
Owner: codex worker
Agent: codex, model gpt-6-luna, effort high; leave work uncommitted, the lead commits it
Status: done
Branch: au-sellers-link
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 0ce21d7
Reference: a8bab3f
Scope: static/index.html tests/decisions.test.cjs tests/navigation.test.cjs tests/au-sellers.test.cjs
Check: none

## Goal
Price & Market gets a link that opens this release's Discogs marketplace listings filtered to sellers shipping from Australia. The API cannot filter listings by country, so the card links to the filtered page instead of showing prices (user, 2026-10-19).

## Files
`static/index.html` (the `#price` markup in `card()`, about line 478), a new `tests/au-sellers.test.cjs` (node:test, reuse `tests/page-harness.cjs`). Nothing else.

## Contracts
No API change: the card already has `r.id` (release id) and `r.market.for_sale`.
SAFETY: any test server uses the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...). Never send requests to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/au-sellers-link-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done =
- Inside the `#price` group, after the `.stats` block, a row link (same `a.row` list style as elsewhere, with `${I.chev}`) reading "Sellers in Australia", href `https://www.discogs.com/sell/release/<id>?ships_from=Australia` (id passed through `encodeURIComponent` and the whole href through `esc`), `target="_blank" rel="noopener"`.
- Shown only when `m.for_sale` is greater than 0.
- Tests: link present with the exact href when for_sale > 0; absent when 0 or missing. `make test` passes.
- Leave the work uncommitted and report `[au-sellers-link] READY` with a short summary.
