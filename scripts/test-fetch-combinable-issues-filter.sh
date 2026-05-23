#!/usr/bin/env bash
# Hermetic regression for the jq title filter in
# .claude/skills/combine-issues/scripts/fetch-combinable-issues.sh — must stay in sync.
set -euo pipefail

FILTER='[
  .[] |
  select(
    (.title | test("^\\[(DESIGNING|IMPLEMENTING|STALLED|DONE)\\] ") | not) and
    (.title | test("^\\[LOCKED\\]") | not)
  )
]'

fail() { echo "FAIL: $1" >&2; exit 1; }

SAMPLE='[
  {"number":1,"title":"[DESIGNED] open design","body":"","labels":[]},
  {"number":2,"title":"[DESIGNING] wip","body":"","labels":[]},
  {"number":3,"title":"[IMPLEMENTING] impl","body":"","labels":[]},
  {"number":4,"title":"[STALLED] stuck","body":"","labels":[]},
  {"number":5,"title":"[DONE] shipped","body":"","labels":[]},
  {"number":6,"title":"[LOCKED] hold","body":"","labels":[]},
  {"number":7,"title":"Plain eligible","body":"","labels":[]}
]'

out=$(printf '%s' "$SAMPLE" | jq -c "$FILTER" 2>/dev/null) || fail "jq filter failed"

# Expect only [DESIGNED] and Plain eligible (numbers 1 and 7)
n=$(printf '%s' "$out" | jq 'length')
[[ "$n" == "2" ]] || fail "expected 2 issues, got $n: $out"

nums=$(printf '%s' "$out" | jq -r 'map(.number) | sort | join(",")')
[[ "$nums" == "1,7" ]] || fail "expected numbers 1,7 got $nums"

echo "PASS: fetch-combinable-issues jq filter"
exit 0
