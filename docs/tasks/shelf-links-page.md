# Task: shelf-links-page
Owner: Codex worker
Status: done
Branch: shelf-links-page
Port: 8002
Lead: Claude session "Do 3 and 4" (herdr pane wF:p5). Report to the lead; don't merge or deploy.
Base: 2ed31b0
Reference: 6127802
Scope: static/index.html tests/navigation.test.cjs tests/links.test.cjs
Check:
Hidden: none (the reference page tests read one element structure; graded by what the card shows instead)
Render: 1216425 12596028
RenderBackend: 1e57050

## Goal
On the record card, show which records on the shelf share musicians, producers or a label with this record, especially useful for jazz ("Herbie Hancock · Piano — on Speak No Evil"). The data comes from a new `links` field of `GET /api/release/<id>` (contract below), built in parallel by another worker (branch shelf-links-api). Build against the contract and the sample; don't wait for the backend.

## Files
`static/index.html`, `tests/navigation.test.cjs` or a new `tests/links.test.cjs`.
Do not touch `server.py`, `engine.py`, `harness.py`, data files.

## Page rules
- New group titled "Connections on Your Shelf", directly below the ownership group and above "Closest in Your Collection". It renders with the release data (no extra request), so it appears before the model's picks.
- Hidden entirely when musicians, producers and labels are all empty, or when `links` is missing (older server).
- One row per entry. Musician: "Herbie Hancock · Piano", subtitle "on Speak No Evil (Wayne Shorter, 1966)" or "on 3 records: A, B, C" / "on 5 records: A, B, C and 2 more". Producer: "Produced by Alfred Lion" + records. Label: "Blue Note" + "10 records you own: A, B, C and 7 more".
- Each named record opens its card (`#/release/<id>`). Escape all text (`esc`). Match the existing iOS styling and icons; light and dark.
- Keep the stale-response protection: a late release response must not draw into a different card.

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
- `count` = number of distinct shelf albums; `records` = up to 3 of them; `year` may be null; `role` may be "".
- Lists may be empty; at most 6 musicians, 3 producers, 2 labels.
Sample (real data, Donald Byrd – Royal Flush, id 1216425):
```json
{"musicians": [{"name": "Billy Higgins", "role": "Drums", "count": 1, "records": [{"id": 7925345, "artist": "Lee Morgan", "title": "The Sidewinder", "year": 1964}]},
               {"name": "Herbie Hancock", "role": "Piano", "count": 1, "records": [{"id": 31430060, "artist": "Wayne Shorter", "title": "Speak No Evil", "year": 1966}]}],
 "producers": [],
 "labels": [{"name": "Blue Note", "count": 10, "records": [{"id": 3820432, "artist": "Jutta Hipp With Zoot Sims", "title": "Jutta Hipp With Zoot Sims", "year": 1957},
            {"id": 5462880, "artist": "Sonny Clark", "title": "The Art Of The Trio", "year": 1980}, {"id": 36534199, "artist": "Melissa Aldana", "title": "Filin", "year": 2026}]}]}
```

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_HOST=127.0.0.1 CD_PORT=8002 python3 server.py
(Until the backend branch is merged this server has no `links`; test rendering with the sample in your tests.)

## Notes
Done = tests cover rendering from the sample, the hidden case and the stale-response case (`make test`), commits on this branch with the trailer `Co-Authored-By: Codex <noreply@openai.com>`. Then tell the lead "READY shelf-links-page" with a two-line summary.
