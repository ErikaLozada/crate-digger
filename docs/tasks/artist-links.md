# Task: artist-links
Owner: Codex worker
Status: done
Branch: artist-links
Port: 8001
Lead: herdr pane wF:p5 (report there; it merges and deploys)
Base: fd7575b
Reference: 839f177
Scope: engine.py tests/test_server.py static/index.html tests/navigation.test.cjs
Check: 8238279 1710836 1216425

## Goal
"Connections on Your Shelf" on the record card also lists the other shelf albums by the same lead artist, e.g. scanning Stanley Turrentine's Never Let Me Go shows "More by Stanley Turrentine: 4 records you own: Hustlin', Prayer Meetin', Common Touch and 1 more". Today these are missing: `engine.shelf_links()` deliberately skips a person who leads both records (that's "same artist", not a sideman). Follow-up to the shelf-links feature (merge 3eefb50).

## Files
`engine.py` (`shelf_links()` only), `tests/test_server.py`, `static/index.html` (`connections()` only), `tests/navigation.test.cjs`.
Do not touch `server.py`, `harness.py`, `styles.py`, data files.

## Contracts
`links` (from `GET /api/release/<id>`) gains a fourth list, `artists`; the other three lists don't change:
```json
"artists": [{"name": "Stanley Turrentine", "count": 4,
             "records": [{"id": 14098396, "artist": "Stanley Turrentine", "title": "Hustlin'", "year": 1965}]}]
```
- One entry per lead artist of the inspected record (`t.main`) who is also a lead artist of other shelf albums (`o.main`). Same exclusions and dedupe as the other lists: not the record itself, not other editions of its master, each album once.
- `count` = distinct shelf albums; `records` = up to 3, oldest original year first (as the other lists); order by `count` descending, then name; at most 3 entries; always present (empty list).
- Classical records often have composer, orchestra and conductor as lead artists: each gets its own entry, which is wanted.
- Page: artist rows come first in the group, titled "More by Stanley Turrentine". Subtitle: one album → "Hustlin' (1965)"; more → "4 records you own: A, B, C and 1 more". Record names open their cards, text escaped, as the existing rows. A missing `artists` (older server) counts as empty; the group stays hidden when all four lists are empty.

## Examples (real data)
- 8238279 Stanley Turrentine – Never Let Me Go → Stanley Turrentine, 4 albums (Hustlin', Prayer Meetin', Common Touch, Cherry).
- 1710836 Karajan / Berliner Philharmoniker – Ravel, Debussy, Mussorgsky → several entries (Herbert von Karajan, Berliner Philharmoniker, …).
- 1216425 Donald Byrd – Royal Flush → `artists` empty; the existing musicians, producer and label rows unchanged.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done = Python and page tests for the new list (ordering, limit, dedupe, empty, page wording, hidden case) pass with `make test`; the three examples behave as described on port 8001; commits on this branch with `Co-Authored-By: Codex <noreply@openai.com>`. Then report to the lead.
