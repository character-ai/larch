#!/usr/bin/env bash
# Hermetic regression for the jq title filter in
# .claude/skills/combine-issues/scripts/fetch-combinable-issues.sh — must stay in sync.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
FILTER_FILE="$REPO_ROOT/.claude/skills/combine-issues/scripts/combinable-issues-title-filter.jq"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$FILTER_FILE" ]] || fail "missing filter file: $FILTER_FILE"

SAMPLE='[
  {"number":1,"title":"[DESIGNED] open design","body":"","labels":[]},
  {"number":2,"title":"[DESIGNING] wip","body":"","labels":[]},
  {"number":3,"title":"[IMPLEMENTING] impl","body":"","labels":[]},
  {"number":4,"title":"[STALLED] stuck","body":"","labels":[]},
  {"number":5,"title":"[DONE] shipped","body":"","labels":[]},
  {"number":6,"title":"[LOCKED] hold","body":"","labels":[]},
  {"number":7,"title":"Plain eligible","body":"","labels":[]},
  {"number":8,"title":"[IN PROGRESS] legacy","body":"","labels":[]},
  {"number":9,"title":"[PLANNED] legacy","body":"","labels":[]}
]'

out=$(printf '%s' "$SAMPLE" | jq -c -f "$FILTER_FILE" 2>/dev/null) || fail "jq filter failed"

# Expect only [DESIGNED] and Plain eligible (numbers 1 and 7)
n=$(printf '%s' "$out" | jq 'length')
[[ "$n" == "2" ]] || fail "expected 2 issues, got $n: $out"

nums=$(printf '%s' "$out" | jq -r 'map(.number) | sort | join(",")')
[[ "$nums" == "1,7" ]] || fail "expected numbers 1,7 got $nums"

echo "PASS: fetch-combinable-issues jq filter"

# --- OOS filter ---
OOS_FILTER_FILE="$REPO_ROOT/.claude/skills/combine-issues/scripts/oos-issues-title-filter.jq"
[[ -f "$OOS_FILTER_FILE" ]] || fail "missing OOS filter file: $OOS_FILTER_FILE"

OOS_SAMPLE='[
  {"number":1,"title":"[OOS] some finding","body":"","labels":[]},
  {"number":2,"title":"[OOS] another finding","body":"","labels":[]},
  {"number":3,"title":"[DESIGNED] not oos","body":"","labels":[]},
  {"number":4,"title":"Plain issue","body":"","labels":[]},
  {"number":5,"title":"has [OOS] in middle","body":"","labels":[]},
  {"number":6,"title":"[IMPLEMENTING] impl","body":"","labels":[]}
]'

oos_out=$(printf '%s' "$OOS_SAMPLE" | jq -c -f "$OOS_FILTER_FILE" 2>/dev/null) || fail "OOS jq filter failed"

# Expect only the two [OOS]-prefixed issues (numbers 1 and 2)
oos_n=$(printf '%s' "$oos_out" | jq 'length')
[[ "$oos_n" == "2" ]] || fail "OOS filter: expected 2 issues, got $oos_n: $oos_out"

oos_nums=$(printf '%s' "$oos_out" | jq -r 'map(.number) | sort | join(",")')
[[ "$oos_nums" == "1,2" ]] || fail "OOS filter: expected numbers 1,2 got $oos_nums"

echo "PASS: oos-issues-title-filter jq filter"
exit 0
