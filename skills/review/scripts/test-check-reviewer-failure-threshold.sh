#!/usr/bin/env bash
# test-check-reviewer-failure-threshold.sh — regression harness.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET="$SCRIPT_DIR/check-reviewer-failure-threshold.sh"

FAIL=0
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/test-check-threshold.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT

emit_records() {
    local file="$1"; shift
    : > "$file"
    for status in "$@"; do
        {
            printf 'REVIEWER_FILE=%s/dummy\n' "$WORKDIR"
            printf 'TOOL=test\n'
            printf 'STATUS=%s\n' "$status"
            printf 'EXIT_CODE=0\n'
            printf '\n'
        } >> "$file"
    done
}

assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %q want %q\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

run_case() {
    local label="$1" panel="$2"; shift 2
    local extra_args=()
    while [[ $# -gt 0 && "$1" == --* ]]; do
        extra_args+=("$1" "$2"); shift 2
    done
    local records=("$@")
    local file="$WORKDIR/${label}.env"
    local out="$WORKDIR/${label}.out"
    emit_records "$file" "${records[@]+"${records[@]}"}"
    "$TARGET" --collector-results-file "$file" --panel "$panel" \
        "${extra_args[@]+"${extra_args[@]}"}" 3>"$out"
    cat "$out"
}

echo "# HARD panel — all OK"
out=$(run_case all_ok_hard hard OK OK OK OK OK OK OK OK OK OK OK OK 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "all-OK HARD → THRESHOLD_OK=true" "$got" "true"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "all-OK HARD → FAILED_SLOTS=0" "$got" "0"

echo "# HARD panel — exactly half fail (6 of 12) → still OK (>50% required)"
out=$(run_case half_fail_hard hard OK OK OK OK OK OK timeout timeout timeout timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "6/12 fail HARD → OK (not >50%)" "$got" "true"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "6/12 → FAILED_SLOTS=6" "$got" "6"

echo "# HARD panel — 7 of 12 fail → just over threshold"
out=$(run_case over_half_hard hard OK OK OK OK OK timeout timeout timeout timeout timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "7/12 fail HARD → THRESHOLD_OK=false" "$got" "false"

echo "# HARD panel — all 12 fail → fail"
out=$(run_case all_fail_hard hard timeout timeout timeout timeout timeout timeout timeout timeout timeout timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "12/12 fail HARD → THRESHOLD_OK=false" "$got" "false"

echo "# SIMPLE panel — 3 of 7 fail (still under threshold)"
out=$(run_case under_simple simple OK OK OK OK timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "3/7 fail SIMPLE → OK" "$got" "true"

echo "# SIMPLE panel — 4 of 7 fail → just over"
out=$(run_case over_simple simple OK OK OK timeout timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "4/7 fail SIMPLE → THRESHOLD_OK=false" "$got" "false"

echo "# cap_hit counts as success"
out=$(run_case cap_hit hard OK OK OK OK OK OK OK OK OK OK OK cap_hit 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="SUCCEEDED_SLOTS"{print $2}')
assert_eq "cap_hit counted as success" "$got" "12"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "cap_hit not counted as failure" "$got" "0"

echo "# never-launched slots count as failures (via --launched-slots)"
out=$(run_case never_launched hard --launched-slots 6 OK OK OK OK OK OK 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "6 OK launched + 6 never-launched → FAILED_SLOTS=6" "$got" "6"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "6 failed-via-not-launched → still OK (not >50%)" "$got" "true"

echo "# both-down: zero records, zero launched"
out=$(run_case both_down hard --launched-slots 0 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "0 launched of 12 → FAILED_SLOTS=12" "$got" "12"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "0 launched → THRESHOLD_OK=false" "$got" "false"

echo "# dynamic slots widen the denominator"
out=$(run_case dynamic_hard hard --launched-slots 16 OK OK OK OK OK OK OK OK OK timeout timeout timeout timeout timeout timeout timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="INTENDED_SLOTS"{print $2}')
assert_eq "dynamic launched slots widen intended denominator" "$got" "16"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "7/16 fail dynamic HARD → still OK" "$got" "true"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-check-reviewer-failure-threshold.sh\n'
    exit 0
else
    printf 'FAIL: test-check-reviewer-failure-threshold.sh\n'
    exit 1
fi
