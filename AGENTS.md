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
| `make task NAME=x OWNER=y` | New branch and sibling worktree for a task, data linked in, own test port, `TASK.md` to fill in |
| `make finish NAME=x` | Removes a task's worktree and branch once merged |
| `make replay TASK=x KIND=codex\|claude MODEL= EFFORT=` | Replays an archived task (`docs/tasks/`) with a chosen model and grades it against the reviewed result; results in `docs/tasks/replays.md` |
| `make worker NAME=x KIND=codex\|claude` | A task worktree plus a worker agent in a herdr pane beside you, with worker permissions |

Skills (in `.agents/skills/`, shared by Claude, Codex and pi): `ship-feature` for any code change, `run-eval` for an evaluation round.

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

- Before starting: check for other agents (`herdr agent list`) and `git status`. Tell any peer which files you will change.
- Agents run in herdr panes (check `HERDR_ENV=1`), and herdr is the default channel for Claude and Codex alike: `herdr agent list` (who is there, idle/working/blocked), `herdr agent prompt <name> "..." --wait` (send and wait for the turn to end), `herdr agent read <name>` (read its reply). Run `herdr --skill` once for the full guide.
- Starting a worker: `make worker NAME=x KIND=codex|claude`, which creates the worktree, opens a herdr pane beside you and starts the agent with the worker permissions the user chose (Codex: writes only its worktree, network allowed, asks for anything else; Claude: auto mode). Optional `MODEL=` and `EFFORT=` pick a cheaper model or lower effort; `TASK.md` records what each worker ran with. Fill in `TASK.md`, then brief it with `herdr agent prompt`. Workers appear in herdr's agent panel.
- Every message between agents starts with the sender's name in brackets, e.g. `[links-page] READY ...` or `[lead] approved`. Text typed into a pane through herdr looks exactly like the user typing; an untagged message is the user's.
- A worker (the `Lead:` line in its `TASK.md` is not `none`) does not repeat the lead's checks or announcements: it reads `TASK.md`, works in its worktree, and reports to the lead. It never merges or deploys. A Codex worker cannot write git metadata from its sandbox, so it leaves its work uncommitted and reports READY; the lead reviews the diff and commits it in the worktree with `Co-Authored-By: Codex <noreply@openai.com>`.
- A worker waiting on an approval shows as `blocked`: tell the user which pane; never answer approvals on their behalf.
- Outside herdr: Claude sessions with `ListAgents`/`SendMessage`; a Codex session with `python3 scripts/watch-codex.py --send "..."` (prints its reply when its turn ends).
- Every commit names the agent that made it in a trailer, e.g. `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` or `Co-Authored-By: Codex <noreply@openai.com>`.
- Parallel work goes in its own worktree and branch, one per task (`make task`), with its own test port. Never use `git stash`.
- One lead owns `main`, merges and `make deploy`. Others do not restart the live service.
- Shared files have one writer at a time: `data/eval_set.json` (the user), the review files, `data/recommendations.json` (the server).
- Message peers before touching shared state, and when a branch is ready.
- Choosing worker models: a cheaper model or lower effort is used for a kind of task only after `make replay` shows it passing every gate (hidden tests, whole suite, real-data output, scope, blind review) on all archived tasks of that kind, two runs each. `make finish` archives each brief so every task becomes a replay case; fill in its `Scope:` and `Check:` lines.
- A prompt change (`harness.SYSTEM`, `harness.lists_text`, `styles.DEFINITIONS`) makes every saved answer miss once; batch prompt changes.

## Conventions

- Match the surrounding code: compact Python, few comments, stdlib only. Tests use `unittest` (Python) and `node:test` (page).
- Small commits whose message says why. Commit finished work promptly: the Mac copy pulls from here with `git pull linux main`.
- Run `make report` after a run or review; never copy results into notes by hand.

## Glossary

- **Recommendation** (code: `recommend`, `/api/recommend`) = the card's sentence, main style and **Closest in Your Collection** picks, from one model call.
- **Shelf** = Discogs collection; **library** = Apple Music library; **wantlist** = Discogs wantlist.
- **No-close record** = labelled `close_match_known: false`.
