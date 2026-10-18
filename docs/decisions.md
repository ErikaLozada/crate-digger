# Decisions

Settled decisions, newest last. Append; don't rewrite. Reopen one by adding a new entry that supersedes it.

- **2026-10-04** Records are matched by sound by a language model choosing from your library and shelf, not by Discogs tags. Tags are too coarse (Phase 0 test).
- **2026-10-18** Model calls go through OpenRouter: primary `openai/gpt-5.6-luna`, fallback `anthropic/claude-haiku-5.5`. Requests go only to providers that honour the JSON schema and keep no data, and return their cost.
- **2026-10-18** The app runs on the Linux laptop (omarchy), reachable over Tailscale only. The Mac is for development, never a server, not even for tests. No Tailscale Funnel: the app has no login.
- **2026-10-18** Only the user labels the test set; labels are never changed to fit model output.
- **2026-10-18** Records labelled `Other/uncertain` are left out of style accuracy; the model's style is shown as a suggested label.
- **2026-10-18** The model must answer "nothing close" (no picks) when nothing is close.
- **2026-10-18** An unavailable answer is not a false match.
- **2026-10-18** Any pick on a record labelled "no close match known" is a false match. Grinspoon and Fantasia keep that label, so their picks are false in every round.
- **2026-10-18** Apple previews are looked up only for the record being inspected; Refresh downloads Discogs details only.
- **2026-10-18** Recommendations are saved and reused while model, prompt, lists and record are unchanged. A JSON file, not a database, until there is history or more than one user.
- **2026-10-18** The app's shelf list comes from the current collection; the harness keeps the fixed `data/results.json` snapshot so runs stay comparable.
- **2026-10-18** Style definitions (one line per family) are part of the prompt. New family House-jazz (Discogs Future Jazz); St Germain is labelled House-jazz.
- **2026-10-18** Luna stays the primary: on run 3 it beat Haiku on false matches (3/20 vs 5/20) at similar style accuracy.
- **2026-10-18** Project instructions live in `AGENTS.md` (portable across Claude Code, Codex and pi); `CLAUDE.md` imports it. Results are generated into `docs/STATUS.md`, never copied by hand.
- **2026-10-18** herdr is the default channel between agents (Claude and Codex): `herdr agent list/prompt/read/start`; workers run in herdr panes so they show in its agent panel. `SendMessage` and `scripts/watch-codex.py` are fallbacks outside herdr.
