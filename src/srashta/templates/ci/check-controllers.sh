#!/usr/bin/env bash
# Constitution check: no business logic in controllers.
# A controller method may call one action and wrap the response. Nothing else.
# This is what keeps the API and web surfaces provably equivalent instead of
# parallel-and-drifting, and it is what makes the layer split real rather than aspirational.
set -uo pipefail
command -v rg >/dev/null || { echo "ripgrep is required for this optional heuristic check"; exit 1; }
fail=0
say() { echo "  $*"; fail=1; }

# Query builders, model writes and transactions belong in actions, not controllers.
while IFS=: read -r file line _; do
  say "business logic in a controller: $file:$line"
done < <(rg -n --no-heading \
  -e '\b(DB::|->where\(|->save\(\)|->update\(|->delete\(\)|->create\(|Model::)' \
  app/Http/Controllers/Api 2>/dev/null)

[ $fail -eq 0 ] && echo "  controllers: clean" || echo "  controllers: violations above"
exit $fail
