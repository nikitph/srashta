#!/usr/bin/env bash
# Constitution check: no business logic in controllers.
# A controller method may call one action and wrap the response. Nothing else.
# This is what keeps the API and web surfaces provably equivalent instead of
# parallel-and-drifting, and it is what makes the layer split real rather than aspirational.
set -uo pipefail
fail=0
say() { echo "  $*"; fail=1; }

# Query builders, model writes and transactions belong in actions, not controllers.
while IFS=: read -r file line _; do
  say "business logic in a controller: $file:$line"
done < <(rg -n --no-heading \
  -e '\b(DB::|->where\(|->save\(\)|->update\(|->delete\(\)|->create\(|Model::)' \
  app/Http/Controllers 2>/dev/null)

# An API controller must have a web counterpart, and vice versa.
for f in $(find app/Http/Controllers/Api -name '*Controller.php' 2>/dev/null); do
  base=$(basename "$f")
  [ -f "app/Http/Controllers/Web/$base" ] || say "no web counterpart for Api/$base"
done
for f in $(find app/Http/Controllers/Web -name '*Controller.php' 2>/dev/null); do
  base=$(basename "$f")
  [ -f "app/Http/Controllers/Api/$base" ] || say "no api counterpart for Web/$base"
done

[ $fail -eq 0 ] && echo "  controllers: clean" || echo "  controllers: violations above"
exit $fail
