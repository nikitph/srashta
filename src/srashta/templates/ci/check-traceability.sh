#!/usr/bin/env bash
# Every commit on this branch names its ticket, so the chain stays walkable.
#
# The hook prefixes locally; this catches commits made without it - a different
# machine, a web edit, a rebase that dropped a message.
set -uo pipefail
BASE="${1:-origin/main}"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
TICKET=$(printf '%s' "$BRANCH" | grep -oE '^[CTI]-[0-9]{2,3}[a-z]?')

if [ -z "$TICKET" ]; then
  echo "  branch '$BRANCH' is not a ticket branch; traceability not checked"
  exit 0
fi

# A base ref that does not resolve makes `git log` fail, the loop read nothing, and
# this script report success. Silent pass on broken input is the failure mode this
# whole check exists to prevent, so verify the input first.
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  for alt in origin/main origin/master main master; do
    git rev-parse --verify --quiet "$alt" >/dev/null && { BASE="$alt"; break; }
  done
fi
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "  cannot resolve a base ref ('$BASE'); refusing to report a pass on nothing"
  exit 1
fi

COUNT=$(git rev-list --count "$BASE..HEAD")
if [ "$COUNT" -eq 0 ]; then
  echo "  no commits between $BASE and HEAD; nothing to check"
  exit 0
fi

fail=0
while read -r sha subject; do
  printf '%s' "$subject" | grep -qE "\b$TICKET\b" || {
    echo "  $sha does not name $TICKET: $subject"; fail=1; }
done < <(git log --format='%h %s' "$BASE..HEAD")

if [ $fail -eq 1 ]; then
  echo
  echo "  srashta trace finds commits by ticket id. A commit that omits it is not an"
  echo "  error at the time - the link is simply lost, silently and permanently."
  echo "  Fix with: git rebase -i $BASE   (or install hooks/commit-msg)"
  exit 1
fi
echo "  traceability: every commit names $TICKET"
