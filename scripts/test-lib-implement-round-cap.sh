#!/usr/bin/env bash
# Offline harness for scripts/lib-implement-round-cap.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIB="$REPO_ROOT/scripts/lib-implement-round-cap.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-lib-implement-round-cap.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# shellcheck source=scripts/lib-implement-round-cap.sh
source "$LIB"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

pass() {
    printf 'ok: %s\n' "$1"
}

lib_helper_returns_zero_when_no_prior_rounds() {
    local got
    got="$(count_prior_degraded_rounds "$TMP" 1)"
    [[ "$got" == "0" ]] || fail "expected 0 for current_round=1 empty tmpdir, got $got"
    pass "lib_helper_returns_zero_when_no_prior_rounds"
}

lib_helper_counts_degraded_rounds_correctly() {
    mkdir -p "$TMP/round-1" "$TMP/round-2" "$TMP/round-3"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-1/review-and-fix.env"
    printf 'DEGRADED_ROUND=false\n' > "$TMP/round-2/review-and-fix.env"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-3/review-and-fix.env"
    local got
    got="$(count_prior_degraded_rounds "$TMP" 4)"
    [[ "$got" == "2" ]] || fail "expected 2 degraded in rounds 1-3 for current_round=4, got $got"
    pass "lib_helper_counts_degraded_rounds_correctly"
}

lib_helper_ignores_non_degraded_rounds() {
    mkdir -p "$TMP/round-1" "$TMP/round-2"
    printf 'DEGRADED_ROUND=false\n' > "$TMP/round-1/review-and-fix.env"
    printf 'DEGRADED_ROUND=false\n' > "$TMP/round-2/review-and-fix.env"
    local got
    got="$(count_prior_degraded_rounds "$TMP" 3)"
    [[ "$got" == "0" ]] || fail "expected 0, got $got"
    pass "lib_helper_ignores_non_degraded_rounds"
}

lib_helper_handles_missing_round_artifacts_gracefully() {
    mkdir -p "$TMP/round-2"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-2/review-and-fix.env"
    local got
    got="$(count_prior_degraded_rounds "$TMP" 3)"
    [[ "$got" == "1" ]] || fail "missing round-1 should count as 0; expected 1 from round-2 only, got $got"
    pass "lib_helper_handles_missing_round_artifacts_gracefully"
}

cli_counts_degraded_rounds_correctly() {
    mkdir -p "$TMP/round-1" "$TMP/round-2" "$TMP/round-3" "$TMP/round-4"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-1/review-and-fix.env"
    printf 'DEGRADED_ROUND=false\n' > "$TMP/round-2/review-and-fix.env"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-3/review-and-fix.env"
    printf 'DEGRADED_ROUND=true\n' > "$TMP/round-4/review-and-fix.env"
    local got
    got="$("$LIB" --count-prior-degraded "$TMP" 4)"
    [[ "$got" == "2" ]] || fail "expected CLI count 2 for rounds 1-3, got $got"
    pass "cli_counts_degraded_rounds_correctly"
}

cli_returns_zero_for_fresh_round_one() {
    local got
    got="$("$LIB" --count-prior-degraded "$TMP" 1)"
    [[ "$got" == "0" ]] || fail "expected CLI count 0 for round 1, got $got"
    pass "cli_returns_zero_for_fresh_round_one"
}

assert_cli_usage() {
    local label=$1
    local stdout_file="$TMP/cli-usage.out"
    local stderr_file="$TMP/cli-usage.err"
    local rc
    shift
    set +e
    "$LIB" "$@" >"$stdout_file" 2>"$stderr_file"
    rc=$?
    set -e
    [[ "$rc" == "2" ]] || fail "$label expected rc=2, got $rc"
    grep -Fq 'usage: lib-implement-round-cap.sh --count-prior-degraded <IMPLEMENT_TMPDIR> <current_round>' "$stderr_file" || fail "$label missing usage"
    pass "$label"
}

lib_helper_returns_zero_when_no_prior_rounds
lib_helper_counts_degraded_rounds_correctly
lib_helper_ignores_non_degraded_rounds
lib_helper_handles_missing_round_artifacts_gracefully
cli_counts_degraded_rounds_correctly
cli_returns_zero_for_fresh_round_one
assert_cli_usage "cli_missing_arg_exits_usage" --count-prior-degraded "$TMP"
assert_cli_usage "cli_non_integer_round_exits_usage" --count-prior-degraded "$TMP" nope
assert_cli_usage "cli_non_positive_round_exits_usage" --count-prior-degraded "$TMP" 0

printf 'test-lib-implement-round-cap: all cases passed\n'
