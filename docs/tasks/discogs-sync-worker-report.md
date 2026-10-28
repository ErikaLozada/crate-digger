# Discogs sync worker report

Owner: sync_worker
Status: READY (uncommitted for lead review)

## Changes
- `discogs_sync.py`: authenticated GET-only identity/folder discovery and paginated full collection/wantlist downloads; validation rejects truncated, changing-count and duplicate-page responses; bounded retries for rate limits, temporary server failures and connection failures.
- Both lists are normalized in memory with existing CSV helpers before publication. Preserve collection copies by instance_id and folder name/id, plus basic metadata for fallback ownership. Date Added is explicitly named for synced wantlists.
- Stage collection, wantlist and last-success metadata before replacing files. Ordinary replacement failures roll back already replaced files. If a restoration itself fails, try every other restoration, preserve failed recovery backup files beside caches and return an explicit recovery error.
- `discogs_write.py`: shared reentrant DATA_LOCK covers remote mutations plus local updates; errors expose safe status/retry metadata for GET retry logic. Buy records instance_id/folder_id in the synced schema; Undo targets the correct copy. Legacy exports retain last-copy fallback. Wishlist date append aligns with named Date Added when available.
- `status()` returns last successful counts/time only, or None for absent/malformed metadata. Dry-run sync performs no network or file writes.

## Verification
`CD_DISCOGS_DRY=1 python3 -W ignore::ResourceWarning -m unittest discover -s tests -p 'test_discogs*.py'`: 29 tests passed (19 sync tests plus 10 existing write tests).

Covered: all pages, duplicate collection copies, folders, empty accounts/removals, missing caches, legacy headers, failed later page preserving old caches/status, missing/rejected token, bounded connection retries, 429 Retry-After, malformed/truncated/changing pagination, failed publication and rollback recovery, malformed status, Unicode username quoting, sync-then-Buy/Wishlist/Undo, exact-instance Undo, account lock serialization. Tests use temporary data and mocked network exclusively. `git diff --check` passes.

## Limits
- No live token/API validation, server launch, deployment, paid model calls or account writes were attempted.
- Existing data/ installation directory assumed, consistent with required Library.xml and other installation data.
- A process crash between file replacements is not an atomic multi-file transaction; ordinary I/O failure rollback is tested. Failed rollback retains recovery backups rather than discarding them.
- Paginated API reads detect changing counts/page metadata and duplicate instances, but cannot guarantee a point-in-time remote snapshot if the account changes without a count change during the download. A subsequent Refresh reconciles it.
- Full project suite and independent review belong to lead.
