# Task: decision-buttons
Owner: claude worker
Agent: claude, model claude-haiku-5-5, effort high
Status: done
Branch: decision-buttons
Port: 8003
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 5c09f38
Reference: 584f199
Scope: static/index.html tests/navigation.test.cjs tests/decisions.test.cjs
Check: 2499163

## Goal
The record card gets Buy, Pass, Explore later and Wishlist, built against the API contract below (the server half is being written in parallel; test against mocked fetch). Serves decisions.md 2026-10-19 and the PRD's later-product flow (steps 8 and 10).

## Files
`static/index.html`, page tests in `tests/` (`node:test`, like `tests/navigation.test.cjs`). Do not touch Python files or data.

## Contracts
CONTRACT (identical in all decision tasks; change only through the lead). Decision: docs/decisions.md 2026-10-19.

Dig history `data/decisions.json` (path from env `CD_DECISIONS`, default `data/decisions.json`; only the server writes it, under a lock, written to a temp file and renamed). A JSON list, oldest first; undo marks an entry, never deletes it:
```json
{"id": "9f2c...", "release_id": 2499163, "action": "buy|pass|explore|wishlist", "date": "2026-10-19T14:02:11+11:00",
 "artist": "Chick Corea", "title": "Return To Forever", "price": "25" , "tracks": ["Sometime Ago - La Fiesta"], "note": "",
 "discogs": {"folder_id": 1, "instance_id": 123} , "undone": null}
```
`id` = uuid4 hex; `price` = string as typed or null; `tracks`/`note` default [] / ""; `discogs` = what `discogs_write.buy/want` returned (null for pass/explore); `undone` = null, or the ISO date it was undone.

API (all JSON):
- `POST /api/decision/<release_id>` body `{"action": ..., "price"?: str|null, "tracks"?: [str], "note"?: str}` → 200 `{"decision": entry}`. `buy` calls `discogs_write.buy(rid)`, `wishlist` calls `discogs_write.want(rid)` FIRST; on `discogs_write.DiscogsError` → 502 `{"error": msg}` and nothing saved. After a successful buy/wishlist the server calls `refresh()` so the shelf/wantlist reload. Unknown action → 400.
- `DELETE /api/decision/<entry_id>` → 200 `{"decision": entry}` with `undone` set. buy → `discogs_write.unbuy(rid, folder_id, instance_id)`, wishlist → `discogs_write.unwant(rid)` first, then refresh(); DiscogsError → 502, entry unchanged. Unknown or already undone id → 404.
- Both write routes reject a request whose Content-Type is not `application/json` with 415 (stops cross-site form posts).
- `GET /api/release/<id>` keeps every field and adds `"decision"`: the latest entry for that release with `undone` null, or null; and `"wanted"`: true if the release is in `data/wantlist.csv`.
- `GET /api/explore` → `{"entries": [...]}`: explore entries not undone, newest first.

`discogs_write` (module on main, stub; task discogs-writes fills it): `buy(rid) -> {'folder_id': 1, 'instance_id': int}`, `unbuy(rid, folder_id, instance_id)`, `want(rid) -> {}`, `unwant(rid)`; raise `DiscogsError(msg)`. With `CD_DISCOGS_DRY=1`: no network, no file changes, made-up ids.

SAFETY: worktrees symlink `data/*` to the real files and `discogs_token.txt` is the real account. Every test server you start: `CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/<task>-decisions.json`. Tests mock the network. Never make a real Discogs write and never edit the real `data/collection.csv` / `data/wantlist.csv`.


## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/decision-buttons-decisions.json CD_HOST=127.0.0.1 CD_PORT=8003 python3 server.py

## Notes
Done = Four buttons at the bottom of the card (iOS style, matching the page). An optional sticker price field used by any action. Explore later opens a small inline form: note plus checkboxes for the card's `tracks`, then Save. Hide Buy only when this exact release is on the shelf (`own.kind == 'same'`; `other_edition` and `apple` keep Buy); hide Wishlist when `wanted` is true. When `decision` is set show a line such as "Passed on 12 Oct" / "Bought on ..." with an Undo button (DELETE) instead of the buttons. Buy/Wishlist show a pending state, then an error row with the server's message on failure. After success, reload the card. A late response must not change a different card (follow the existing request-guard pattern in the page). Escape all text. Tests for: rendering per decision state, hidden buttons, undo, error, and the late-response guard. `make test` passes. Commit with your trailer and report `[decision-buttons] READY` with a summary.
