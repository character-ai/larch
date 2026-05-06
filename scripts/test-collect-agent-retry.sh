#!/usr/bin/env bash
# test-collect-agent-retry.sh - Regression coverage for CMD_JSON retry metadata.
#
# Wired into Makefile via the test-collect-agent-retry target and the
# test-harnesses aggregator; runs on every `make lint`.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-collect-agent-retry-XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
SKIP=0
FAILED=()

ok() { PASS=$((PASS + 1)); echo "  ok: $1"; }
fail() { FAIL=$((FAIL + 1)); FAILED+=("$1"); echo "  FAIL: $1" >&2; }
skipm() { SKIP=$((SKIP + 1)); echo "  SKIPPED: $1"; }

require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "missing required tool: $1"
    fi
}

assert_line() {
    local label="$1"
    local expected="$2"
    local haystack="$3"
    if printf '%s\n' "$haystack" | grep -Fxq "$expected"; then
        ok "$label"
    else
        fail "$label: missing line '$expected'"
        printf '%s\n' "$haystack" >&2
    fi
}

json_array() {
    jq -cn --args '$ARGS.positional' -- "$@"
}

write_empty_candidate() {
    local output="$1"
    mkdir -p "$(dirname "$output")"
    : > "$output"
    printf '0\n' > "${output}.done"
}

write_meta() {
    local output="$1"
    local cmd_json="$2"
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$cmd_json"
    } > "${output}.meta"
}

write_meta_body() {
    local output="$1"
    shift
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf '%s\n' "$@"
    } > "${output}.meta"
}

write_meta_without_timeout() {
    local output="$1"
    local cmd_json="$2"
    {
        printf 'TOOL=cursor\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$cmd_json"
    } > "${output}.meta"
}

write_meta_with_timeout() {
    local output="$1"
    local timeout="$2"
    local cmd_json="$3"
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=%s\n' "$timeout"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$cmd_json"
    } > "${output}.meta"
}

run_collector() {
    local shell_path="$1"
    local output="$2"
    local health="$3"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 "$shell_path" "$COLLECTOR" --timeout 5 --write-health "$health" "$output" 2>"${health}.stderr"
}

assert_fail_closed() {
    local label="$1"
    local output="$2"
    local expected_reason="$3"
    local health="$TMPROOT/${label}.health"
    local out
    out=$(run_collector bash "$output" "$health")
    assert_line "$label status" "STATUS=EMPTY_OUTPUT" "$out"
    assert_line "$label healthy" "HEALTHY=false" "$out"
    assert_line "$label reason" "FAILURE_REASON=$expected_reason" "$out"
    assert_line "$label health-file" "CURSOR_HEALTHY=false" "$(cat "$health")"
}

HELPER="$TMPROOT/retry-helper.sh"
cat > "$HELPER" <<'HELPER'
#!/usr/bin/env bash
set -euo pipefail

args=("$@")
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            out="${2:?--output requires a value}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

[[ -n "$out" ]] || exit 40

if [[ "${EXPECT_TRAILING_NEWLINE:-}" == "true" ]]; then
    found="false"
    for arg in "${args[@]}"; do
        [[ "$arg" == "line"$'\n' ]] && found="true"
    done
    [[ "$found" == "true" ]] || exit 42
fi

if [[ "${EXPECT_PROMPT_UNMUTATED:-}" == "true" ]]; then
    standalone_retry="false"
    prompt_original="false"
    prompt_retry="false"
    for arg in "${args[@]}"; do
        [[ "$arg" == "${RETRY_OUTPUT_EXPECTED:-}" ]] && standalone_retry="true"
        [[ "$arg" == "prompt mentions ${ORIGINAL_OUTPUT:-}" ]] && prompt_original="true"
        [[ "$arg" == "prompt mentions ${RETRY_OUTPUT_EXPECTED:-}" ]] && prompt_retry="true"
    done
    [[ "$standalone_retry" == "true" ]] || exit 43
    [[ "$prompt_original" == "true" ]] || exit 44
    [[ "$prompt_retry" == "false" ]] || exit 45
fi

printf 'OK\n' > "$out"
HELPER
chmod +x "$HELPER"

require_tool jq
require_tool base64

