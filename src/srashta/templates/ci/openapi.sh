#!/usr/bin/env bash
# Generate the API contract, and diff it against what is committed.
#
# WHY CI AND NOT A TICKET: tickets in a wave run concurrently with exclusive file
# ownership. If every api ticket regenerated docs/openapi.yaml, every ticket in the
# wave would touch the same file - a guaranteed collision, and a direct violation of
# the rule the validator exists to enforce. So no ticket owns the contract. CI
# generates it, the PR shows the diff, and CI commits it on merge to main.
#
# Generation is annotation-free (dedoc/scramble reads routes, form requests and
# resources), so an agent produces contract documentation by writing ordinary Laravel
# code and never by remembering to document anything.
set -uo pipefail
OUT=docs/openapi.yaml
TMP=$(mktemp)

php artisan scramble:export --path="$TMP" 2>/dev/null \
  || { echo "  scramble not installed: composer require dedoc/scramble"; exit 1; }

mkdir -p docs
if [ ! -f "$OUT" ]; then
  cp "$TMP" "$OUT"; echo "  API contract created at $OUT"; exit 0
fi

if diff -q "$OUT" "$TMP" >/dev/null; then
  echo "  API contract unchanged"; exit 0
fi

echo "  API contract changed:"
diff -u "$OUT" "$TMP" | sed -n '1,120p' | sed 's/^/    /'
cp "$TMP" "$OUT"

# After the api -> surface boundary the contract is frozen like any other contract:
# screens are built against it and an unannounced change breaks them silently.
if [ -f docs/.openapi-frozen ]; then
  echo
  echo "  The API contract is FROZEN (docs/.openapi-frozen exists)."
  echo "  Screens are built against it. This change needs a contract-change ticket,"
  echo "  not a quiet regeneration."
  exit 1
fi
exit 0
