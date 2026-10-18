# Crate Digger

A private web app for deciding on a record in a shop: scan it, see whether you own it, its main style, and the closest records you already own or listen to. Requirements: `Crate Digger Product Requirements v5.md`. Results: `docs/STATUS.md` (generated). Why things are the way they are: `docs/decisions.md`.

## Commands

| Command | Does |
| --- | --- |
| `make test` | Python `unittest` and `node --test`; also run by the pre-commit hook |
| `make report` | Rebuilds `docs/STATUS.md` from `data/eval_set.json`, `data/review*.json` and `data/runs/` |
| `make status` | What is live, worktrees and their tasks, uncommitted changes |
| `make deploy` | Refuses on a dirty tree or failing tests, restarts the service, checks it answers, logs the commit |
| `make setup` | Once per clone: turns on the git hooks in `.githooks/` |

Harness (costs money, about US$0.10–0.14 per 20-record run): `set -a; . ~/.config/crate-digger/env; set +a; python3 harness.py --model primary` (or `fallback`). Runs land in `data/runs/`.

## How it runs

- `server.py` is the backend and serves `static/index.html`. It runs as the systemd user service `crate-digger` on the Linux laptop (omarchy), from this folder, on 127.0.0.1:8000. `tailscale serve` makes it reachable over the tailnet only.
- Never bind it publicly and never enable Tailscale Funnel: the app has no login.
- Page changes take effect on reload; Python changes need `make deploy`. Logs: `journalctl --user -u crate-digger -f`.
- Keys: the OpenRouter key is in `~/.config/crate-digger/env` (mode 600, loaded only by the service); the Discogs token is in `discogs_token.txt` (600, git-ignored). Never print, commit or send them to the browser.
- Model calls go through OpenRouter (`check_models.py`): primary `openai/gpt-5.6-luna`, fallback `anthropic/claude-haiku-5.5`, routed only to providers that honour the JSON schema and keep no data. The app calls only the primary.

## Data

- `data/` is git-ignored except `eval_set.json` and `review*.json`. Your exports (`collection.csv`, `Library.xml`), Discogs downloads (`releases/`, `masters/`, `compact.json`), runs and saved answers stay local.
- Refresh in the app downloads Discogs details for new shelf and wantlist records, rebuilds `compact.json` (`build_compact.py`) and reloads. Apple previews are looked up live, only for the record being inspected.
- The app's shelf list for the model is built from the current `collection.csv`. The harness uses the fixed snapshot `data/results.json` so runs stay comparable.
- Answers are saved in `data/recommendations.json`, keyed by a hash of model, prompt, lists and record; any change to these asks the model again.

## Evaluation rules

- Only the user labels `data/eval_set.json`. Never change a label to fit model output; the pre-commit hook rejects label changes unless the user commits with `LABELS_OK=1`.
- A false match is a pick the user judges not close. Any pick on a record labelled `close_match_known: false` is false. An unavailable answer is not a false match.
- Records labelled `Other/uncertain` are left out of style accuracy.
- Review picks with the user in the conversation (one table, letters per pick; short answers like "all ok except D"), then write their verdicts into `data/reviewN.json`. Carry over verdicts already given for the same record and pick.

## Working with other agents

- Before starting: check for other sessions and `git status`. Tell any peer which files you will change.
- Reaching other agents: Claude sessions with `ListAgents` and `SendMessage`; a Codex session with `codex queue --thread <session id> --message "..."` (find the id in `~/.codex/session_index.jsonl`, and read its replies in its file under `~/.codex/sessions/`). Codex cannot message Claude, so it reports in its own session and in commits.
- Every commit names the agent that made it in a trailer, e.g. `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` or `Co-Authored-By: Codex <noreply@openai.com>`.
- Parallel work goes in its own worktree and branch, one per task, with `data/` symlinked in and its own `CD_PORT` for a test server. Never use `git stash`.
- One lead owns `main`, merges and `make deploy`. Others do not restart the live service.
- Shared files have one writer at a time: `data/eval_set.json` (the user), the review files, `data/recommendations.json` (the server).
- Message peers before touching shared state, and when a branch is ready.
- A prompt change (`harness.SYSTEM`, `harness.lists_text`, `styles.DEFINITIONS`) makes every saved answer miss once; batch prompt changes.

## Conventions

- Match the surrounding code: compact Python, few comments, stdlib only. Tests use `unittest` (Python) and `node:test` (page).
- Small commits whose message says why. Commit finished work promptly: the Mac copy pulls from here with `git pull linux main`.
- Run `make report` after a run or review; never copy results into notes by hand.

## Glossary

- **Recommendation** (code: `recommend`, `/api/recommend`) = the card's sentence, main style and **Closest in Your Collection** picks, from one model call.
- **Shelf** = Discogs collection; **library** = Apple Music library; **wantlist** = Discogs wantlist.
- **No-close record** = labelled `close_match_known: false`.