# Case A: valid CMD_JSON retries empty output and returns the retry file.
OUT_A="$TMPROOT/cursor-a.txt"
HEALTH_A="$TMPROOT/case-a.health"
write_empty_candidate "$OUT_A"
write_meta "$OUT_A" "$(json_array bash "$HELPER" --output "$OUT_A")"
RESULT_A=$(run_collector bash "$OUT_A" "$HEALTH_A")
assert_line "case A reviewer file" "REVIEWER_FILE=${OUT_A%.txt}-retry.txt" "$RESULT_A"
assert_line "case A status" "STATUS=OK" "$RESULT_A"
assert_line "case A healthy" "HEALTHY=true" "$RESULT_A"

# Case B: malformed JSON fails closed and flips tool health.
OUT_B="$TMPROOT/cursor-b.txt"
write_empty_candidate "$OUT_B"
write_meta "$OUT_B" "not-valid-json"
assert_fail_closed "case-b" "$OUT_B" "Retry metadata invalid: malformed CMD_JSON"

# Case B2: alphabetic TIMEOUT fails closed before retry queueing.
OUT_B2="$TMPROOT/cursor-b2.txt"
write_empty_candidate "$OUT_B2"
write_meta_with_timeout "$OUT_B2" "abc" "$(json_array bash "$HELPER" --output "$OUT_B2")"
assert_fail_closed "case-b2" "$OUT_B2" "Retry metadata invalid: TIMEOUT not a positive integer"

# Case B3: padded zero TIMEOUT fails closed before retry queueing.
OUT_B3="$TMPROOT/cursor-b3.txt"
write_empty_candidate "$OUT_B3"
write_meta_with_timeout "$OUT_B3" "00" "$(json_array bash "$HELPER" --output "$OUT_B3")"
assert_fail_closed "case-b3" "$OUT_B3" "Retry metadata invalid: TIMEOUT not a positive integer"

# Case B4: missing TIMEOUT fails closed before retry queueing.
OUT_B4="$TMPROOT/cursor-b4.txt"
write_empty_candidate "$OUT_B4"
write_meta_without_timeout "$OUT_B4" "$(json_array bash "$HELPER" --output "$OUT_B4")"
assert_fail_closed "case-b4" "$OUT_B4" "Retry metadata invalid: TIMEOUT missing"

# Case C: stale CMD-only metadata is not accepted (TOOL is present, only CMD_JSON missing).
OUT_C="$TMPROOT/cursor-c.txt"
write_empty_candidate "$OUT_C"
write_meta_body "$OUT_C" 'CMD=printf\ ok'
assert_fail_closed "case-c" "$OUT_C" "Retry metadata invalid: missing CMD_JSON"

# Case C2: both CMD_JSON and TOOL missing — combined message.
OUT_C2="$TMPROOT/cursor-c2.txt"
write_empty_candidate "$OUT_C2"
{
    printf 'TIMEOUT=2\n'
    printf 'CAPTURE_STDOUT=false\n'
    printf 'CAPTURE_STDOUT_ONLY=false\n'
    printf 'OUTPUT_FILE=%s\n' "$OUT_C2"
} > "${OUT_C2}.meta"
HEALTH_C2="$TMPROOT/case-c2.health"
RESULT_C2=$(run_collector bash "$OUT_C2" "$HEALTH_C2")
assert_line "case C2 status" "STATUS=EMPTY_OUTPUT" "$RESULT_C2"
assert_line "case C2 reason" "FAILURE_REASON=Retry metadata invalid: missing CMD_JSON and TOOL" "$RESULT_C2"

# Case D: JSON arrays must contain only strings.
OUT_D="$TMPROOT/cursor-d.txt"
write_empty_candidate "$OUT_D"
write_meta "$OUT_D" '[1,2,3]'
assert_fail_closed "case-d" "$OUT_D" "Retry metadata invalid: malformed CMD_JSON"

# Case E: argv elements ending in a newline survive the base64+sentinel path.
OUT_E="$TMPROOT/cursor-e.txt"
HEALTH_E="$TMPROOT/case-e.health"
write_empty_candidate "$OUT_E"
TRAILING_NEWLINE_ARG=$'line\n'
write_meta "$OUT_E" "$(json_array bash "$HELPER" --output "$OUT_E" "$TRAILING_NEWLINE_ARG")"
RESULT_E=$(EXPECT_TRAILING_NEWLINE=true run_collector bash "$OUT_E" "$HEALTH_E")
assert_line "case E status" "STATUS=OK" "$RESULT_E"

