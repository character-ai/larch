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
    local raw_status status reviewer_file idx=0
    : > "$file"
    for raw_status in "$@"; do
        idx=$((idx + 1))
        status="$raw_status"
        reviewer_file="$WORKDIR/cursor-specialist-security-output.txt"
        case "$raw_status" in
            dyn:*) status="${raw_status#dyn:}"; reviewer_file="$WORKDIR/dyn-extra-output.txt" ;;
            dyn-codex:*) status="${raw_status#dyn-codex:}"; reviewer_file="$WORKDIR/dyn-extra-codex-output.txt" ;;
            dyn-phase2:*) status="${raw_status#dyn-phase2:}"; reviewer_file="$WORKDIR/dyn-extra-output-phase2.txt" ;;
            dyn-phase3:*) status="${raw_status#dyn-phase3:}"; reviewer_file="$WORKDIR/dyn-extra-output-phase3.txt" ;;
            dyn-retry:*) status="${raw_status#dyn-retry:}"; reviewer_file="$WORKDIR/dyn-extra-output-retry.txt" ;;
            codex:*) status="${raw_status#codex:}"; reviewer_file="$WORKDIR/codex-specialist-security-output.txt" ;;
            phase2:*) status="${raw_status#phase2:}"; reviewer_file="$WORKDIR/cursor-specialist-security-output-phase2.txt" ;;
            phase3:*) status="${raw_status#phase3:}"; reviewer_file="$WORKDIR/cursor-specialist-security-output-phase3.txt" ;;
        esac
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

kv() { awk -F= -v k="$1" '$1==k{print $2; exit}'; }

echo "# default denominator is 4"
out=$(run_case default_4 hard OK OK timeout timeout 2>&1)
assert_eq "default INTENDED_SLOTS=4" "$(printf '%s\n' "$out" | kv INTENDED_SLOTS)" "4"
assert_eq "2/4 failures passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"

out=$(run_case fail_4 hard --intended-slots 4 OK timeout timeout timeout 2>&1)
assert_eq "3/4 failures fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"

out=$(run_case pass_8 hard --intended-slots 8 OK OK OK OK OK OK OK timeout 2>&1)
assert_eq "1/8 failures passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"
assert_eq "explicit INTENDED_SLOTS=8" "$(printf '%s\n' "$out" | kv INTENDED_SLOTS)" "8"

out=$(run_case fail_8 hard --intended-slots 8 OK OK OK timeout timeout timeout timeout timeout 2>&1)
assert_eq "5/8 failures fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"
assert_eq "5/8 FAILED_SLOTS=5" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "5"

echo "# dropped static slots count, dynamic drops excluded"
drops="$WORKDIR/drops.tsv"
printf 'security\tcursor\tformat-gate-miss\tpreamble\n' > "$drops"
printf 'dyn-api\tcodex\tformat-gate-miss\tpreamble\n' >> "$drops"
out=$(run_case one_drop_8 hard --intended-slots 8 --dropped-slots-file "$drops" OK OK OK OK OK OK OK 2>&1)
assert_eq "one static drop counted" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "1"
assert_eq "1 dropped peer of 8 passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"
assert_eq "dynamic drop excluded from FAILED_SLOTS" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

drops5="$WORKDIR/drops5.tsv"
for slot in security correctness edge-cases testing security; do
    printf '%s\tcursor\tcollector-failure\tbad\n' "$slot" >> "$drops5"
done
out=$(run_case five_drops_8 hard --intended-slots 8 --dropped-slots-file "$drops5" OK OK OK 2>&1)
assert_eq "5 dropped static peers of 8 fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"
assert_eq "DROPPED_STATIC_SLOTS=5" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "5"

echo "# launched padding applies only without drop accounting"
out=$(run_case never_launched hard --intended-slots 4 --launched-slots 0 2>&1)
assert_eq "0 launched of 4 pads failures" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "4"
assert_eq "0 launched of 4 fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"

out=$(run_case no_padding_with_drop hard --intended-slots 4 --launched-slots 0 --dropped-slots-file "$drops" 2>&1)
assert_eq "drop accounting suppresses never-launched padding" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

echo "# dynamic outputs, including Codex twins and phase/retry variants, are excluded"
out=$(run_case dynamic_names hard --intended-slots 8 --launched-slots 8 OK OK OK timeout timeout dyn:timeout dyn-codex:timeout dyn-phase2:timeout dyn-phase3:timeout dyn-retry:timeout 2>&1)
assert_eq "dynamic variants excluded from COUNTED_SLOTS" "$(printf '%s\n' "$out" | kv COUNTED_SLOTS)" "5"
assert_eq "only static failures contribute" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "2"

out=$(run_case not_substantive hard --intended-slots 4 OK OK NOT_SUBSTANTIVE timeout 2>&1)
assert_eq "NOT_SUBSTANTIVE counts as failed" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "2"
assert_eq "NOT_SUBSTANTIVE tracked separately" "$(printf '%s\n' "$out" | kv NOT_SUBSTANTIVE_SLOTS)" "1"

out=$(run_case cap_hit hard --intended-slots 4 OK OK cap_hit timeout 2>&1)
assert_eq "cap_hit counted as success" "$(printf '%s\n' "$out" | kv SUCCEEDED_SLOTS)" "3"
assert_eq "cap_hit not a failure" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-check-reviewer-failure-threshold.sh\n'
    exit 0
else
    printf 'FAIL: test-check-reviewer-failure-threshold.sh\n'
    exit 1
fi
