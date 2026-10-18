---
name: ship-feature
description: Take a change from idea to live in this project, safely alongside other agents - announce, isolate in a worktree when others are active, test, review, merge, deploy. Use when starting any code change to Crate Digger, a feature or a fix.
---

# Ship a feature

1. **Look around.** Run `git status` and `make status`, and check for other agent sessions (Claude: `ListAgents`; Codex: newest session in `~/.codex/session_index.jsonl`).
2. **Pin down done.** Say in one or two sentences what done looks like and which requirement or decision it serves (`Crate Digger Product Requirements v5.md`, `docs/decisions.md`). If it changes a settled decision, ask the user first.
3. **Isolate if anyone else is active.** `make task NAME=<short-name> OWNER=<you>`, work in the new folder, and fill in `TASK.md` (goal, files, contracts). Working alone, use `main` directly.
4. **Announce.** Tell every active peer which files you will change: Claude with `SendMessage`, Codex with `python3 scripts/watch-codex.py --send "..."` (run in the background; it reports the reply).
5. **Build test-first where you can.** Add or change tests in `tests/` (`unittest`, `node:test`), then the code, matching the surrounding style. Check the change in the real app on your task's test port (see `TASK.md`), never on the live service.
6. **Check what it touches.** If the change alters the model request (`harness.SYSTEM`, `harness.lists_text`, `styles.DEFINITIONS`), saved answers start over and the eval may need a new round (skill `run-eval`). Write that in `TASK.md` under Contracts.
7. **Commit** small commits whose message says why, with your agent trailer (`Co-Authored-By: ...`). The pre-commit hook runs the tests.
8. **Review.** In Claude Code run `/code-review` on the branch; otherwise ask another agent or the user to read the diff. Fix what holds up.
9. **Hand over.** If you are not the lead, tell the lead the branch is ready and stop. The lead merges into `main`, runs `make deploy` and then `make finish NAME=<short-name>`.
10. **Record.** New settled decisions go into `docs/decisions.md`. Tell the user what changed and what to check.
