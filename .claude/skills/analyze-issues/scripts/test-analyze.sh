#!/usr/bin/env bash
# test-analyze.sh - behavioral regression harness for analyze.py.
#
# Usage:
#   bash .claude/skills/analyze-issues/scripts/test-analyze.sh
#
# Exit codes:
#   0 - all assertions passed
#   1 - one or more assertions failed

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ANALYZER="$SCRIPT_DIR/analyze.py"
FIXTURE="$SCRIPT_DIR/test-fixture.json"

if [[ ! -r "$ANALYZER" ]]; then
    echo "ERROR: analyzer not readable at $ANALYZER" >&2
    exit 1
fi
if [[ ! -r "$FIXTURE" ]]; then
    echo "ERROR: fixture not readable at $FIXTURE" >&2
    exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (missing $needle)")
        echo "  FAIL: $label (missing $needle)" >&2
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (unexpected $needle)")
        echo "  FAIL: $label (unexpected $needle)" >&2
    fi
}

out=$(python3 "$ANALYZER" --json "$FIXTURE")

assert_contains "$out" "## Executive Summary" "executive summary section"
assert_contains "$out" "## Coverage Stats" "coverage stats section"
assert_contains "$out" "## Category Breakdown" "category breakdown section"
assert_contains "$out" "## Growth Chart" "growth chart section"
assert_contains "$out" "## Pattern Observations" "pattern observations section"
assert_contains "$out" "## Wasteful-work Findings" "wasteful-work findings section"
assert_contains "$out" "## Reviewer/Persona Tables" "reviewer/persona section"

assert_contains "$out" "Total issues: 10" "issue count"
assert_contains "$out" "Tracking/umbrella" "tracking category"
assert_contains "$out" "Bug fix: 3 (" "bug fix category count (pins rule-order; #2/#6 via bug+crash, #10 via 'error' word-boundary; fix-in-fixture / fix-in-prefix no longer alias)"
assert_contains "$out" "Test coverage: 1 (" "test coverage classification (#7 'Test coverage: add fixture' no longer aliased to Bug fix)"
assert_contains "$out" "Other: 1 (" "other category for #8 'prefix handling tweak' (fix-in-prefix no longer aliases)"
assert_contains "$out" "Documentation/contract drift: 2 (" "documentation category (#3 README+contract; #9 'documentation'; #10 'Docker' must NOT match 'doc' -> Documentation)"
assert_contains "$out" "Hardening/validation/security" "hardening category"
assert_contains "$out" "Auto-spawned share: 1/10" "auto-spawned share"

assert_contains "$out" "W1 duplicate-titled issues opened within 7 days:" "duplicate heading"
assert_contains "$out" "#2 and #6: bug fix: crash in foo" "duplicate title pair"
assert_contains "$out" "W3 [STALLED] issues: 1 total" "stalled issue count"

assert_contains "$out" "Design-phase vote findings:" "vote findings heading"
assert_contains "$out" "#7: codex / generic (YES=2 NO=1 EXONERATE=0)" "vote tally row"
assert_contains "$out" "codex: 1 findings" "codex aggregate"
assert_contains "$out" "codex / generic: 1 findings" "codex generic pair"
assert_not_contains "$out" "- code: 1 findings" "codex not collapsed to code aggregate"
assert_not_contains "$out" "- code / generic:" "codex not collapsed to code persona"

# load_issues: stderr warning + threshold abort + --lenient backward compat.
TMP_LOW=$(mktemp -t analyze-low-skip.XXXXXX)
TMP_HIGH=$(mktemp -t analyze-high-skip.XXXXXX)
trap 'rm -f "$TMP_LOW" "$TMP_HIGH"' EXIT

# 1 non-dict in 20 elements = 5% (not exceeding the 5% threshold) -> succeeds with stderr warning.
python3 -c '
import json
items = [
    {"number": i, "title": f"issue {i}", "body": "", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z"}
    for i in range(1, 20)
]
items.append("not a dict")
print(json.dumps(items))
' > "$TMP_LOW"

low_stderr=$(python3 "$ANALYZER" --json "$TMP_LOW" 2>&1 >/dev/null)
assert_contains "$low_stderr" "WARN load_issues: skipping non-dict element at index 19" "load_issues stderr warning at threshold"

# 1 non-dict in 10 elements = 10% > 5% -> aborts (exit non-zero) without --lenient.
python3 -c '
import json
items = [
    {"number": i, "title": f"issue {i}", "body": "", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z"}
    for i in range(1, 10)
]
items.append("not a dict")
print(json.dumps(items))
' > "$TMP_HIGH"

if python3 "$ANALYZER" --json "$TMP_HIGH" >/dev/null 2>&1; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("load_issues threshold abort: 10% non-dict should fail without --lenient")
    echo "  FAIL: load_issues threshold abort: 10% non-dict should fail without --lenient" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: load_issues threshold abort fires above 5%"
fi

# --lenient suppresses the threshold abort and still produces the report.
lenient_out=$(python3 "$ANALYZER" --json "$TMP_HIGH" --lenient 2>/dev/null) || lenient_out=""
assert_contains "$lenient_out" "Total issues: 9" "--lenient: report renders 9 valid dicts past 10% threshold"
assert_contains "$lenient_out" "## Executive Summary" "--lenient: report includes Executive Summary"

if [[ $FAIL -gt 0 ]]; then
    echo "FAILED ($FAIL of $((PASS + FAIL))):" >&2
    for test_name in "${FAILED_TESTS[@]}"; do
        echo "  - $test_name" >&2
    done
    exit 1
fi

echo "All $PASS assertions passed."
