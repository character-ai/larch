#!/usr/bin/env bash
# test-session-entry-gate.sh — Regression test for scripts/session-entry-gate.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/session-entry-gate.sh"

PASS=0
FAIL=0
FAILED_TESTS=()

fail_case() {
    local label="$1" detail="$2"
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$label ($detail)")
    printf '  FAIL: %s\n       %s\n' "$label" "$detail" >&2
}

pass_case() {
    local label="$1"
    PASS=$((PASS + 1))
    printf '  ok: %s\n' "$label"
}

assert_eq() {
    local got="$1" expected="$2" label="$3"
    if [[ "$got" == "$expected" ]]; then
        pass_case "$label"
    else
        fail_case "$label" "got '$got', expected '$expected'"
    fi
}

assert_empty() {
    local got="$1" label="$2"
    if [[ -z "$got" ]]; then
        pass_case "$label"
    else
        fail_case "$label" "expected empty, got '$got'"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass_case "$label"
    else
        fail_case "$label" "missing '$needle' in '$haystack'"
    fi
}

[[ -x "$SCRIPT" ]] || {
    printf 'FAIL: %s does not exist or is not executable\n' "$SCRIPT" >&2
    exit 1
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

run_gate() {
    local label="$1"
    shift
    local out="$tmp/${label//[^A-Za-z0-9_]/_}.out"
    local err="$tmp/${label//[^A-Za-z0-9_]/_}.err"
    local rc=0
    "$SCRIPT" "$@" >"$out" 2>"$err" || rc=$?
    RUN_STDOUT=$(cat "$out")
    RUN_STDERR=$(cat "$err")
    RUN_RC="$rc"
}

expect_success() {
    local label="$1" expected_gate="$2" expected_skip="$3"
    shift 3
    printf '=== %s ===\n' "$label"
    run_gate "$label" "$@"
    local expected_stdout
    expected_stdout=$(printf 'ENTRY_GATE=%s\nSKIP_BRANCH_CHECK=%s' "$expected_gate" "$expected_skip")
    assert_eq "$RUN_RC" "0" "$label: exit code 0"
    assert_eq "$RUN_STDOUT" "$expected_stdout" "$label: exact stdout"
    assert_empty "$RUN_STDERR" "$label: stderr empty"
    if [[ "$expected_gate" == "continue" ]]; then
        assert_eq "$expected_skip" "true" "$label: continue implies skip"
    else
        assert_eq "$expected_skip" "false" "$label: strict implies no skip"
    fi
}

expect_failure() {
    local label="$1" expected_substring="$2"
    shift 2
    printf '=== %s ===\n' "$label"
    run_gate "$label" "$@"
    assert_eq "$RUN_RC" "4" "$label: exit code 4"
    assert_empty "$RUN_STDOUT" "$label: stdout empty"
    assert_contains "$RUN_STDERR" "GATE_ERROR=" "$label: stderr has GATE_ERROR"
    assert_contains "$RUN_STDERR" "$expected_substring" "$label: stderr has expected reason"
}

expect_success "1 implement main strict" strict false \
    --mode implement --current-branch main --is-main true --is-user-branch false --user-prefix sergey
expect_success "2 implement user branch continue" continue true \
    --mode implement --current-branch sergey/foo --is-main false --is-user-branch true --user-prefix sergey
expect_success "3 implement random branch strict" strict false \
    --mode implement --current-branch random-branch --is-main false --is-user-branch false --user-prefix sergey
expect_success "4 implement detached strict" strict false \
    --mode implement --current-branch "" --is-main true --is-user-branch false --user-prefix sergey
expect_success "5 design user branch continue" continue true \
    --mode design --current-branch sergey/foo --is-main false --is-user-branch true --user-prefix sergey --branch-info-supplied false
expect_success "6 design nested main continue" continue true \
    --mode design --current-branch main --is-main true --is-user-branch false --user-prefix sergey --branch-info-supplied true
expect_success "7 design main strict" strict false \
    --mode design --current-branch main --is-main true --is-user-branch false --user-prefix sergey --branch-info-supplied false
expect_success "8 design random branch strict" strict false \
    --mode design --current-branch random-branch --is-main false --is-user-branch false --user-prefix sergey --branch-info-supplied false
expect_success "9 design nested detached continue" continue true \
    --mode design --current-branch "" --is-main true --is-user-branch false --user-prefix sergey --branch-info-supplied true

expect_failure "10 invalid mode" "invalid mode" \
    --mode foo --current-branch main --is-main true --is-user-branch false --user-prefix sergey
expect_failure "11 missing mode" "missing required flag --mode" \
    --current-branch main --is-main true --is-user-branch false --user-prefix sergey
expect_failure "12 mode missing value" "missing value for --mode" \
    --mode
expect_failure "13 invalid is-main" "invalid value for --is-main" \
    --mode implement --current-branch main --is-main yes --is-user-branch false --user-prefix sergey
expect_failure "14 invalid empty is-user-branch" "invalid value for --is-user-branch" \
    --mode implement --current-branch main --is-main true --is-user-branch "" --user-prefix sergey
expect_failure "15 is-main missing value" "missing value for --is-main" \
    --mode implement --current-branch main --is-main
expect_failure "16 missing current branch" "missing required flag --current-branch" \
    --mode implement --is-main true --is-user-branch false --user-prefix sergey
expect_failure "17 empty user prefix" "--user-prefix must be non-empty" \
    --mode implement --current-branch main --is-main true --is-user-branch false --user-prefix ""
expect_failure "18 missing user prefix" "missing required flag --user-prefix" \
    --mode implement --current-branch main --is-main true --is-user-branch false
expect_failure "19 implement branch-info true" "--branch-info-supplied not allowed for mode=implement" \
    --mode implement --current-branch main --is-main true --is-user-branch false --user-prefix sergey --branch-info-supplied true
expect_failure "20 implement branch-info false" "--branch-info-supplied not allowed for mode=implement" \
    --mode implement --current-branch main --is-main true --is-user-branch false --user-prefix sergey --branch-info-supplied false
expect_failure "21 unknown flag" "unknown flag: --bogus" \
    --mode implement --current-branch main --is-main true --is-user-branch false --user-prefix sergey --bogus

printf '\n=== Summary ===\n'
printf '  passed: %s\n' "$PASS"
printf '  failed: %s\n' "$FAIL"
if [[ $FAIL -gt 0 ]]; then
    printf '\nFailed tests:\n' >&2
    for failed in "${FAILED_TESTS[@]}"; do
        printf '  - %s\n' "$failed" >&2
    done
    exit 1
fi

printf 'all tests passed\n'
exit 0
