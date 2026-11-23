#!/bin/zsh
# Weekly Homebrew update + upgrade (formulae and casks).
# Notifications are sent only while today < NOTIFY_UNTIL (initial trial period);
# after that the script runs silently and only writes to the log.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin"
export NONINTERACTIVE=1 HOMEBREW_NO_ENV_HINTS=1
NOTIFY_UNTIL="2026-12-13"   # covers the first two Mondays: 2026-11-30 and 2026-12-07

notify() {
  [[ "$(date +%Y-%m-%d)" < "$NOTIFY_UNTIL" ]] || return 0
  osascript -e "display notification \"$1\" with title \"Brew upgrade\" subtitle \"$2\""
}

echo "=== $(date) ==="
before=$(brew outdated --quiet 2>/dev/null | wc -l | tr -d ' ')

if ! brew update; then
  notify "brew update failed. See /tmp/brew-upgrade.log" "FAILED"
  exit 1
fi
if ! brew upgrade; then
  notify "brew upgrade had errors. See /tmp/brew-upgrade.log" "FAILED"
  exit 1
fi

notify "Upgraded; $before package(s) were outdated before the run." "OK"
echo "done"
