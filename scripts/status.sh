#!/bin/bash
# What is live, and what every worktree is doing. Run with `make status`.
cd "$(dirname "$0")/.."

echo "LIVE"
echo "  service:     $(systemctl --user is-active crate-digger 2>/dev/null) since $(systemctl --user show crate-digger -p ActiveEnterTimestamp --value 2>/dev/null)"
if [ -s data/deploys.log ]; then
  last="$(tail -1 data/deploys.log)"; live="$(echo "$last" | cut -d' ' -f3)"
  echo "  last deploy: $last"
  behind="$(git rev-list --count "$live"..main 2>/dev/null)"
  [ "${behind:-0}" -gt 0 ] && echo "  main is $behind commit(s) ahead of what was deployed; Python changes need make deploy"
else
  echo "  last deploy: none logged yet (make deploy logs each one)"
fi

echo
echo "WORKTREES"
git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}' | while read -r path; do
  branch="$(git -C "$path" branch --show-current)"
  dirty="$(git -C "$path" status --porcelain | wc -l)"
  ahead="$(git rev-list --count main.."$branch" 2>/dev/null)"
  task=""
  if [ -f "$path/TASK.md" ]; then
    task="$(grep -m1 -i '^owner:' "$path/TASK.md" | cut -d: -f2- | xargs) · $(grep -m1 -i '^status:' "$path/TASK.md" | cut -d: -f2- | xargs)"
  fi
  printf '  %-12s %s\n' "$branch" "$path"
  printf '  %-12s %s uncommitted file(s)%s%s\n' "" "$dirty" "$([ "$branch" != main ] && echo ", $ahead commit(s) not on main")" "${task:+ · $task}"
done

echo
echo "Other agent sessions: ListAgents in Claude Code. Results: docs/STATUS.md (make report)."
