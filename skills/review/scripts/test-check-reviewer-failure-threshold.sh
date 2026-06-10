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
    local raw_status status reviewer_file idx=0 slot
    local slots=(correctness edge-cases testing)
    : > "$file"
    for raw_status in "$@"; do
        idx=$((idx + 1))
        slot="${slots[$(( (idx - 1) % 3 ))]}"
        status="$raw_status"
        reviewer_file="$WORKDIR/cursor-specialist-${slot}-output.txt"
        case "$raw_status" in
            same:*) status="${raw_status#same:}"; reviewer_file="$WORKDIR/cursor-specialist-correctness-output.txt" ;;
            dyn:*) status="${raw_status#dyn:}"; reviewer_file="$WORKDIR/dyn-extra-output.txt" ;;
            dyn-codex:*) status="${raw_status#dyn-codex:}"; reviewer_file="$WORKDIR/dyn-extra-codex-output.txt" ;;
            dyn-phase2:*) status="${raw_status#dyn-phase2:}"; reviewer_file="$WORKDIR/dyn-extra-output-phase2.txt" ;;
            dyn-phase3:*) status="${raw_status#dyn-phase3:}"; reviewer_file="$WORKDIR/dyn-extra-output-phase3.txt" ;;
            dyn-retry:*) status="${raw_status#dyn-retry:}"; reviewer_file="$WORKDIR/dyn-extra-output-retry.txt" ;;
            codex:*) status="${raw_status#codex:}"; reviewer_file="$WORKDIR/codex-specialist-${slot}-output.txt" ;;
            phase2:*) status="${raw_status#phase2:}"; reviewer_file="$WORKDIR/cursor-specialist-correctness-output-phase2.txt" ;;
            phase3:*) status="${raw_status#phase3:}"; reviewer_file="$WORKDIR/cursor-specialist-correctness-output-phase3.txt" ;;
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

echo "# default denominator follows the single-vendor static panel"
out=$(run_case default_3 hard OK OK timeout 2>&1)
assert_eq "default INTENDED_SLOTS=3" "$(printf '%s\n' "$out" | kv INTENDED_SLOTS)" "3"
assert_eq "1/3 failures passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"

out=$(run_case fail_3 hard --intended-slots 3 OK timeout timeout 2>&1)
assert_eq "2/3 failures fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"

out=$(run_case pass_6 hard --intended-slots 6 OK OK OK codex:OK codex:OK codex:timeout 2>&1)
assert_eq "1/6 failures passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"
assert_eq "explicit INTENDED_SLOTS=6" "$(printf '%s\n' "$out" | kv INTENDED_SLOTS)" "6"

out=$(run_case fail_6 hard --intended-slots 6 OK OK timeout codex:timeout codex:timeout codex:timeout 2>&1)
assert_eq "4/6 failures fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"
assert_eq "4/6 FAILED_SLOTS=4" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "4"

echo "# dropped static slots count, dynamic drops excluded"
drops="$WORKDIR/drops.tsv"
printf 'testing	codex	format-gate-miss	preamble
' > "$drops"
printf 'dyn-api	codex	format-gate-miss	preamble
' >> "$drops"
out=$(run_case one_drop_6 hard --intended-slots 6 --dropped-slots-file "$drops" OK OK OK codex:OK codex:OK 2>&1)
assert_eq "one static drop counted" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "1"
assert_eq "1 dropped peer of 6 passes" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "true"
assert_eq "dynamic drop excluded from FAILED_SLOTS" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

drops4="$WORKDIR/drops4.tsv"
{
    printf 'correctness	cursor	collector-failure	bad
'
    printf 'edge-cases	cursor	collector-failure	bad
'
    printf 'testing	cursor	collector-failure	bad
'
    printf 'correctness	codex	collector-failure	bad
'
} >> "$drops4"
out=$(run_case four_drops_6 hard --intended-slots 6 --dropped-slots-file "$drops4" 2>&1)
assert_eq "4 dropped static peers of 6 fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"
assert_eq "DROPPED_STATIC_SLOTS=4" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "4"

echo "# launched padding subtracts dropped slots already accounted for"
out=$(run_case never_launched hard --intended-slots 3 --launched-slots 0 2>&1)
assert_eq "0 launched of 3 pads failures" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "3"
assert_eq "0 launched of 3 fails" "$(printf '%s\n' "$out" | kv THRESHOLD_OK)" "false"

out=$(run_case no_padding_with_drop hard --intended-slots 3 --launched-slots 0 --dropped-slots-file "$drops" 2>&1)
assert_eq "drop accounting only suppresses accounted never-launched slots" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "3"

echo "# dynamic outputs, including Codex twins and phase/retry variants, are excluded"
out=$(run_case dynamic_names hard --intended-slots 6 --launched-slots 6 OK OK OK codex:timeout codex:timeout dyn:timeout dyn-codex:timeout dyn-phase2:timeout dyn-phase3:timeout dyn-retry:timeout 2>&1)
assert_eq "dynamic variants excluded from COUNTED_SLOTS" "$(printf '%s\n' "$out" | kv COUNTED_SLOTS)" "5"
assert_eq "only static failures contribute" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "2"

out=$(run_case not_substantive hard --intended-slots 3 OK NOT_SUBSTANTIVE timeout 2>&1)
assert_eq "NOT_SUBSTANTIVE counts as failed" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "2"
assert_eq "NOT_SUBSTANTIVE tracked separately" "$(printf '%s\n' "$out" | kv NOT_SUBSTANTIVE_SLOTS)" "1"

