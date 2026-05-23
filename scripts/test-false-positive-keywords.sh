#!/usr/bin/env bash
# Regression harness for scripts/false-positive-keywords.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LIB="$REPO_ROOT/scripts/false-positive-keywords.sh"

if [[ ! -f "$LIB" ]]; then
    echo "ERROR: missing library: $LIB" >&2
    exit 1
fi

# shellcheck source=scripts/false-positive-keywords.sh
# shellcheck disable=SC1090
source "$LIB"

PASS=0
FAIL=0
FAILED_TESTS=()

record_pass() {
    PASS=$((PASS + 1))
    echo "  ok: $1"
}

record_fail() {
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$1")
    echo "  FAIL: $1" >&2
}

assert_match() {
    local label="$1" text="$2" rc=0
    matches_false_positive_keywords "$text" || rc=$?
    if [ "$rc" -eq 0 ]; then
        record_pass "$label"
    else
        record_fail "$label (expected match, rc=$rc)"
    fi
}

assert_no_match() {
    local label="$1" text="$2" rc=0
    matches_false_positive_keywords "$text" || rc=$?
    if [ "$rc" -eq 1 ]; then
        record_pass "$label"
    else
        record_fail "$label (expected no match, rc=$rc)"
    fi
}

echo "=== positive fixtures ==="
assert_match "straight apostrophe won't fix" "Closing because this won't fix the underlying issue."
assert_match "curly apostrophe won't fix" "Closing because this won’t fix the underlying issue."
assert_match "wontfix compact" "wontfix: this is unsupported."
assert_match "superseded bare" "This has been superseded by the new workflow."
assert_match "superseded by issue" "Superseded by #42."
assert_match "not an issue" "After triage, this is not an issue."
assert_match "not a bug" "Closing: not a bug after checking the implementation."
assert_match "duplicate of issue" "Duplicate of #42."
assert_match "false positive spaced" "This report is a false positive."
assert_match "false positive hyphenated" "This report is false-positive noise."
assert_match "mixed case mid sentence" "We found this was a False Positive after review."

echo ""
echo "=== negative fixtures ==="
assert_no_match "not a duplicate" "This is not a duplicate; it is still a real issue."
assert_no_match "not duplicate" "This is not duplicate of the other report."
assert_no_match "not a false positive" "This is not a false positive and should stay open."
assert_no_match "deduplicated prose" "The deduplicated counter increased."
assert_no_match "bare duplicate" "This may be duplicate but needs investigation."
assert_no_match "benign close" "Closing after the requested work completed."

echo ""
echo "=== helper failure fixture ==="
failure_dir=$(mktemp -d "${TMPDIR:-/tmp}/test-false-positive-keywords-path-XXXXXX")
stderr_file="$failure_dir/stderr.log"
set +e
PATH="$failure_dir" /bin/bash -c "source '$LIB'; matches_false_positive_keywords 'wontfix'" 2>"$stderr_file"
failure_rc=$?
set -e
if [ "$failure_rc" -ge 2 ]; then
    record_pass "grep helper failure propagates rc >= 2"
else
    record_fail "grep helper failure expected rc >= 2, got $failure_rc"
fi
if grep -q 'grep failed' "$stderr_file"; then
    record_pass "helper failure emits diagnostic"
else
    record_fail "helper failure diagnostic missing"
fi
rm -rf "$failure_dir"

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if (( FAIL > 0 )); then
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
echo "All assertions passed."
