# Task: server-hardening
Owner: claude worker
Agent: claude, model claude-sonnet-5-5, effort medium
Status: done
Branch: server-hardening
Port: 8001
Lead: herdr pane w2:p1 (report there; it merges and deploys)
Base: 457ce24
Reference: 91f38d0
Scope: server.py discogs_write.py build_compact.py tests/test_server.py tests/test_discogs_write.py
Check: none

## Goal
Fix five findings from a review of the backend (pi, 2026-10-19), each with a test that fails before the fix. No behaviour change for the normal path; no prompt change (do not touch harness.SYSTEM, harness.lists_text, styles.DEFINITIONS, or anything that feeds request_key).

## Files
`server.py`, `discogs_write.py`, `build_compact.py` only if needed, `tests/test_server.py`, `tests/test_discogs_write.py`. Do not touch `static/index.html` (another worker is on it), `harness.py`, `styles.py`, data files.

## Contracts
API unchanged except one new error text (item 2). The page shows the server's `error` string as is.
SAFETY: worktrees symlink `data/*` to the real files and `discogs_token.txt` is the real account. Any test server uses the command below (CD_DISCOGS_DRY=1, CD_DECISIONS=/tmp/...); tests use temp dirs and mocks. Never make a real Discogs write, never write the real data files, never send requests to the live service on port 8000.

## Test server
set -a; . ~/.config/crate-digger/env; set +a; CD_DISCOGS_DRY=1 CD_DECISIONS=/tmp/server-hardening-decisions.json CD_HOST=127.0.0.1 CD_PORT=8001 python3 server.py

## Notes
Done =
1. Bind default: `HOST` in server.py defaults to `127.0.0.1` (CD_HOST still overrides). Update the module docstring line that suggests opening it from another device on the same Wi-Fi: it is reached through `tailscale serve`.
2. Partial failures after a successful Discogs write (discogs_write.py, server.record_decision):
   - In `buy`/`want`/`unbuy`/`unwant`, a failure updating the local CSV (OSError, csv.Error, ValueError) after the Discogs call succeeded must not raise: print it to stderr and return the normal result. Discogs is the source of truth; the next export fixes the CSV.
   - In `record_decision`, if saving the history fails after `buy`/`want` succeeded, print the full entry JSON (it holds `instance_id`) to stderr and raise an error whose message is exactly: `Discogs was updated, but the history could not be saved; do not retry. Details are in the server log.` The route returns it as 500 `{"error": ...}`. Same idea for `undo_decision` if saving fails after the Discogs undo: `Discogs was updated, but the history could not be saved. Details are in the server log.`
   - Tests: mocked CSV write failure after a successful remote call returns the normal result; mocked history-save failure returns 500 with that message and logs the entry.
3. Refresh is serialized: a module-level lock around the whole body of `refresh()` (the decision routes call it too). `load()` builds everything in locals first and publishes the globals in one assignment at the end, so a request never sees half old, half new state. Test: two concurrent `refresh()` calls with a slow mocked `fetch_new` never overlap.
4. Rebuild recovery: `refresh()` rebuilds `compact.json` when releases were added OR when any `data/releases/*.json` or `data/masters/*.json` is newer than `data/compact.json` (or compact.json is missing). Test: a failed rebuild is retried on the next refresh.
5. One paid call per record: in `recommend()`, a per-request-key lock (a dict of locks guarded by a small lock) wraps the cache check and the model call, re-checking `SAVED` after acquiring it. Test: two concurrent identical requests with a slow mocked `harness.run_one` make one call and both get the answer.
- `make test` passes. Commit with your trailer (Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>) and report `[server-hardening] READY` with a summary.
