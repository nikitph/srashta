#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-.srashta/runtime}"
if [ "$#" -eq 0 ]; then
  python3 -m srashta api generate
else
  python3 -m srashta api check --base "$1"
fi
