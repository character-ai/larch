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

assert_contains "$out" "Total issues: 7" "issue count"
assert_contains "$out" "Tracking/umbrella" "tracking category"
assert_contains "$out" "Bug fix" "bug fix category"
assert_contains "$out" "Documentation/contract drift" "documentation category"
assert_contains "$out" "Hardening/validation/security" "hardening category"
assert_contains "$out" "Auto-spawned share: 1/7" "auto-spawned share"

assert_contains "$out" "W1 duplicate-titled issues opened within 7 days:" "duplicate heading"
assert_contains "$out" "#2 and #6: bug fix: crash in foo" "duplicate title pair"
assert_contains "$out" "W3 [STALLED] issues: 1 total" "stalled issue count"

assert_contains "$out" "Design-phase vote findings:" "vote findings heading"
assert_contains "$out" "#7: codex / generic (YES=2 NO=1 EXONERATE=0)" "vote tally row"
assert_contains "$out" "codex: 1 findings" "codex aggregate"
assert_contains "$out" "codex / generic: 1 findings" "codex generic pair"
assert_not_contains "$out" "- code: 1 findings" "codex not collapsed to code aggregate"
assert_not_contains "$out" "- code / generic:" "codex not collapsed to code persona"

if [[ $FAIL -gt 0 ]]; then
    echo "FAILED ($FAIL of $((PASS + FAIL))):" >&2
    for test_name in "${FAILED_TESTS[@]}"; do
        echo "  - $test_name" >&2
    done
    exit 1
fi

echo "All $PASS assertions passed."
