# Discogs sync independent review

Reviewer: separate Codex agent; cross-provider review unavailable in this backend.
Baseline: 5007329c9840e3d1423fbc8c6593caee06a312a9

## Findings

- **R1 — P2, resolved:** Originally a newly synced collection item whose details failed to download appeared in the shelf/local search but its card raised `URLError` offline: `fetch_release` only fell back to a raw release file that did not exist. The original ownership test masked this by substituting a successful raw response. `server.py:206` now captures the compact cache with the rest of the read snapshot; `server.py:207`–`217` falls back to its basic information on failed or malformed full-detail responses and marks the result non-live. No fake raw file is saved, so missing details are retried. Updated `test_failed_detail_download_keeps_synced_ownership` calls the actual offline release path; `test_missing_or_invalid_raw_details_still_show_synced_owned_record` covers saved missing/invalid raw responses. Independently reran all 47 server tests successfully after this fix.

No unresolved material findings after the final re-review.

## Resolved during design review

- Startup initially planned a synchronous full refresh before HTTP serving. Existing deploy health checks allow only about 15 seconds, while missing-detail downloads take at least 1.1 seconds each. The implementation now loads usable caches immediately and schedules refresh in a daemon thread; first setup without an account cache still requires a successful sync.
- Independent cache replacement cannot be fully crash-atomic. The implementation rolls back completed replacements on publication failure, continues other rollback attempts if one restore fails, retains recovery copies for failed restores and reports recovery failure honestly. Status is published only after both account caches.
- Background refresh introduced a concrete card race: collection membership could change between an owned-id check and a later `next()` over the shelf. A short separate snapshot lock now publishes and captures coherent read snapshots, without making card reads wait for the long-running account/write lock.

## Coverage and verification

Read all new `discogs_sync.py`, its tests, the write-helper diff, server/UI integration and added tests, then re-reviewed the final fix. Sync tests independently passed: 19 tests with mocked network and temporary files. Server tests independently passed: 47 tests, with in-memory route streams and no sockets. Checked multipage validation, changed/truncated data, empty lists/removals, duplicate collection instances, folders, token errors, bounded GET retries, legacy wantlist date alignment, exact Undo and cache/status rollback. No unresolved sync/write module defects found. No real account calls, credential disclosure, local data changes or server starts.

Live Discogs API behaviour and Linux deployment could not be verified from this session. Faults involving process termination or hardware failure between separate CSV replacements are outside the rollback guarantee.
