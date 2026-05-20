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
    local raw_status status reviewer_file
    : > "$file"
    for raw_status in "$@"; do
        status="$raw_status"
        reviewer_file="$WORKDIR/dummy"
        if [[ "$raw_status" == dyn:* ]]; then
            status="${raw_status#dyn:}"
            reviewer_file="$WORKDIR/dyn-extra-output.txt"
        elif [[ "$raw_status" == dyn-phase2:* ]]; then
            status="${raw_status#dyn-phase2:}"
            reviewer_file="$WORKDIR/dyn-extra-output-phase2.txt"
        elif [[ "$raw_status" == dyn-phase3:* ]]; then
            status="${raw_status#dyn-phase3:}"
            reviewer_file="$WORKDIR/dyn-extra-output-phase3.txt"
        elif [[ "$raw_status" == dyn-retry:* ]]; then
            status="${raw_status#dyn-retry:}"
            reviewer_file="$WORKDIR/dyn-extra-output-retry.txt"
        fi
        {
            printf 'REVIEWER_FILE=%s\n' "$reviewer_file"
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

echo "# round 2+ hard panel uses a 6-slot intended denominator"
out=$(run_case round2_hard hard --round-num 2 --launched-slots 6 OK OK OK OK OK timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="INTENDED_SLOTS"{print $2}')
assert_eq "round2 HARD → INTENDED_SLOTS=6" "$got" "6"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "round2 HARD one real failure stays one failure" "$got" "1"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "round2 HARD 1/6 fail → THRESHOLD_OK=true" "$got" "true"

echo "# both-down: zero records, zero launched"
out=$(run_case both_down hard --launched-slots 0 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "0 launched of 12 → FAILED_SLOTS=12" "$got" "12"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "0 launched → THRESHOLD_OK=false" "$got" "false"

echo "# round 2+ both-down: zero records, zero launched"
out=$(run_case both_down_round2 hard --round-num 2 --launched-slots 0 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="INTENDED_SLOTS"{print $2}')
assert_eq "round2 0 launched → INTENDED_SLOTS=6" "$got" "6"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "round2 0 launched of 6 → FAILED_SLOTS=6" "$got" "6"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "round2 0 launched → THRESHOLD_OK=false" "$got" "false"

echo "# dynamic slots are excluded from the static threshold math"
out=$(run_case dynamic_hard hard --launched-slots 16 \
    OK OK OK OK OK OK OK OK OK timeout timeout timeout \
    dyn:timeout dyn:timeout dyn:timeout dyn:timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="INTENDED_SLOTS"{print $2}')
assert_eq "dynamic slots do not widen intended denominator" "$got" "12"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "3/12 static fail dynamic HARD reviewers ignored → still OK" "$got" "true"
got=$(printf '%s\n' "$out" | awk -F= '$1=="COUNTED_SLOTS"{print $2}')
assert_eq "only static slots are counted when dynamic reviewer files are present" "$got" "12"

echo "# dynamic fallback basenames are still excluded from static failure accounting"
out=$(run_case dynamic_fallback_names hard --launched-slots 12 \
    OK OK OK OK OK OK OK OK OK timeout timeout timeout \
    dyn-phase2:timeout dyn-phase3:timeout dyn-retry:timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="COUNTED_SLOTS"{print $2}')
assert_eq "dynamic phase2/phase3/retry outputs do not enter counted slots" "$got" "12"
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "only static failures contribute when dynamic fallback outputs fail" "$got" "3"

echo "# NOT_SUBSTANTIVE slots are counted as failed AND tracked separately"
out=$(run_case not_substantive simple --launched-slots 7 \
    OK OK OK OK OK NOT_SUBSTANTIVE NOT_SUBSTANTIVE 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "NOT_SUBSTANTIVE counts as failed" "$got" "2"
got=$(printf '%s\n' "$out" | awk -F= '$1=="NOT_SUBSTANTIVE_SLOTS"{print $2}')
assert_eq "NOT_SUBSTANTIVE_SLOTS count emitted" "$got" "2"
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "2 of 7 NOT_SUBSTANTIVE → threshold OK (not >50%)" "$got" "true"

echo "# 4 NOT_SUBSTANTIVE of 7 → threshold fails"
out=$(run_case not_substantive_majority simple --launched-slots 7 \
    OK OK OK NOT_SUBSTANTIVE NOT_SUBSTANTIVE NOT_SUBSTANTIVE NOT_SUBSTANTIVE 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="THRESHOLD_OK"{print $2}')
assert_eq "4 of 7 NOT_SUBSTANTIVE → threshold fails" "$got" "false"
got=$(printf '%s\n' "$out" | awk -F= '$1=="NOT_SUBSTANTIVE_SLOTS"{print $2}')
assert_eq "NOT_SUBSTANTIVE_SLOTS=4 emitted on majority-fail path" "$got" "4"

echo "# mixed NOT_SUBSTANTIVE and other failures"
out=$(run_case mixed_failures simple --launched-slots 7 \
    OK OK OK NOT_SUBSTANTIVE FAILED NOT_SUBSTANTIVE timeout 2>&1)
got=$(printf '%s\n' "$out" | awk -F= '$1=="FAILED_SLOTS"{print $2}')
assert_eq "mixed: all non-OK count as failed" "$got" "4"
got=$(printf '%s\n' "$out" | awk -F= '$1=="NOT_SUBSTANTIVE_SLOTS"{print $2}')
assert_eq "mixed: only NOT_SUBSTANTIVE counted in NOT_SUBSTANTIVE_SLOTS" "$got" "2"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-check-reviewer-failure-threshold.sh\n'
    exit 0
else
    printf 'FAIL: test-check-reviewer-failure-threshold.sh\n'
    exit 1
fi
