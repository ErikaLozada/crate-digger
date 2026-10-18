#!/bin/bash
# Removes a task's worktree and branch once its branch is merged into main: make finish NAME=fix-search
set -e
cd "$(dirname "$0")/.."
NAME="$1"; WT="$(dirname "$PWD")/$(basename "$PWD")-$NAME"
[ -n "$NAME" ] || { echo "usage: make finish NAME=<short-name>"; exit 1; }
git merge-base --is-ancestor "$NAME" main || { echo "Branch $NAME is not merged into main yet; merge it (and make deploy) first."; exit 1; }
[ -z "$(git -C "$WT" status --porcelain --untracked-files=no)" ] || { echo "$WT has uncommitted changes:"; git -C "$WT" status --short; exit 1; }
git worktree remove --force "$WT"          # --force: TASK.md and the data symlinks are untracked by design
git branch -d "$NAME"
echo "Task $NAME finished: worktree and branch removed."
