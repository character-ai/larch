#!/usr/bin/env bash
# Regression harness for check-plan-size.sh (issue #2670).

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/check-plan-size.sh"
SOFT_KEY="SOFT_TRIGGER""_FIRED"
FILES_KEY="FILES""_COUNT"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

fill_lines() {
    local n="$1"
    local msg="${2:-body line}"
    awk -v n="$n" -v m="$msg" 'BEGIN { for (i = 1; i <= n; i++) print m }'
}

assert_kv_eq() {
    local key="$1" expected="$2" blob="$3"
    local got
    got=$(printf '%s\n' "$blob" | grep "^${key}=" | head -1 | cut -d= -f2- || true)
    [[ "$got" == "$expected" ]] || fail "expected ${key}=${expected}, got ${got} (output: $blob)"
}

assert_no_key() {
    local key="$1" blob="$2"
    if printf '%s\n' "$blob" | grep -q "^${key}="; then
        fail "did not expect ${key} in output: $blob"
    fi
}

run_ok() {
    local d="$1"
    set +e
    if [[ $# -ge 2 ]]; then
        out=$("$SUBJECT" --design-tmpdir "$d" --plan-file "$2")
    else
        out=$("$SUBJECT" --design-tmpdir "$d")
    fi
    rc=$?
    set -e
    [[ "$rc" -eq 0 ]] || fail "expected rc 0 from check-plan-size, got $rc (output: $out)"
    printf '%s' "$out"
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-check-plan-size-root.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

# --- Case 1: no triggers; retired keys are not emitted ---
d="$TMPROOT/c1"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### UPDATED: \`f%s.md\`\n" "$_"; done
    fill_lines 195 'body line'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "" "$out"
assert_no_key "$SOFT_KEY" "$out"
assert_no_key "$FILES_KEY" "$out"

# --- Case 2: plan-body hard ---
d="$TMPROOT/c2"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`z%s\`\n" "$_"; done
    fill_lines 796 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case2 rc"
assert_kv_eq PLAN_LINES 801 "$out"
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "plan-body-lines" "$out"
assert_no_key "$SOFT_KEY" "$out"

# --- Case 3: diff hard ---
d="$TMPROOT/c3"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`q%s\`\n" "$_"; done
    fill_lines 195 'b'
    printf 'diff_lines: 1501\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case3 rc"
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "diff-lines" "$out"

# --- Case 4: hard plan with former soft dimensions only reports hard reasons ---
d="$TMPROOT/c4"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5 6 7 8 9; do printf "### UPDATED: \`t%s\`\n" "$_"; done
    fill_lines 792 'b'
    printf 'diff_lines: 700\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "plan-body-lines" "$out"
assert_no_key "$FILES_KEY" "$out"

# --- Case 5: ten file headings do not emit retired file-count key or trigger ---
d="$TMPROOT/c5"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5 6 7 8 9 10; do printf "### NEW: \`h%s\`\n" "$_"; done
    fill_lines 190 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case5 rc"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "" "$out"
assert_no_key "$FILES_KEY" "$out"
assert_no_key "$SOFT_KEY" "$out"

# --- Case 6: missing plan ---
d="$TMPROOT/c6"
mkdir -p "$d"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case6 expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-plan "$out"

# --- Case 7: argv / usage errors use rc 3 (no PLAN_SIZE_STATUS) ---
set +e
out=$("$SUBJECT" --bogus-flag 2>&1)
rc=$?
set -e
[[ "$rc" -eq 3 ]] || fail "case7 unknown flag expected rc 3 got $rc"
assert_no_key PLAN_SIZE_STATUS "$out"
set +e
out=$("$SUBJECT" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 3 ]] || fail "case7 missing --design-tmpdir expected rc 3 got $rc"

# --- Case 8: bad trailer ---
d="$TMPROOT/c8"
mkdir -p "$d"
printf 'hello\nnot a trailer\n' >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case8 rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"

# --- Case 9: hard boundary equalities ---
d="$TMPROOT/c9a"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 795 'b'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c9a"
assert_kv_eq PLAN_LINES 800 "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
d="$TMPROOT/c9b"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines: 1500\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c9b"
assert_kv_eq DIFF_LINES 1500 "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"

# --- Case 10: zero headings ---
d="$TMPROOT/c10"
mkdir -p "$d"
{ fill_lines 199 'only body'; printf 'diff_lines: 10\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c10"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"

# --- Case 11: multi diff_lines in body ---
d="$TMPROOT/c11"
mkdir -p "$d"
{ printf 'diff_lines: 100\n'; fill_lines 198 'x'; printf 'closing paragraph\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case11 reject"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"
# Accept when trailer is truly final (prose may contain an earlier diff_lines line)
{ fill_lines 199 'x'; printf 'diff_lines: 100\n'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "case11 accept"
assert_kv_eq DIFF_LINES 400 "$out"
assert_kv_eq PLAN_LINES 200 "$out"

# --- Case 12: trailer whitespace must match emit-plan.sh (single space after colon) ---
d="$TMPROOT/c12"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines:\t1\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case12 tab after colon expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"
d="$TMPROOT/c12b"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines:  1\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case12b double space expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"

# --- Case 13: --plan-file override (non-default path) ---
d="$TMPROOT/c13"
mkdir -p "$d"
{
    fill_lines 246 'b'
    printf 'diff_lines: 400\n'
} >"$d/alternate-plan.txt"
out=$(run_ok "$d" "$d/alternate-plan.txt")
assert_kv_eq PLAN_LINES 246 "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"

echo "PASS: test-check-plan-size.sh"
