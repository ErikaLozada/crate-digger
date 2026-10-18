---
name: ship-feature
description: Take a change from idea to live in this project, safely alongside other agents - announce, isolate in a worktree when others are active, test, review, merge, deploy. Use when starting any code change to Crate Digger, a feature or a fix.
---

# Ship a feature

**Worker started by a lead** (the `Lead:` line in your `TASK.md` is not `none`): skip steps 1, 3 and 4 and the merging in step 9. Read `TASK.md` and start at step 5. If you are a Codex worker, don't commit (your sandbox can't write git metadata): leave the work uncommitted and the lead commits it after review. Report to the lead with messages that begin with your name in brackets, e.g. `[fix-search] READY ...`.

1. **Look around.** Run `git status` and `make status`, and check for other agents with `herdr agent list`.
2. **Pin down done.** Say in one or two sentences what done looks like and which requirement or decision it serves (`Crate Digger Product Requirements v5.md`, `docs/decisions.md`). If it changes a settled decision, ask the user first.
3. **Isolate if anyone else is active.** `make task NAME=<short-name> OWNER=<you>`, work in the new folder, and fill in `TASK.md` (goal, files, contracts). To hand the task to another agent instead, `make worker NAME=<short-name> KIND=codex|claude` and brief it. Working alone, use `main` directly.
4. **Announce.** Tell every active peer which files you will change: `herdr agent prompt <name> "..." --wait`, then `herdr agent read <name>` for the reply (outside herdr: `SendMessage` for Claude, `scripts/watch-codex.py --send` for Codex). Start every message with your name in brackets.
5. **Build test-first where you can.** Add or change tests in `tests/` (`unittest`, `node:test`), then the code, matching the surrounding style. Check the change in the real app on your task's test port (see `TASK.md`), never on the live service.
6. **Check what it touches.** If the change alters the model request (`harness.SYSTEM`, `harness.lists_text`, `styles.DEFINITIONS`), saved answers start over and the eval may need a new round (skill `run-eval`). Write that in `TASK.md` under Contracts.
7. **Commit** small commits whose message says why, with your agent trailer (`Co-Authored-By: ...`). The pre-commit hook runs the tests.
8. **Review.** In Claude Code run `/code-review` on the branch; otherwise ask another agent or the user to read the diff. Besides correctness, check for duplicated logic: new code should build on existing helpers rather than copy their rules into a second place, which tests cannot catch (the shelf-links reference re-implemented `engine.link()`). Fix what holds up.
9. **Hand over.** If you are not the lead, tell the lead the branch is ready and stop. The lead commits any uncommitted Codex work in its worktree (with the Codex trailer) after review, then merges into `main`, runs `make deploy` and then `make finish NAME=<short-name>`.
10. **Record.** New settled decisions go into `docs/decisions.md`. Tell the user what changed and what to check.
