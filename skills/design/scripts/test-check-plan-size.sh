#!/usr/bin/env bash
# Regression harness for check-plan-size.sh (issue #2670).

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/check-plan-size.sh"

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

run_ok() {
    local d="$1"
    set +e
    out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
    rc=$?
    set -e
    [[ "$rc" -eq 0 ]] || fail "expected rc 0 from check-plan-size, got $rc (output: $out)"
    printf '%s' "$out"
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-check-plan-size-root.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

# --- Case 1: no triggers ---
d="$TMPROOT/c1"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### UPDATED: \`f%s.md\`\n" "$_"; done
    fill_lines 195 'body line'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "" "$out"
assert_kv_eq FILES_COUNT 5 "$out"

# --- Case 2: plan-body soft (251 lines) ---
d="$TMPROOT/c2"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`x%s\`\n" "$_"; done
    fill_lines 246 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq PLAN_LINES 251 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED true "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "plan-body-lines" "$out"

# --- Case 3: diff soft ---
d="$TMPROOT/c3"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`p%s\`\n" "$_"; done
    fill_lines 195 'b'
    printf 'diff_lines: 601\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq SOFT_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "diff-lines" "$out"

# --- Case 4: files soft (9 headings) ---
d="$TMPROOT/c4"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5 6 7 8 9; do printf "### REWRITTEN: \`h%s\`\n" "$_"; done
    fill_lines 191 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case4 rc"
assert_kv_eq FILES_COUNT 9 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "files-count" "$out"

# --- Case 5: multiple soft ---
d="$TMPROOT/c5"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5 6 7 8 9; do printf "### NEW: \`m%s\`\n" "$_"; done
    fill_lines 242 'b'
    printf 'diff_lines: 601\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case5 rc"
assert_kv_eq TRIGGER_REASONS "plan-body-lines,diff-lines,files-count" "$out"

# --- Case 6: plan-body hard ---
d="$TMPROOT/c6"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`z%s\`\n" "$_"; done
    fill_lines 796 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case6 rc"
assert_kv_eq PLAN_LINES 801 "$out"
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "plan-body-lines" "$out"

# --- Case 7: diff hard ---
d="$TMPROOT/c7"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`q%s\`\n" "$_"; done
    fill_lines 195 'b'
    printf 'diff_lines: 1501\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "case7 rc"
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq TRIGGER_REASONS "diff-lines" "$out"

# --- Case 8: hard + soft dimensions ---
d="$TMPROOT/c8"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5 6 7 8 9; do printf "### UPDATED: \`t%s\`\n" "$_"; done
    fill_lines 792 'b'
    printf 'diff_lines: 700\n'
} >"$d/plan.txt"
out=$(run_ok "$d")
assert_kv_eq HARD_TRIGGER_FIRED true "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
assert_kv_eq TRIGGER_REASONS "plan-body-lines,diff-lines,files-count" "$out"

# --- Case 9: missing plan ---
d="$TMPROOT/c9"
mkdir -p "$d"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case9 expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-plan "$out"

# --- Case 8b: argv / usage errors use rc 3 (no PLAN_SIZE_STATUS) ---
set +e
out=$("$SUBJECT" --bogus-flag 2>&1)
rc=$?
set -e
[[ "$rc" -eq 3 ]] || fail "case8b unknown flag expected rc 3 got $rc"
if printf '%s\n' "$out" | grep -q '^PLAN_SIZE_STATUS='; then
    fail "case8b did not expect PLAN_SIZE_STATUS in output: $out"
fi
set +e
out=$("$SUBJECT" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 3 ]] || fail "case8b missing --design-tmpdir expected rc 3 got $rc"

# --- Case 10: bad trailer ---
d="$TMPROOT/c10"
mkdir -p "$d"
printf 'hello\nnot a trailer\n' >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case10 rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"

# --- Case 11: boundary equalities ---
# 11a 250 lines — no soft plan
d="$TMPROOT/c11a"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 245 'b'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11a"
assert_kv_eq PLAN_LINES 250 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
# 11b diff 600 — no soft diff
d="$TMPROOT/c11b"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines: 600\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11b"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
# 11b2 diff_lines trailer is zero — valid trailer, no soft diff on zero alone
d="$TMPROOT/c11b2"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines: 0\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11b2"
assert_kv_eq DIFF_LINES 0 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
# 11c 8 headings — no soft files
d="$TMPROOT/c11c"
mkdir -p "$d"
{ for _ in 1 2 3 4 5 6 7 8; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 192 'b'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11c"
assert_kv_eq FILES_COUNT 8 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"
# 11d 800 body lines — no hard plan
d="$TMPROOT/c11d"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 795 'b'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11d"
assert_kv_eq PLAN_LINES 800 "$out"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"
# 11e diff 1500 — no hard diff
d="$TMPROOT/c11e"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines: 1500\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c11e"
assert_kv_eq HARD_TRIGGER_FIRED false "$out"

# --- Case 12: zero headings ---
d="$TMPROOT/c12"
mkdir -p "$d"
{ fill_lines 199 'only body'; printf 'diff_lines: 10\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "c12"
assert_kv_eq FILES_COUNT 0 "$out"
assert_kv_eq SOFT_TRIGGER_FIRED false "$out"

# --- Case 13: multi diff_lines in body ---
d="$TMPROOT/c13"
mkdir -p "$d"
{ printf 'diff_lines: 100\n'; fill_lines 198 'x'; printf 'closing paragraph\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case13 reject"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"
# Accept when trailer is truly final (prose may contain an earlier diff_lines line)
{ fill_lines 199 'x'; printf 'diff_lines: 100\n'; printf 'diff_lines: 400\n'; } >"$d/plan.txt"
out=$(run_ok "$d") || fail "case13 accept"
assert_kv_eq DIFF_LINES 400 "$out"
assert_kv_eq PLAN_LINES 200 "$out"

# --- Case 14: whitespace-tolerant headings ---
d="$TMPROOT/c14"
mkdir -p "$d"
{
    printf "###  NEW: \`wide1\`\n"
    printf "### UPDATED : \`wide2\`\n"
    fill_lines 198 'b'
    printf 'diff_lines: 1\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "c14"
assert_kv_eq FILES_COUNT 2 "$out"

# --- Case 15: hard (801) — partition simulation per plan ---
d="$TMPROOT/c15"
mkdir -p "$d"
{
    for _ in 1 2 3 4 5; do printf "### NEW: \`s%s\`\n" "$_"; done
    fill_lines 796 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "c15"
assert_kv_eq HARD_TRIGGER_FIRED true "$out"

# --- Case 16: ###NEW: without whitespace after ### does not count ---
d="$TMPROOT/c16"
mkdir -p "$d"
{
    cat <<'EOF'
###NEW: `bad-heading.md`
EOF
    for _ in 1 2 3 4 5; do printf "### NEW: \`ok%s\`\n" "$_"; done
    fill_lines 189 'b'
    printf 'diff_lines: 400\n'
} >"$d/plan.txt"
out=$(run_ok "$d") || fail "c16"
assert_kv_eq FILES_COUNT 5 "$out"

# --- Case 17: trailer whitespace must match emit-plan.sh (single space after colon) ---
d="$TMPROOT/c17"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines:\t1\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case17 tab after colon expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"
d="$TMPROOT/c17b"
mkdir -p "$d"
{ for _ in 1 2 3 4 5; do printf "### NEW: \`a%s\`\n" "$_"; done; fill_lines 195 'b'; printf 'diff_lines:  1\n'; } >"$d/plan.txt"
set +e
out=$("$SUBJECT" --design-tmpdir "$d" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "case17b double space expected rc 2 got $rc"
assert_kv_eq PLAN_SIZE_STATUS missing-diff-lines "$out"

echo "PASS: test-check-plan-size.sh"
