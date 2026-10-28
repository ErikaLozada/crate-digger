# Discogs account sync

Base: 5007329c9840e3d1423fbc8c6593caee06a312a9
Lead: Codex
Status: implemented and independently reviewed

## Goal
Replace manual Discogs collection/wantlist exports with authenticated downloads on Refresh and startup. Keep local CSV caches for existing readers and offline fallback. Apple library remains an XML import. No deployment or account writes in this task.

## Rules and isolation
Use the shared main folder with exclusive file ownership: data and tokens are untracked and must never be changed by worker runs. Existing unrelated docs/reel-import-requirements.md belongs to the user. Python stdlib, existing compact style, unittest and node:test. Tests mock network, use TemporaryDirectory for writable data, and CD_DISCOGS_DRY=1. Never launch a server on this Mac, make paid calls, print secrets, run real Discogs writes, change protected labels, or alter harness prompts/fixed evaluation snapshots. Code only: no Computer Use, screen, app or GUI actions. Workers never commit. Lead runs final make test and commits with normal hooks.

Herdr socket is inaccessible; use built-in agents with the available inherited model (the configured Claude worker models are unavailable through this backend). Review is by a separate agent; cross-provider review unavailable.

## Contract
- New discogs_sync.sync() returns a dict with collection, wantlist counts and synced_at ISO timestamp. It downloads /oauth/identity, /users/{username}/collection/folders/0/releases, /users/{username}/wants, following all pages with bounded retry/backoff for temporary errors and rate limiting. Reuse discogs_write authentication and row/format helpers; errors never include credentials.
- New discogs_write.DATA_LOCK is a threading.RLock. All four account write operations hold it across remote write plus CSV update. sync holds it across download and publishing; server.refresh also uses it across sync/fetch/reload. No DECISIONS_LOCK acquisition while holding DATA_LOCK. Lock ordering: REFRESH_LOCK then DATA_LOCK; existing decision functions release DECISIONS_LOCK before refresh.
- Download and validate both complete lists before touching either cache. Retain duplicate collection instances and folders, handle remote deletions and empty lists. Use existing CSV headers when present and compatible defaults otherwise. Preserve instance_id in a column for correct Undo after sync. Roll back already replaced files if publishing the second fails; test this. Do not mark sync successful until caches are saved. Persist last success in data/discogs-sync.json; provide discogs_sync.status() returning last success or None. Files in data are ignored already.
- Respect DRY: sync raises a safe DiscogsError without network/files when CD_DISCOGS_DRY=1. All tests explicitly mock sync or disable DRY only inside temporary-data tests.
- server.refresh(sync=True) performs sync under both locks, then current fetch_new/build/load. On sync failure, reload last good cache and return sync_error (safe message) plus last successful sync metadata, without pretending lists were updated. Existing added/failed/shelf/library fields stay; add wantlist count and sync metadata. refresh(sync=False) skips account download, used after Buy/Wishlist/Undo to avoid stale remote reads undoing successful local actions.
- fetch_new reads wantlist release_id by header, not a positional index. load must not reuse removed shelf records from fixed harness recs for app recommendations; harness remains unchanged. Keep ownership valid even if newly synced record details cannot be downloaded (basic_info is available from sync).
- Startup loads a usable cached snapshot immediately and schedules refresh in a daemon thread, so slow API/detail downloads do not block the listener or the deploy health check. Without any usable cache, bootstrap may sync synchronously and fail clearly if offline. Importing server does not start sync/network. No credentials in browser; Refresh UI reports success counts and last success/error clearly. No fabricating empty account.

## Tasks and owners
1. sync-worker: discogs_sync.py, discogs_write.py, tests/test_discogs_sync.py, tests/test_discogs_write.py. Implement downloads, normalization, safe caching, metadata and write serialization. Focus failure tests: multipage, duplicate instances, folders, empty/removals, invalid token, missing key, malformed/truncated pagination, 429/transient retry bound, failed page leaves old caches, failed publication rolls back, dry-run no side effects, Undo removes correct duplicate after sync.
2. integration-worker: server.py, static/index.html, tests/test_server.py, tests/discogs-sync.test.cjs. Integrate agreed API; tests mock discogs_sync. Test sync before reload, fallback reporting, startup offline, local writes skip full sync, overlapping refresh/write serialized, header-based IDs, live ownership after details failures, recommendation candidates no longer include removed shelf copies, UI error and success messages/navigation protection.
3. lead: docs/decisions.md, AGENTS.md, this plan. Review each diff and contract, full tests, inspect all changes for duplicate logic and live-data safety, commit only task files.
4. reviewer: docs/tasks/discogs-sync-review.md only. Read baseline diff and tests, report concrete correctness defects with failing scenarios; lead confirms and assigns fixes. Repeat until no material defects remain.

## Acceptance
Mocked paginated lists fully replace cached collection/wantlist; interrupted sync never leaves partial lists; Buy/Wishlist/Undo still work without full re-sync; key never sent to browser; offline refresh reports cached status; test suite passes. No live API validation possible in this network-restricted session. No Linux deployment from this Mac.

## Results
- Final `CD_DISCOGS_DRY=1 make test`: 93 Python tests and 44 Node tests passed.
- Additional end-to-end check in temporary data: mocked Discogs API through real sync, CSV publication, server reload, offline owned card, then remote removals; passed.
- Read-only check against existing local data: app shelf, wantlist and recommendation candidate IDs match the cached CSVs (162 shelf rows, 587 library albums). Fingerprints confirm credentials, exports, compact/fixed snapshots, decisions, saved recommendations and the user's unrelated requirements file were unchanged.
- Independent reviewer confirmed startup availability, rollback recovery and coherent snapshots; its offline-card finding R1 was fixed and re-reviewed. No unresolved material findings. See discogs-sync-review.md and the worker reports.
- No live API validation, server launch, Linux service deployment or push was performed. Cached multi-file publication has tested I/O rollback, not a process-crash transaction guarantee.
