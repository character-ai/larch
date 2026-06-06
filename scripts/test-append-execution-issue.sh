#!/usr/bin/env bash
# test-append-execution-issue.sh — Regression tests for append-execution-issue.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/append-execution-issue.sh"
TMPDIR_BASE="$(mktemp -d "${TMPDIR:-/tmp}/test-append-execution-issue.XXXXXX")"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

assert_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    /' "$file" || true
    fi
}

assert_section_contains() {
    local label=$1 file=$2 header=$3 needle=$4
    if awk -v header="$header" -v needle="$needle" '
        $0 == header { in_section = 1; next }
        in_section && /^### / { exit }
        in_section && index($0, needle) { found = 1 }
        END { exit found ? 0 : 1 }
    ' "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    /' "$file" || true
    fi
}

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

unknown_out="$TMPDIR_BASE/unknown.out"
set +e
"$SCRIPT" --step 5 >"$unknown_out" 2>&1
unknown_rc=$?
set -e
assert_rc "unknown flag exits 1" "$unknown_rc" 1
assert_contains "unknown flag FAILED" "$unknown_out" "FAILED=true"
assert_contains "unknown flag ERROR" "$unknown_out" "ERROR=usage: unknown flag: --step"
assert_contains "unknown flag USAGE" "$unknown_out" "USAGE=append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)"

missing_category_out="$TMPDIR_BASE/missing-category.out"
set +e
"$SCRIPT" --log "$TMPDIR_BASE/execution-issues.md" --entry "- **Step 5**: warning" >"$missing_category_out" 2>&1
missing_category_rc=$?
set -e
assert_rc "missing category exits 1" "$missing_category_rc" 1
assert_contains "missing category USAGE" "$missing_category_out" "USAGE=append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)"

happy_log="$TMPDIR_BASE/happy-execution-issues.md"
happy_out="$TMPDIR_BASE/happy.out"
printf '### Tool Failures\n\n- existing failure\n\n### Warnings\n\n- old warning\n\n### Q/A\n\n- existing question\n' > "$happy_log"
"$SCRIPT" --log "$happy_log" --category "Warnings" --entry "- **Step 5**: new warning" >"$happy_out"
assert_contains "happy path APPENDED" "$happy_out" "APPENDED=true"
assert_contains "happy path LOG" "$happy_out" "LOG=$happy_log"
assert_contains "happy path keeps Warnings" "$happy_log" "### Warnings"
assert_contains "happy path keeps following section" "$happy_log" "### Q/A"
assert_section_contains "happy path appends under Warnings" "$happy_log" "### Warnings" "- **Step 5**: new warning"

if [ "$FAIL_COUNT" -ne 0 ]; then
    echo "test-append-execution-issue: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-append-execution-issue: $PASS_COUNT pass(es)"