# Case F: only standalone output argv elements are swapped, not prompt substrings.
OUT_F="$TMPROOT/cursor-f.txt"
HEALTH_F="$TMPROOT/case-f.health"
RETRY_F="${OUT_F%.txt}-retry.txt"
write_empty_candidate "$OUT_F"
write_meta "$OUT_F" "$(json_array bash "$HELPER" --output "$OUT_F" "prompt mentions $OUT_F")"
RESULT_F=$(EXPECT_PROMPT_UNMUTATED=true ORIGINAL_OUTPUT="$OUT_F" RETRY_OUTPUT_EXPECTED="$RETRY_F" run_collector bash "$OUT_F" "$HEALTH_F")
assert_line "case F status" "STATUS=OK" "$RESULT_F"

# Case G: when the system /bin/bash is vulnerable (<4.4), exercise the retry
# path under that runtime as the macOS bash-3.2 portability guard.
SYSTEM_BASH="/bin/bash"
BASH_MAJOR=""
BASH_MINOR=""
if [[ -x "$SYSTEM_BASH" ]]; then
    # shellcheck disable=SC2016 # ${BASH_VERSINFO[*]} must be expanded by $SYSTEM_BASH, not the parent shell.
    BASH_MAJOR="$("$SYSTEM_BASH" -c 'echo "${BASH_VERSINFO[0]}"' 2>/dev/null || echo "")"
    # shellcheck disable=SC2016 # ${BASH_VERSINFO[*]} must be expanded by $SYSTEM_BASH, not the parent shell.
    BASH_MINOR="$("$SYSTEM_BASH" -c 'echo "${BASH_VERSINFO[1]}"' 2>/dev/null || echo "")"
fi

DYNAMIC_VULNERABLE="false"
if [[ "$BASH_MAJOR" == "3" ]]; then
    DYNAMIC_VULNERABLE="true"
elif [[ "$BASH_MAJOR" == "4" ]] && [[ -n "$BASH_MINOR" ]] && (( BASH_MINOR < 4 )); then
    DYNAMIC_VULNERABLE="true"
fi

if [[ "$DYNAMIC_VULNERABLE" == "true" ]]; then
    OUT_G="$TMPROOT/cursor-g.txt"
    HEALTH_G="$TMPROOT/case-g.health"
    write_empty_candidate "$OUT_G"
    write_meta "$OUT_G" "$(json_array bash "$HELPER" --output "$OUT_G")"
    RESULT_G=$(run_collector "$SYSTEM_BASH" "$OUT_G" "$HEALTH_G")
    assert_line "case G status under $SYSTEM_BASH" "STATUS=OK" "$RESULT_G"
else
    skipm "case G: bash ${BASH_MAJOR:-unknown}.${BASH_MINOR:-?} at $SYSTEM_BASH (need < 4.4 for dynamic retry portability check)"
fi

# Case H: mixed-batch — one candidate has malformed CMD_JSON (no retry launched),
# another candidate has valid CMD_JSON (retry launched and succeeds). The
# malformed entry's specific FAILURE_REASON must survive the post-wait
# result-update loop; without the RETRY_LAUNCHED guard, the second loop would
# overwrite it with "Retry process did not complete (sentinel file missing)".
OUT_H_BAD="$TMPROOT/cursor-h-bad.txt"
OUT_H_OK="$TMPROOT/cursor-h-ok.txt"
HEALTH_H="$TMPROOT/case-h.health"
write_empty_candidate "$OUT_H_BAD"
write_meta "$OUT_H_BAD" "not-valid-json"
write_empty_candidate "$OUT_H_OK"
write_meta "$OUT_H_OK" "$(json_array bash "$HELPER" --output "$OUT_H_OK")"
RESULT_H=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --write-health "$HEALTH_H" "$OUT_H_BAD" "$OUT_H_OK" 2>"${HEALTH_H}.stderr")
# Bad entry retains its specific reason despite the valid sibling launching a retry.
assert_line "case H bad reviewer file" "REVIEWER_FILE=$OUT_H_BAD" "$RESULT_H"
assert_line "case H bad reason" "FAILURE_REASON=Retry metadata invalid: malformed CMD_JSON" "$RESULT_H"
# Good entry recovers via retry.
assert_line "case H ok reviewer file" "REVIEWER_FILE=${OUT_H_OK%.txt}-retry.txt" "$RESULT_H"
assert_line "case H ok status" "STATUS=OK" "$RESULT_H"

echo ""
echo "Summary: $PASS passed, $FAIL failed, $SKIP skipped"
if (( FAIL > 0 )); then
    echo "Failed cases:" >&2
    for t in "${FAILED[@]+"${FAILED[@]}"}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
exit 0
