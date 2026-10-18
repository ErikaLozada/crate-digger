# Task: discogs-writes
Owner: claude worker
Agent: claude, model claude-sonnet-5-5, effort medium
Status: done
Branch: discogs-writes
Port: 8002
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 5c09f38
Reference: 964670e be88238
Scope: discogs_write.py tests/test_discogs_write.py
Check: 2499163

## Goal
Fill in `discogs_write.py` so Buy adds a release to the Discogs collection (folder 1) and Wishlist to the wantlist, each undoable, then updates the local export so the shelf/wantlist reflect it at once. Serves decisions.md 2026-10-19. The server routes are written by another worker against the same signatures.

## Files
`discogs_write.py`, `tests/test_discogs_write.py`. Do not touch `server.py`, `static/index.html` or data files. Reuse `server.py` patterns (User-Agent `UA`, token header `Discogs token=...`) but don't import `server` (it loads data at import); read the token the same way it does.

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
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/discogs-writes-decisions.json CD_HOST=127.0.0.1 CD_PORT=8002 python3 server.py

## Notes
Done = Username from `GET /oauth/identity` (cached). buy: `POST /users/{u}/collection/folders/1/releases/{rid}` → instance_id; unbuy: `DELETE /users/{u}/collection/folders/{f}/releases/{rid}/instances/{i}`; want: `PUT /users/{u}/wants/{rid}`; unwant: `DELETE` same. Check these against the Discogs API docs. After success: buy appends a row to `data/collection.csv` with the release's fields (fetch `GET /releases/{rid}` for artist, title, label, format, catno, year; folder name `Uncategorized`; Date Added now), unbuy removes that row; want/unwant likewise for `data/wantlist.csv` (keep its header and column order exactly). Non-2xx or network failure → `DiscogsError` with a short human message, never the token. `CD_DISCOGS_DRY=1` → no network, no file changes. Tests mock urllib and use temp CSV copies (paths overridable by module variables). `make test` passes. Commit with your trailer and report `[discogs-writes] READY` with a summary. Never run a real write.
