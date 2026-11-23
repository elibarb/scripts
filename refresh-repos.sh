#!/bin/zsh
# Refresh every ~/github.com/<org>/<repo>: update only the default branch, never disturb WIP.
ROOT="$HOME/github.com"
problems=()
note() { problems+=("$1: $2"); echo "  $2" }

echo "=== $(date) ==="
for repo in "$ROOT"/*/*(N/); do
  [[ -d "$repo/.git" ]] || continue
  name="${repo#$ROOT/}"
  echo "== $name"
  g() { git -C "$repo" "$@" }

  g remote get-url origin >/dev/null 2>&1 || { echo "  no origin remote, skipped"; continue; }
  g fetch --all --prune --quiet || { note "$name" "fetch failed"; continue; }
  g remote set-head origin -a >/dev/null 2>&1   # learn the default branch

  default=$(g symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
  default=${default#origin/}
  [[ -n "$default" ]] || { note "$name" "no default branch found"; continue; }

  current=$(g symbolic-ref --short HEAD 2>/dev/null)

  if [[ "$current" == "$default" ]]; then
    if [[ -z "$(g status --porcelain)" ]]; then
      g merge --ff-only --quiet "origin/$default" || note "$name" "$default can't fast-forward"
    else
      echo "  on $default with local changes, skipped"
    fi
  else
    g fetch --quiet origin "$default:$default" 2>/dev/null \
      || note "$name" "$default not updated (diverged or checked out in another worktree)"
  fi
done

if (( ${#problems} )); then
  msg="${#problems} issue(s). See /tmp/refresh-repos.log"
  sub="${problems[1]//\"/}"
  osascript -e "display notification \"$msg\" with title \"Repo refresh\" subtitle \"$sub\""
fi
