# Discogs sync integration report

Owner: integration_worker
Status: ready for review

## Changes
- server.py: Refresh calls discogs_sync.sync under the existing refresh lock plus the shared account-data lock; failed syncs reload cached lists and return a safe error with last successful sync metadata. Local Buy/Wishlist/Undo refreshes skip the full account download.
- server.py: Startup loads usable cached data immediately, then starts a daemon sync. A first launch without account caches downloads synchronously and fails clearly if still offline. Background failure preserves cached operation. Importing the module never syncs.
- server.py: Live shelf and wantlist metadata now come from current CSVs and compact cache, alongside the Apple XML import; fixed harness snapshots are no longer app inputs. CSV placeholders retain exact and master-based ownership when detail downloads fail, without writing fake detail files that would prevent retries. Wantlist IDs are read by column name.
- server.py: A short SNAPSHOT_LOCK protects publication/capture of coherent state. Card rendering uses one captured snapshot throughout, even when background sync replaces the globals during a remote lookup. Network synchronization never holds this snapshot lock.
- server.py: If the full record lookup fails and there is no usable raw cache (including a saved 404 marker), the card renders the synced CSV/compact placeholder with live=false and unknown optional details. No placeholder is written as a downloaded release, so enrichment can still retry.
- static/index.html: Refresh shows Discogs counts, last successful sync, cached/error status, download failures, and distinguishes the local Apple library import. Existing navigation guards and escaping remain.
- tests/test_server.py: Existing decision route tests now call Handler.route with in-memory streams instead of opening a server. This preserves route/error/content-type assertions while obeying the project's rule that the Mac never runs a server, including tests.

## Verification
- CD_DISCOGS_DRY=1 python3 -W ignore::ResourceWarning -m unittest discover -s tests -p test_server.py: 47 passed.
- node --test tests/discogs-sync.test.cjs tests/navigation.test.cjs tests/decisions.test.cjs: 35 passed.
- git diff --check: passed.
- New cases cover sync-before-load ordering, detail failures retaining ownership, master-based edition matching, empty list removals, no fixed evaluation snapshot dependency, cached fallback with last success, sanitized unexpected errors, local-action sync avoidance, refresh/write serialization, prompt cached startup, asynchronous failure, first-start sync and offline failure, concurrent snapshot replacement, UI success/failure/empty counts/escaping/navigation protection.

## Limits
No live Discogs requests, service starts, paid calls, deployments, credentials changes or writes to real account/data were performed. Full suite and independent review remain lead checks. The local Apple XML must still exist for app startup. A first setup without a usable account cache may take time to download; existing installations bind promptly using their cache while syncing in the background.
