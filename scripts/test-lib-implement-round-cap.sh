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

lib_helper_returns_zero_when_no_prior_rounds
lib_helper_counts_degraded_rounds_correctly
lib_helper_ignores_non_degraded_rounds
lib_helper_handles_missing_round_artifacts_gracefully

printf 'test-lib-implement-round-cap: all cases passed\n'