out=$(run_case duplicate_collector_rows hard --intended-slots 3 same:timeout same:timeout same:timeout 2>&1)
assert_eq "duplicate collector base counted once" "$(printf '%s\n' "$out" | kv COUNTED_SLOTS)" "1"
assert_eq "duplicate collector failures counted once" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

out=$(run_case duplicate_collector_recovery hard --intended-slots 3 same:timeout same:OK 2>&1)
assert_eq "duplicate collector recovery counted once" "$(printf '%s\n' "$out" | kv COUNTED_SLOTS)" "1"
assert_eq "duplicate collector recovery prefers success" "$(printf '%s\n' "$out" | kv SUCCEEDED_SLOTS)" "1"
assert_eq "duplicate collector recovery clears prior failure" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "0"

out=$(run_case cap_hit hard --intended-slots 3 OK cap_hit timeout 2>&1)
assert_eq "cap_hit counted as success" "$(printf '%s\n' "$out" | kv SUCCEEDED_SLOTS)" "2"
assert_eq "cap_hit not a failure" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "1"

echo "# reviewer output files count phase fallback static slots without double-counting collector rows"
phase_success="$WORKDIR/cursor-specialist-correctness-output-phase3.txt"
phase_fail="$WORKDIR/codex-specialist-testing-output-phase2.txt"
printf 'substantive fallback finding\n' > "$phase_success"
: > "$phase_fail"
printf 'substantive correctness finding\n' > "$WORKDIR/cursor-specialist-correctness-output.txt"
collector="$WORKDIR/output-files.env"
emit_records "$collector" OK
out="$WORKDIR/output-files.out"
out_content=$("$TARGET" --collector-results-file "$collector" --panel hard --intended-slots 3 \
    --reviewer-output-files "$WORKDIR/cursor-specialist-correctness-output.txt" "$phase_success" "$phase_fail" \
    2>&1)
assert_eq "phase output duplicate not double counted as extra success" "$(printf '%s\n' "$out_content" | kv SUCCEEDED_SLOTS)" "1"
assert_eq "phase output failure counted" "$(printf '%s\n' "$out_content" | kv FAILED_SLOTS)" "1"
assert_eq "collector duplicate output not double counted" "$(printf '%s\n' "$out_content" | kv COUNTED_SLOTS)" "2"

collector="$WORKDIR/output-files-recovery.env"
emit_records "$collector" timeout
recovered="$WORKDIR/cursor-specialist-correctness-output.txt"
printf 'substantive recovered static reviewer\n' > "$recovered"
out_content=$("$TARGET" --collector-results-file "$collector" --panel hard --intended-slots 3 \
    --reviewer-output-files "$recovered" \
    2>&1)
assert_eq "substantive output overrides collector failure" "$(printf '%s\n' "$out_content" | kv SUCCEEDED_SLOTS)" "1"
assert_eq "substantive output override removes failure" "$(printf '%s\n' "$out_content" | kv FAILED_SLOTS)" "0"

drops_dup="$WORKDIR/drops-dup.tsv"
printf 'correctness\tcursor\tformat-gate-miss\tpreamble\n' > "$drops_dup"
printf 'correctness\tcursor\tformat-gate-miss\tpreamble\n' >> "$drops_dup"
out=$(run_case duplicate_drops hard --intended-slots 3 --dropped-slots-file "$drops_dup" 2>&1)
assert_eq "duplicate dropped slot counted once" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "1"

drops_counted="$WORKDIR/drops-counted.tsv"
printf 'correctness\tcursor\tformat-gate-miss\tpreamble\n' > "$drops_counted"
out=$(run_case counted_drop hard --intended-slots 3 --dropped-slots-file "$drops_counted" OK 2>&1)
assert_eq "dropped slot already counted from collector is skipped" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "0"

echo "# collector success downgrades when output file is non-substantive"
empty_ok="$WORKDIR/cursor-specialist-correctness-output.txt"
: > "$empty_ok"
collector_empty_ok="$WORKDIR/collector-empty-ok.env"
emit_records "$collector_empty_ok" OK
out_content=$("$TARGET" --collector-results-file "$collector_empty_ok" --panel hard --intended-slots 3 \
    --reviewer-output-files "$empty_ok" \
    2>&1)
assert_eq "empty output downgrades collector OK" "$(printf '%s\n' "$out_content" | kv SUCCEEDED_SLOTS)" "0"
assert_eq "empty output counts as failure" "$(printf '%s\n' "$out_content" | kv FAILED_SLOTS)" "1"

echo "# unrecognized dropped tool does not inflate failures"
drops_unknown="$WORKDIR/drops-unknown.tsv"
printf 'correctness\tunknown-tool\tformat-gate-miss\tpreamble\n' > "$drops_unknown"
out=$(run_case unknown_drop hard --intended-slots 3 --dropped-slots-file "$drops_unknown" OK OK OK 2>&1)
assert_eq "unknown dropped tool ignored" "$(printf '%s\n' "$out" | kv DROPPED_STATIC_SLOTS)" "0"
assert_eq "unknown dropped tool does not add failure" "$(printf '%s\n' "$out" | kv FAILED_SLOTS)" "0"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-check-reviewer-failure-threshold.sh\n'
    exit 0
else
    printf 'FAIL: test-check-reviewer-failure-threshold.sh\n'
    exit 1
fi
