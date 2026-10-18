# Task: decisions-store
Owner: codex worker
Agent: codex, model gpt-6-sol, effort medium; leave work uncommitted, the lead commits it
Status: done
Branch: decisions-store
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 5c09f38
Reference: bd8d494
Scope: server.py tests/test_server.py
Check: 2499163

## Goal
The server keeps the dig history and serves the decision API in the contract below: record and undo Buy, Pass, Explore later and Wishlist, with buy/wishlist going through `discogs_write` (stub on main; another worker fills it in parallel, so mock it in tests). Serves decisions.md 2026-10-19.

## Files
`server.py` (history helpers, routes, `do_DELETE`, `decision`/`wanted` in `release()`, wantlist ids in `load()`), `tests/test_server.py`. Do not touch `discogs_write.py`, `static/index.html`, `harness.py`, `styles.py`, data files.

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
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/decisions-store-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done = Tests for: each action saved with its fields; buy/wishlist call discogs_write and save nothing on DiscogsError (502); undo marks `undone` and calls unbuy/unwant; 404 on unknown/already undone; 415 on a non-JSON Content-Type; `decision` is the latest non-undone entry; `/api/explore` newest first; history survives a reload of the file. `make test` passes. On your test port with `CD_DISCOGS_DRY=1` mocked or the stub patched, `curl` a pass and an explore on 2499163 and show `/api/release/2499163` has `decision`. Leave the work uncommitted (Codex) and report `[decisions-store] READY` with a short summary.
