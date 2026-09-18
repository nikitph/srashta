#!/usr/bin/env bash
set -euo pipefail
BASE="${1:?pass the trusted base commit}"
BRANCH="${2:-${GITHUB_HEAD_REF:-$(git branch --show-current)}}"
if [[ ! "$BRANCH" =~ ^([CTI]-[0-9]{2,3}[a-z]?)- ]]; then
  echo 'A ticket branch name is required, including on detached CI checkouts.'; exit 1
fi
TICKET="${BASH_REMATCH[1]}"
git rev-parse --verify "$BASE^{commit}" >/dev/null
export PYTHONPATH="${PYTHONPATH:-.srashta/runtime}"
PHASE=$(python3 ci/ticket-phase.py "$BASE" "$TICKET")
python3 -m srashta verify "$PHASE" "$TICKET" --base "$BASE"
