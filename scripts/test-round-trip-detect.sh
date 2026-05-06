#!/usr/bin/env bash
# test-round-trip-detect.sh — regression harness for round-trip-detect.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DETECT="$REPO_ROOT/scripts/round-trip-detect.sh"
NEG_FIXTURES="$REPO_ROOT/scripts/test-round-trip-detect-negative-fixtures.txt"

PASS=0
FAIL=0
FAILED_TESTS=()

assert_equal() {
    local actual="$1" expected="$2" label="$3"
    if [ "$actual" = "$expected" ]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (expected '$expected', got '$actual')")
        echo "  FAIL: $label (expected '$expected', got '$actual')" >&2
    fi
}

run_detect() {
    "$DETECT" "$@"
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-round-trip-detect-XXXXXX")
# shellcheck disable=SC2317
trap 'rm -rf "$TMPROOT"' EXIT

echo "=== positives ==="
assert_equal "$(run_detect --text-string 'was reverted in 1a2b3c4')" "ROUND_TRIP=true" "7-char reverted SHA"
assert_equal "$(run_detect --text-string 'was reverted in 1234567890abcdef1234567890abcdef12345678')" "ROUND_TRIP=true" "40-char reverted SHA"
assert_equal "$(run_detect --text-string 'please reintroduce the helper')" "ROUND_TRIP=true" "reintroduce"
assert_equal "$(run_detect --text-string 'please re-introduce the helper')" "ROUND_TRIP=true" "re-introduce"
assert_equal "$(run_detect --text-string 'please readd the hook')" "ROUND_TRIP=true" "readd"
assert_equal "$(run_detect --text-string 'please re-add the hook')" "ROUND_TRIP=true" "re-add"
assert_equal "$(run_detect --text-string 'revert of #1240')" "ROUND_TRIP=true" "revert of issue"
assert_equal "$(run_detect --text-string 'revert of abcdef1')" "ROUND_TRIP=true" "revert of SHA"
assert_equal "$(run_detect --text-string 'closed in favor of #1239')" "ROUND_TRIP=true" "closed in favor"
assert_equal "$(run_detect --text-string 'replace standalone with alias')" "ROUND_TRIP=true" "replace standalone with alias"
assert_equal "$(run_detect --text-string 'Please RE-ADD the hook')" "ROUND_TRIP=true" "mixed-case positive"

echo ""
echo "=== file and stdin paths ==="
BODY_FILE="$TMPROOT/body.txt"
printf 'This work was reverted in cafebabe.\n' > "$BODY_FILE"
assert_equal "$(run_detect --text-file "$BODY_FILE")" "ROUND_TRIP=true" "--text-file positive"
assert_equal "$(printf 'closed in favor of #123\n' | run_detect --stdin)" "ROUND_TRIP=true" "--stdin positive"

echo ""
echo "=== negatives ==="
assert_equal "$(run_detect --text-string '')" "ROUND_TRIP=false" "empty input"
assert_equal "$(run_detect --text-string 'prereadditional work')" "ROUND_TRIP=false" "substring negative prereadditional"
assert_equal "$(run_detect --text-string 'preintroduces behavior')" "ROUND_TRIP=false" "substring negative preintroduces"
assert_equal "$(run_detect --text-string 'revertofnothing')" "ROUND_TRIP=false" "substring negative revertofnothing"
assert_equal "$(run_detect --text-file "$NEG_FIXTURES")" "ROUND_TRIP=false" "vendored #1239 negative fixtures"

ERR_FILE="$TMPROOT/err.txt"
OUT=$(run_detect --text-file "$TMPROOT/missing.txt" 2>"$ERR_FILE")
assert_equal "$OUT" "ROUND_TRIP=false" "missing file degrades false"
if grep -q 'warning:' "$ERR_FILE"; then
    PASS=$((PASS + 1))
    echo "  ok: missing file emits warning"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("missing file emits warning")
    echo "  FAIL: missing file warning absent" >&2
fi

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
echo "All assertions passed."
