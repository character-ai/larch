#!/usr/bin/env bash
# test-persist-post-plan-keys.sh — Regression harness for persist-post-plan-keys.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LAUNCHER="$SCRIPT_DIR/persist-post-plan-keys.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-persist-post-plan-keys.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    printf '  ok: %s\n' "$1"
    PASS=$((PASS + 1))
}

fail_case() {
    printf 'FAIL: %s\n' "$1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail_case "$label (missing '$needle'; got ${haystack:0:400})"
    fi
}

assert_file_has_line() {
    local file="$1" expected="$2" label="$3"
    if grep -Fxq "$expected" "$file"; then
        pass "$label"
    else
        fail_case "$label (line '$expected' missing from $file)"
    fi
}

assert_file_lacks_line() {
    local file="$1" forbidden="$2" label="$3"
    if grep -Fxq "$forbidden" "$file"; then
        fail_case "$label (forbidden line '$forbidden' present in $file)"
    else
        pass "$label"
    fi
}

make_case() {
    local dir="$1"
    mkdir -p "$dir"
    printf '%s\n' "Plan body content sufficient for a real plan body." > "$dir/plan.txt"
    printf '%s\n' "Feature description body." > "$dir/feature-description.txt"
    {
        printf 'LARCH_TOKEN_SESSION_ID=session-xyz\n'
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=/dev/null\n'
        printf 'KEEP_ME=keep-value\n'
    } > "$dir/session-env.sh"
}

echo "=== missing required flags ==="
set +e
out="$("$LAUNCHER" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "no flags exits 2"; else fail_case "no flags rc=$rc"; fi
assert_contains "$out" "--implement-tmpdir is required" "no flags error names tmpdir"

set +e
out="$("$LAUNCHER" --implement-tmpdir "$TMP" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing plan-file exits 2"; else fail_case "missing plan-file rc=$rc"; fi
assert_contains "$out" "--plan-file is required" "missing plan-file error"

case_dir="$TMP/case1"
make_case "$case_dir"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing feature-file exits 2"; else fail_case "missing feature-file rc=$rc"; fi
assert_contains "$out" "--feature-file is required" "missing feature-file error"

set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing workflow-path exits 2"; else fail_case "missing workflow-path rc=$rc"; fi
assert_contains "$out" "--workflow-path is required" "missing workflow-path error"

echo "=== reject invalid workflow-path ==="
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path BOGUS 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "bad workflow exits 2"; else fail_case "bad workflow rc=$rc"; fi
assert_contains "$out" "must be SIMPLE or HARD, got: BOGUS" "bad workflow error names value"

echo "=== reject unknown option ==="
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE --bogus 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "unknown option exits 2"; else fail_case "unknown option rc=$rc"; fi
assert_contains "$out" "unknown option: --bogus" "unknown option error"

echo "=== reject missing plan-file ==="
case_dir="$TMP/case-missing-plan"
make_case "$case_dir"
rm "$case_dir/plan.txt"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing plan-file exits 2"; else fail_case "missing plan-file rc=$rc"; fi
assert_contains "$out" "--plan-file not found" "missing plan-file error"

echo "=== reject empty plan-file ==="
case_dir="$TMP/case-empty-plan"
make_case "$case_dir"
: > "$case_dir/plan.txt"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "empty plan-file exits 2"; else fail_case "empty plan-file rc=$rc"; fi
assert_contains "$out" "--plan-file is empty" "empty plan-file error"

echo "=== reject missing session-env ==="
case_dir="$TMP/case-no-sessionenv"
make_case "$case_dir"
rm "$case_dir/session-env.sh"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing session-env exits 2"; else fail_case "missing session-env rc=$rc"; fi
assert_contains "$out" "session-env not found" "missing session-env error"

echo "=== reject newline in argument ==="
case_dir="$TMP/case-nl"
make_case "$case_dir"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file $'/tmp/with\nnewline' --workflow-path SIMPLE 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "newline-arg exits 2"; else fail_case "newline-arg rc=$rc"; fi
assert_contains "$out" "contains newline" "newline-arg error"

