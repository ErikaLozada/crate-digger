# Task: shelf-links-api
Owner: Claude worker
Status: done
Branch: shelf-links-api
Port: 8001
Lead: Claude session "Do 3 and 4" (herdr pane wF:p5). Report to the lead; don't merge or deploy.
Base: 2ed31b0
Reference: 7c7c479 1e57050
Scope: server.py engine.py tests/test_server.py
Check: 1216425 12989331 14098396

## Goal
`GET /api/release/<id>` also returns which records on the shelf share musicians, producers or a label with the inspected record, with the records named, so the card can show "Herbie Hancock (piano) plays on Speak No Evil". The matching already exists in `engine.link()` (Discogs artist IDs, leaders who are sidemen elsewhere, non-musical roles dropped); this task exposes it per person, label and producer. Feature 1 of the shelf-credits work; the page is a separate task (Codex, branch shelf-links-page) built against the contract below.

## Files
`server.py` (`release()`), `engine.py` only if needed (keep `match()`'s existing output unchanged), `tests/test_server.py`.
Do not touch `static/index.html`, `harness.py`, `styles.py`, data files.

## Contracts
CONTRACT (identical in both tasks; change only through the lead):
`GET /api/release/<id>` keeps every existing field and adds `links`:
```json
"links": {
  "musicians": [{"name": "Herbie Hancock", "role": "Piano", "count": 1,
                 "records": [{"id": 31430060, "artist": "Wayne Shorter", "title": "Speak No Evil", "year": 1966}]}],
  "producers": [{"name": "Alfred Lion", "count": 4, "records": [...]}],
  "labels":    [{"name": "Blue Note", "count": 10, "records": [...]}]
}
```
- Only shelf records count. Exclude the inspected record and other editions of the same master; one entry per album when you own several editions.
- `count` = number of distinct shelf albums; `records` = up to 3 of them, oldest original year first; `year` may be null.
- `musicians` include a leader of either record who plays on the other (as `engine.link` does). `role` = the person's first musical role on the inspected record, else on the shelf record, else "".
- Order: musicians who lead either record first, then by `count` descending, then name. At most 6 musicians, 3 producers, 2 labels. Broad labels are already excluded by `engine.is_specific`.
- Empty lists when there is nothing; `links` is always present.
Example (real data): `GET /api/release/1216425` (Donald Byrd, Royal Flush) → Billy Higgins (Drums) on The Sidewinder; Herbie Hancock (Piano) on Speak No Evil; Blue Note, 10 records.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done = tests for ordering, limits, edition dedupe and empty case pass (`make test`), the example above returns as described on port 8001, commits on this branch with your Co-Authored-By trailer. Then tell the lead "READY shelf-links-api" with a two-line summary.
