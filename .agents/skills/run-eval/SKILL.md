---
name: run-eval
description: Run Crate Digger's recommendation harness on the 20-record test set for both models, review the picks with the user in the conversation, and regenerate docs/STATUS.md. Use when the prompt, style definitions, models or labels changed, or when the user asks for a new evaluation round.
---

# Run an evaluation round

Costs about US$0.25 for both models. Confirm with the user before starting if they didn't ask for a run.

1. **Check the ground first.** `git status` is clean and `make test` passes. Note the commit: the round evaluates exactly that prompt.
2. **Run both models**, primary first:
   ```
   set -a; . ~/.config/crate-digger/env; set +a
   python3 harness.py --model primary
   python3 harness.py --model fallback
   ```
   Each run writes `data/runs/<model>-<timestamp>.json`.
3. **Prepare the review.** Create the next `data/reviewN.json`: one entry per model and record with `model`, `id`, `record`, `your_style`, `model_style`, `close_match_known`, `your_note`, `picks` (each as `Artist — Album [shelf|library] — reason`), `false_match`, `needs_review`. Carry over `false_match` from earlier review files for the same record and pick. Set `needs_review` only on entries with a pick not judged before.
   - Apply the fixed rules without asking: any pick on a record labelled `close_match_known: false` is a false match; an unavailable answer has no picks and is not a false match.
4. **Review in the conversation.** Show one table of the new picks only, with a letter per pick, and ask which are not close. Accept short answers ("all ok except D, M"). Write the verdicts into the file yourself and clear `needs_review`.
5. **Report.** Run `make report`, then tell the user the acceptance table for the primary from `docs/STATUS.md`. Never quote numbers from memory or older notes.
6. **Commit** `data/reviewN.json` and `docs/STATUS.md` together (the run files stay local).

Never change `data/eval_set.json`: only the user labels. If the user changes a label, they commit it themselves with `LABELS_OK=1`.