echo "=== SIMPLE happy path persists all three keys ==="
case_dir="$TMP/case-simple"
make_case "$case_dir"
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE)"
assert_contains "$out" "POST_PLAN_KEYS_PERSISTED=true" "SIMPLE stdout signals success"
assert_file_has_line "$case_dir/session-env.sh" "PLAN_FILE=$case_dir/plan.txt" "SIMPLE PLAN_FILE persisted"
assert_file_has_line "$case_dir/session-env.sh" "FEATURE_FILE=$case_dir/feature-description.txt" "SIMPLE FEATURE_FILE persisted"
assert_file_has_line "$case_dir/session-env.sh" "POST_PLAN_WORKFLOW_PATH=SIMPLE" "SIMPLE POST_PLAN_WORKFLOW_PATH persisted"
assert_file_has_line "$case_dir/session-env.sh" "KEEP_ME=keep-value" "SIMPLE preserves unrelated keys"

echo "=== HARD happy path persists all three keys ==="
case_dir="$TMP/case-hard"
make_case "$case_dir"
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path HARD)"
assert_contains "$out" "POST_PLAN_KEYS_PERSISTED=true" "HARD stdout signals success"
assert_file_has_line "$case_dir/session-env.sh" "POST_PLAN_WORKFLOW_PATH=HARD" "HARD POST_PLAN_WORKFLOW_PATH persisted"

echo "=== re-run replaces existing keys (idempotent) ==="
case_dir="$TMP/case-rerun"
make_case "$case_dir"
"$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE >/dev/null
# Switch to HARD and a different plan file content; PLAN_FILE path stays the same.
"$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path HARD >/dev/null
# Each key should appear exactly once with the latest value.
count_workflow=$(grep -c '^POST_PLAN_WORKFLOW_PATH=' "$case_dir/session-env.sh" || true)
if [[ "$count_workflow" -eq 1 ]]; then pass "re-run leaves exactly one POST_PLAN_WORKFLOW_PATH= line"; else fail_case "re-run POST_PLAN_WORKFLOW_PATH count=$count_workflow"; fi
assert_file_has_line "$case_dir/session-env.sh" "POST_PLAN_WORKFLOW_PATH=HARD" "re-run replaces with HARD"
assert_file_lacks_line "$case_dir/session-env.sh" "POST_PLAN_WORKFLOW_PATH=SIMPLE" "re-run drops old SIMPLE line"

echo "=== anchored filter does not strip unrelated keys with PLAN_FILE in name ==="
case_dir="$TMP/case-anchor"
make_case "$case_dir"
# Add a key whose name CONTAINS but is not exactly PLAN_FILE. A loose (unanchored)
# grep -v PLAN_FILE pattern would erroneously strip these.
{
    printf 'LARCH_PLAN_FILE_HISTORY=keep-1\n'
    printf 'X_FEATURE_FILE_BACKUP=keep-2\n'
    printf 'OLD_POST_PLAN_WORKFLOW_PATH=keep-3\n'
} >> "$case_dir/session-env.sh"
"$LAUNCHER" --implement-tmpdir "$case_dir" --plan-file "$case_dir/plan.txt" --feature-file "$case_dir/feature-description.txt" --workflow-path SIMPLE >/dev/null
assert_file_has_line "$case_dir/session-env.sh" "LARCH_PLAN_FILE_HISTORY=keep-1" "anchor preserves LARCH_PLAN_FILE_HISTORY"
assert_file_has_line "$case_dir/session-env.sh" "X_FEATURE_FILE_BACKUP=keep-2" "anchor preserves X_FEATURE_FILE_BACKUP"
assert_file_has_line "$case_dir/session-env.sh" "OLD_POST_PLAN_WORKFLOW_PATH=keep-3" "anchor preserves OLD_POST_PLAN_WORKFLOW_PATH"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-persist-post-plan-keys.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-persist-post-plan-keys.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
