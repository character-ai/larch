#!/usr/bin/env bash
# test-collect-agent-retry.sh - Regression coverage for CMD_JSON retry metadata.
#
# Wired into Makefile via the test-collect-agent-retry target and the
# test-harnesses aggregator; runs on every `make lint`.

set -uo pipefail

# Drop wait-for-reviewers.sh's sentinel-poll cadence to 0.05s. Each successful
# retry case otherwise pays one full 5s default poll waiting for the retry
# sentinel to appear. Production callers inherit the 5s default; only this
# stub-driven harness needs the fast cadence. Companion knob to the existing
# RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 set inline at run_collector below.
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-collect-agent-retry-XXXXXX")"
# Suppress rm stderr: backgrounded retry subshells (collect-agent-results.sh)
# can still hold a per-case workdir as cwd when this trap fires, producing a
# transient "Permission denied" on macOS APFS. Cleanup is best-effort; the OS
# reaps stale dirs under TMPDIR.
trap 'rm -rf "$TMPROOT" 2>/dev/null' EXIT

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

assert_equals() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

assert_no_line_prefix() {
    local label="$1"
    local prefix="$2"
    local haystack="$3"
    if printf '%s\n' "$haystack" | grep -q "^$prefix"; then
        fail "$label: unexpected line prefix '$prefix'"
        printf '%s\n' "$haystack" >&2
    else
        ok "$label"
    fi
}

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'CURSOR_SHAPE_STUB'
#!/usr/bin/env bash
set -euo pipefail
helper=""
args=("$@")
while [[ $# -gt 0 ]]; do
    case "$1" in
        --helper)
            helper="${2:?--helper requires a value}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
if [[ -n "$helper" ]]; then
    exec bash "$helper" "${args[@]}"
fi
exit 40
CURSOR_SHAPE_STUB
chmod +x "$STUB_BIN/cursor"
cat > "$STUB_BIN/codex" <<'CODEX_SHAPE_STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        out="$arg"
    fi
    last="$arg"
done
[[ -n "$out" ]] || exit 40
printf 'OK\n' > "$out"
CODEX_SHAPE_STUB
chmod +x "$STUB_BIN/codex"
PATH="$STUB_BIN:$PATH"
export PATH

json_array() {
    if [[ "${1:-}" == "bash" && -n "${2:-}" ]]; then
        local helper="$2"
        shift 2
        jq -cn --args '$ARGS.positional' -- cursor agent --workspace "$TMPROOT" --helper "$helper" "$@"
    else
        jq -cn --args '$ARGS.positional' -- "$@"
    fi
}

write_empty_candidate() {
    local output="$1"
    mkdir -p "$(dirname "$output")"
    : > "$output"
    printf '0\n' > "${output}.done"
}

write_nonempty_candidate() {
    local output="$1"
    mkdir -p "$(dirname "$output")"
    printf 'substantive collector retry regression content with enough words to be visibly non-empty for the sentinel validation cases\n' > "$output"
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

write_meta_for_tool() {
    local output="$1"
    local tool="$2"
    local cmd_json="$3"
    {
        printf 'TOOL=%s\n' "$tool"
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$cmd_json"
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
    local stderr="${3:-$TMPROOT/collector.stderr}"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 "$shell_path" "$COLLECTOR" --timeout 5 "$output" 2>"$stderr"
}

run_collector_structured() {
    local shell_path="$1"
    local output="$2"
    local stderr="${3:-$TMPROOT/collector-structured.stderr}"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 "$shell_path" "$COLLECTOR" --timeout 5 --structured-reviewer-validation "$output" 2>"$stderr"
}

run_collector_summary_structured() {
    local shell_path="$1"
    local output="$2"
    local stderr="${3:-$TMPROOT/collector-summary.stderr}"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 "$shell_path" "$COLLECTOR" --timeout 5 --structured-reviewer-validation --summary-only "$output" 2>"$stderr"
}

assert_fail_closed() {
    local label="$1"
    local output="$2"
    local expected_reason="$3"
    local out
    out=$(run_collector bash "$output" "$TMPROOT/${label}.stderr")
    assert_line "$label status" "STATUS=EMPTY_OUTPUT" "$out"
    assert_line "$label reason" "FAILURE_REASON=$expected_reason" "$out"
    assert_line "$label exit-code" "EXIT_CODE=99" "$out"
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
STDERR_A="$TMPROOT/case-a.stderr"
write_empty_candidate "$OUT_A"
write_meta "$OUT_A" "$(json_array bash "$HELPER" --output "$OUT_A")"
RESULT_A=$(run_collector bash "$OUT_A" "$STDERR_A")
assert_line "case A reviewer file" "REVIEWER_FILE=${OUT_A%.txt}-retry.txt" "$RESULT_A"
assert_line "case A status" "STATUS=OK" "$RESULT_A"

# Case A2: structured reviewer validation writes a normalized TSV sidecar and
# emits the STRUCTURED_SIDECAR field before FAILURE_REASON.
OUT_A2="$TMPROOT/cursor-a2.txt"
STDERR_A2="$TMPROOT/case-a2.stderr"
{
    printf 'schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n'
    printf '1\tin_scope\tImportant\tcorrectness\tfoo.sh:7\tbad branch\tinput fails\tadd guard\n'
} > "$OUT_A2"
printf '0\n' > "${OUT_A2}.done"
RESULT_A2=$(run_collector_structured bash "$OUT_A2" "$STDERR_A2")
assert_line "case A2 status" "STATUS=OK" "$RESULT_A2"
assert_line "case A2 structured sidecar field" "STRUCTURED_SIDECAR=${OUT_A2}.tsv" "$RESULT_A2"
assert_line "case A2 sidecar normalized" $'1\tin_scope\timportant\tcorrectness\tfoo.sh:7\tbad branch\tinput fails\tadd guard' "$(cat "${OUT_A2}.tsv")"

# Case A3: structured reviewer validation fails closed when STATUS=OK output
# has no valid records.
OUT_A3="$TMPROOT/cursor-a3.txt"
STDERR_A3="$TMPROOT/case-a3.stderr"
printf 'ordinary prose only\n' > "$OUT_A3"
printf '0\n' > "${OUT_A3}.done"
RESULT_A3=$(run_collector_structured bash "$OUT_A3" "$STDERR_A3")
assert_line "case A3 status" "STATUS=NOT_SUBSTANTIVE" "$RESULT_A3"
assert_line "case A3 structured sidecar empty field" "STRUCTURED_SIDECAR=" "$RESULT_A3"
assert_line "case A3 reason" "FAILURE_REASON=structured records not found after repair" "$RESULT_A3"

# Case A4: --summary-only preserves core status fields while suppressing
# diagnostic-heavy fields, even when structured validation would normally emit
# STRUCTURED_SIDECAR and FAILURE_REASON.
OUT_A4="$TMPROOT/cursor-a4.txt"
STDERR_A4="$TMPROOT/case-a4.stderr"
{
    printf 'schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n'
    printf '1\tin_scope\tImportant\tcorrectness\tfoo.sh:7\tbad branch\tinput fails\tadd guard\n'
} > "$OUT_A4"
printf '0\n' > "${OUT_A4}.done"
RESULT_A4=$(run_collector_summary_structured bash "$OUT_A4" "$STDERR_A4")
assert_line "case A4 reviewer file" "REVIEWER_FILE=$OUT_A4" "$RESULT_A4"
assert_line "case A4 status" "STATUS=OK" "$RESULT_A4"
assert_no_line_prefix "case A4 suppresses structured sidecar" "STRUCTURED_SIDECAR=" "$RESULT_A4"
assert_no_line_prefix "case A4 suppresses failure reason" "FAILURE_REASON=" "$RESULT_A4"

# Case B: malformed JSON fails closed for the reviewer result.
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
STDERR_C2="$TMPROOT/case-c2.stderr"
RESULT_C2=$(run_collector bash "$OUT_C2" "$STDERR_C2")
assert_line "case C2 status" "STATUS=EMPTY_OUTPUT" "$RESULT_C2"
assert_line "case C2 reason" "FAILURE_REASON=Retry metadata invalid: missing CMD_JSON and TOOL" "$RESULT_C2"
assert_line "case C2 exit-code" "EXIT_CODE=99" "$RESULT_C2"

# Case D: JSON arrays must contain only strings.
OUT_D="$TMPROOT/cursor-d.txt"
write_empty_candidate "$OUT_D"
write_meta "$OUT_D" '[1,2,3]'
assert_fail_closed "case-d" "$OUT_D" "Retry metadata invalid: malformed CMD_JSON"

# Case E: argv elements ending in a newline survive the base64+sentinel path.
OUT_E="$TMPROOT/cursor-e.txt"
STDERR_E="$TMPROOT/case-e.stderr"
write_empty_candidate "$OUT_E"
TRAILING_NEWLINE_ARG=$'line\n'
write_meta "$OUT_E" "$(json_array bash "$HELPER" --output "$OUT_E" "$TRAILING_NEWLINE_ARG")"
RESULT_E=$(EXPECT_TRAILING_NEWLINE=true run_collector bash "$OUT_E" "$STDERR_E")
assert_line "case E status" "STATUS=OK" "$RESULT_E"

# Case F: only standalone output argv elements are swapped, not prompt substrings.
OUT_F="$TMPROOT/cursor-f.txt"
STDERR_F="$TMPROOT/case-f.stderr"
RETRY_F="${OUT_F%.txt}-retry.txt"
write_empty_candidate "$OUT_F"
write_meta "$OUT_F" "$(json_array bash "$HELPER" --output "$OUT_F" "prompt mentions $OUT_F")"
RESULT_F=$(EXPECT_PROMPT_UNMUTATED=true ORIGINAL_OUTPUT="$OUT_F" RETRY_OUTPUT_EXPECTED="$RETRY_F" run_collector bash "$OUT_F" "$STDERR_F")
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
    STDERR_G="$TMPROOT/case-g.stderr"
    write_empty_candidate "$OUT_G"
    write_meta "$OUT_G" "$(json_array bash "$HELPER" --output "$OUT_G")"
    RESULT_G=$(run_collector "$SYSTEM_BASH" "$OUT_G" "$STDERR_G")
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
STDERR_H="$TMPROOT/case-h.stderr"
write_empty_candidate "$OUT_H_BAD"
write_meta "$OUT_H_BAD" "not-valid-json"
write_empty_candidate "$OUT_H_OK"
write_meta "$OUT_H_OK" "$(json_array bash "$HELPER" --output "$OUT_H_OK")"
RESULT_H=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$OUT_H_BAD" "$OUT_H_OK" 2>"${STDERR_H}.stderr")
# Bad entry retains its specific reason despite the valid sibling launching a retry.
assert_line "case H bad reviewer file" "REVIEWER_FILE=$OUT_H_BAD" "$RESULT_H"
assert_line "case H bad reason" "FAILURE_REASON=Retry metadata invalid: malformed CMD_JSON" "$RESULT_H"
assert_line "case H bad exit-code" "EXIT_CODE=99" "$RESULT_H"
# Good entry recovers via retry.
assert_line "case H ok reviewer file" "REVIEWER_FILE=${OUT_H_OK%.txt}-retry.txt" "$RESULT_H"
assert_line "case H ok status" "STATUS=OK" "$RESULT_H"

# Case I: retry exits non-zero → EXIT_CODE in result mirrors the sentinel
# value (regression guard for #1290). Uses a helper that writes nothing to the
# retry output file and exits with a recognizable non-zero code; the wrapper
# captures that exit code into the .done sentinel via its EXIT trap, and the
# collector now propagates it as EXIT_CODE=<RETRY_EXIT> instead of masking as 0.
NONZERO_HELPER="$TMPROOT/retry-helper-nonzero.sh"
cat > "$NONZERO_HELPER" <<'NZ_HELPER'
#!/usr/bin/env bash
exit 7
NZ_HELPER
chmod +x "$NONZERO_HELPER"

OUT_I="$TMPROOT/cursor-i.txt"
STDERR_I="$TMPROOT/case-i.stderr"
write_empty_candidate "$OUT_I"
write_meta "$OUT_I" "$(json_array bash "$NONZERO_HELPER" --output "$OUT_I")"
RESULT_I=$(run_collector bash "$OUT_I" "$STDERR_I")
assert_line "case I status" "STATUS=EMPTY_OUTPUT" "$RESULT_I"
assert_line "case I exit-code propagated" "EXIT_CODE=7" "$RESULT_I"
# Pin the wrapper's exit-7 narrative end-to-end so a regression in
# build_failure_reason or its caller would surface here too, not only via
# the bare EXIT_CODE check above.
if printf '%s\n' "$RESULT_I" | grep -qE '^FAILURE_REASON=Retry also failed: Failed with exit code 7'; then
    ok "case I failure-reason narrates exit 7"
else
    fail "case I missing 'Retry also failed: Failed with exit code 7' FAILURE_REASON"
    printf '%s\n' "$RESULT_I" >&2
fi

# Case J: retry exit is 0 but retry output stays empty → STATUS=EMPTY_OUTPUT
# with EXIT_CODE=0 (confirms scripts/collect-agent-results.md sub-case: an
# EXIT_CODE=0 row with STATUS=EMPTY_OUTPUT can occur and is NOT a success).
EMPTY_HELPER="$TMPROOT/retry-helper-empty.sh"
cat > "$EMPTY_HELPER" <<'EMPTY_HELPER_EOF'
#!/usr/bin/env bash
# Touch the output file so it exists but is empty; exit 0.
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$out" ]] || exit 40
: > "$out"
exit 0
EMPTY_HELPER_EOF
chmod +x "$EMPTY_HELPER"

OUT_J="$TMPROOT/cursor-j.txt"
STDERR_J="$TMPROOT/case-j.stderr"
write_empty_candidate "$OUT_J"
write_meta "$OUT_J" "$(json_array bash "$EMPTY_HELPER" --output "$OUT_J")"
RESULT_J=$(run_collector bash "$OUT_J" "$STDERR_J")
assert_line "case J status" "STATUS=EMPTY_OUTPUT" "$RESULT_J"
assert_line "case J exit-code zero" "EXIT_CODE=0" "$RESULT_J"

# Case K: missing retry sentinel branch via direct helper invocation. Launching a
# real retry that never publishes its sentinel would pay the production retry-wait
# floor, so this pins the row builder directly through the collector's source-only
# path.
RESULT_K=$(
    bash -c '
        source "$1" --source-only
        build_missing_retry_sentinel_result "/tmp/cursor-k.txt" "cursor"
    ' _ "$COLLECTOR" 2>/dev/null
)
assert_line "case K reviewer file" "REVIEWER_FILE=/tmp/cursor-k.txt|TOOL=cursor|STATUS=EMPTY_OUTPUT|EXIT_CODE=99|STRUCTURED_SIDECAR=|FAILURE_REASON=Retry process did not complete (sentinel file missing)" "$RESULT_K"

# Case L: malformed initial sentinel content containing the pipe field delimiter
# is coerced before result construction, so no injected field appears in stdout.
OUT_L="$TMPROOT/cursor-l.txt"
STDERR_L="$TMPROOT/case-l.stderr"
write_nonempty_candidate "$OUT_L"
printf '0|EXTRA\n' > "${OUT_L}.done"
RESULT_L=$(run_collector bash "$OUT_L" "$STDERR_L")
assert_line "case L exit-code coerced" "EXIT_CODE=99" "$RESULT_L"
LINE_COUNT_L=$(printf '%s\n' "$RESULT_L" | wc -l | tr -d '[:space:]')
if [[ "$LINE_COUNT_L" == "6" ]]; then
    ok "case L field-count"
else
    fail "case L field injection: $LINE_COUNT_L lines"
fi
if printf '%s\n' "$RESULT_L" | grep -Fxq "EXTRA"; then
    fail "case L injected field surfaced"
else
    ok "case L no injected field"
fi

# Case M: oversized digit-only sentinel content is rejected before Bash arithmetic
# can overflow and misclassify it as <=255.
OUT_M="$TMPROOT/cursor-m.txt"
STDERR_M="$TMPROOT/case-m.stderr"
write_nonempty_candidate "$OUT_M"
printf '18446744073709551616\n' > "${OUT_M}.done"
RESULT_M=$(run_collector bash "$OUT_M" "$STDERR_M")
assert_line "case M exit-code overflow-guarded" "EXIT_CODE=99" "$RESULT_M"

# Case N: empty initial sentinel file is readable but invalid, so it is coerced.
OUT_N="$TMPROOT/cursor-n.txt"
STDERR_N="$TMPROOT/case-n.stderr"
write_nonempty_candidate "$OUT_N"
: > "${OUT_N}.done"
RESULT_N=$(run_collector bash "$OUT_N" "$STDERR_N")
assert_line "case N exit-code empty-sentinel" "EXIT_CODE=99" "$RESULT_N"

# Case O: 256 is numeric but outside Unix exit-code range.
OUT_O="$TMPROOT/cursor-o.txt"
STDERR_O="$TMPROOT/case-o.stderr"
write_nonempty_candidate "$OUT_O"
printf '256\n' > "${OUT_O}.done"
RESULT_O=$(run_collector bash "$OUT_O" "$STDERR_O")
assert_line "case O exit-code over-255" "EXIT_CODE=99" "$RESULT_O"

# Case P: coerced-99 with empty output + valid .meta must route to retry, NOT to
# STATUS=FAILED. Without the FINDING_1 fix, a malformed .done would deny the
# one-shot empty-output recovery the retry path was designed for. With the fix,
# coerced-99 + empty output is treated as a retry-eligible empty-output case,
# so the helper runs and the retry succeeds.
OUT_P="$TMPROOT/cursor-p.txt"
STDERR_P="$TMPROOT/case-p.stderr"
write_empty_candidate "$OUT_P"
write_meta "$OUT_P" "$(json_array bash "$HELPER" --output "$OUT_P")"
printf '0|EXTRA\n' > "${OUT_P}.done"  # malformed → coerced to 99
RESULT_P=$(run_collector bash "$OUT_P" "$STDERR_P")
assert_line "case P retry succeeded" "REVIEWER_FILE=${OUT_P%.txt}-retry.txt" "$RESULT_P"
assert_line "case P status" "STATUS=OK" "$RESULT_P"

# Case P2: per-tool CMD_JSON shape allowlists fail closed on known-dangerous
# cursor extensions.
OUT_P2="$TMPROOT/cursor-p2.txt"
write_empty_candidate "$OUT_P2"
write_meta "$OUT_P2" "$(jq -cn --args '$ARGS.positional' -- cursor agent --workspace "$TMPROOT" --add-dir /etc --helper "$HELPER" --output "$OUT_P2")"
assert_fail_closed "case-p2" "$OUT_P2" "Retry metadata invalid: CMD_JSON argv shape rejected for cursor"

# Case P3: codex's registered shape is accepted by the legacy CMD_JSON path.
OUT_P3="$TMPROOT/codex-p3.txt"
STDERR_P3="$TMPROOT/case-p3.stderr"
write_empty_candidate "$OUT_P3"
write_meta_for_tool "$OUT_P3" codex "$(jq -cn --args '$ARGS.positional' -- codex exec --full-auto -C "$TMPROOT" --add-dir "$TMPROOT" --output-last-message "$OUT_P3")"
RESULT_P3=$(run_collector bash "$OUT_P3" "$STDERR_P3")
assert_line "case P3 codex shape accepted" "STATUS=OK" "$RESULT_P3"
assert_line "case P3 codex retry file" "REVIEWER_FILE=${OUT_P3%.txt}-retry.txt" "$RESULT_P3"

# Case P4: unknown TOOL values fail closed instead of falling back to a less
# constrained CMD_JSON path.
OUT_P4="$TMPROOT/cursor-p4.txt"
write_empty_candidate "$OUT_P4"
write_meta_for_tool "$OUT_P4" unknown-tool "$(jq -cn --args '$ARGS.positional' -- cursor agent --workspace "$TMPROOT" --helper "$HELPER" --output "$OUT_P4")"
assert_fail_closed "case-p4" "$OUT_P4" "Retry metadata invalid: unknown TOOL for CMD_JSON"

# Outer-launcher retry coverage. The retry metadata points at the real
# launch-review.sh, while PATH supplies a stub cursor binary so the
# launcher runs offline.
CURSOR_STUB_BIN="$TMPROOT/cursor-stub-bin"
mkdir -p "$CURSOR_STUB_BIN"
cat > "$CURSOR_STUB_BIN/cursor" <<'CURSOR_STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${CURSOR_STUB_PWD_LOG:-}" ]]; then
    pwd -P > "$CURSOR_STUB_PWD_LOG"
fi
printf '{"result":"%s","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n' "${CURSOR_STUB_RESULT:-POST-PROCESSED OK}"
CURSOR_STUB
chmod +x "$CURSOR_STUB_BIN/cursor"
export LARCH_CURSOR_MODEL=test-cursor-model

write_outer_meta() {
    local output="$1"
    local launcher="$2"
    local prompt_file="$3"
    local workdir="$4"
    shift 4
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'OUTER_LAUNCHER=%s\n' "$launcher"
        printf 'OUTER_LAUNCHER_PROMPT_FILE=%s\n' "$prompt_file"
        printf 'OUTER_LAUNCHER_WORKDIR=%s\n' "$workdir"
        printf '%s\n' "$@"
    } > "${output}.meta"
}

prepare_outer_candidate() {
    local output="$1"
    write_empty_candidate "$output"
    printf 'outer prompt\n' > "${output}.prompt"
}

OUT_Q="$TMPROOT/cursor-q.txt"
STDERR_Q="$TMPROOT/case-q.stderr"
WORKDIR_Q="$TMPROOT/workdir-q"
mkdir -p "$WORKDIR_Q"
prepare_outer_candidate "$OUT_Q"
write_outer_meta "$OUT_Q" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_Q}.prompt" "$WORKDIR_Q"
export CURSOR_STUB_RESULT="POST-PROCESSED OK"
RESULT_Q=$(PATH="$CURSOR_STUB_BIN:$PATH" run_collector bash "$OUT_Q" "$STDERR_Q")
assert_line "case Q reviewer file" "REVIEWER_FILE=${OUT_Q%.txt}-retry.txt" "$RESULT_Q"
assert_line "case Q status" "STATUS=OK" "$RESULT_Q"
assert_equals "case Q retry post-processed" "POST-PROCESSED OK" "$(cat "${OUT_Q%.txt}-retry.txt")"

OUT_Q2="$TMPROOT/codex-q2.txt"
STDERR_Q2="$TMPROOT/case-q2.stderr"
WORKDIR_Q2="$TMPROOT/workdir-q2"
mkdir -p "$WORKDIR_Q2"
prepare_outer_candidate "$OUT_Q2"
{
    printf 'TOOL=codex\n'
    printf 'TIMEOUT=2\n'
    printf 'CAPTURE_STDOUT=false\n'
    printf 'CAPTURE_STDOUT_ONLY=false\n'
    printf 'OUTPUT_FILE=%s\n' "$OUT_Q2"
    printf 'OUTER_LAUNCHER=%s\n' "$REPO_ROOT/scripts/launch-review.sh"
    printf 'OUTER_LAUNCHER_PROMPT_FILE=%s\n' "${OUT_Q2}.prompt"
    printf 'OUTER_LAUNCHER_WORKDIR=%s\n' "$WORKDIR_Q2"
} > "${OUT_Q2}.meta"
RESULT_Q2=$(LARCH_CODEX_MODEL=test-codex-model run_collector bash "$OUT_Q2" "$STDERR_Q2")
assert_line "case Q2 codex outer reviewer file" "REVIEWER_FILE=${OUT_Q2%.txt}-retry.txt" "$RESULT_Q2"
assert_line "case Q2 codex outer status" "STATUS=OK" "$RESULT_Q2"
assert_equals "case Q2 codex outer output" "OK" "$(cat "${OUT_Q2%.txt}-retry.txt")"

OUT_R1="$TMPROOT/cursor-r1.txt"
prepare_outer_candidate "$OUT_R1"
write_outer_meta "$OUT_R1" "$REPO_ROOT/scripts/launch-review.sh" "" "$WORKDIR_Q"
assert_fail_closed "case-r1" "$OUT_R1" "Retry metadata invalid: missing OUTER_LAUNCHER_PROMPT_FILE"

OUT_R2="$TMPROOT/cursor-r2.txt"
prepare_outer_candidate "$OUT_R2"
write_outer_meta "$OUT_R2" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_R2}.prompt" ""
assert_fail_closed "case-r2" "$OUT_R2" "Retry metadata invalid: missing OUTER_LAUNCHER_WORKDIR"

OUT_S1="$TMPROOT/cursor-s1.txt"
prepare_outer_candidate "$OUT_S1"
write_outer_meta "$OUT_S1" "$REPO_ROOT/scripts/../scripts/launch-review.sh" "${OUT_S1}.prompt" "$WORKDIR_Q"
assert_fail_closed "case-s1" "$OUT_S1" "Retry metadata invalid: OUTER_LAUNCHER contains .."
if [[ -e "${OUT_S1%.txt}-retry.txt" ]]; then
    fail "case S1 should reject before creating retry output"
else
    ok "case S1 no retry output"
fi

OUT_S2="$TMPROOT/cursor-s2.txt"
prepare_outer_candidate "$OUT_S2"
WRONG_LAUNCHER="$TMPROOT/not-launch-review.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$WRONG_LAUNCHER"
chmod +x "$WRONG_LAUNCHER"
write_outer_meta "$OUT_S2" "$WRONG_LAUNCHER" "${OUT_S2}.prompt" "$WORKDIR_Q"
assert_fail_closed "case-s2" "$OUT_S2" "Retry metadata invalid: OUTER_LAUNCHER not canonical launch-review.sh"

OUT_U1="$TMPROOT/cursor-u1.txt"
prepare_outer_candidate "$OUT_U1"
EVIL_PROMPT="$TMPROOT/evil-prompt.txt"
printf 'evil\n' > "$EVIL_PROMPT"
write_outer_meta "$OUT_U1" "$REPO_ROOT/scripts/launch-review.sh" "$EVIL_PROMPT" "$WORKDIR_Q"
assert_fail_closed "case-u1" "$OUT_U1" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar"

OUT_U2="$TMPROOT/cursor-u2.txt"
write_empty_candidate "$OUT_U2"
REAL_PROMPT_U2="$TMPROOT/real-u2.prompt"
printf 'prompt\n' > "$REAL_PROMPT_U2"
ln -s "$REAL_PROMPT_U2" "${OUT_U2}.prompt"
write_outer_meta "$OUT_U2" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_U2}.prompt" "$WORKDIR_Q"
assert_fail_closed "case-u2" "$OUT_U2" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not a readable regular non-symlink file"

OUT_V="$TMPROOT/cursor-v.txt"
STDERR_V="$TMPROOT/case-v.stderr"
prepare_outer_candidate "$OUT_V"
write_outer_meta "$OUT_V" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_V}.prompt" "$WORKDIR_Q" 'CMD_JSON=not-json'
export CURSOR_STUB_RESULT="BROKEN CMDJSON IGNORED"
RESULT_V=$(PATH="$CURSOR_STUB_BIN:$PATH" run_collector bash "$OUT_V" "$STDERR_V")
assert_line "case V status" "STATUS=OK" "$RESULT_V"
assert_equals "case V output" "BROKEN CMDJSON IGNORED" "$(cat "${OUT_V%.txt}-retry.txt")"

OUT_W="$TMPROOT/cursor-w.txt"
STDERR_W="$TMPROOT/case-w.stderr"
PWD_LOG_W="$TMPROOT/case-w-pwd.log"
WORKDIR_W="$TMPROOT/workdir-w"
mkdir -p "$WORKDIR_W"
prepare_outer_candidate "$OUT_W"
write_outer_meta "$OUT_W" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_W}.prompt" "$WORKDIR_W"
export CURSOR_STUB_RESULT="POST-PROCESSED OK"
export CURSOR_STUB_PWD_LOG="$PWD_LOG_W"
RESULT_W=$(PATH="$CURSOR_STUB_BIN:$PATH" run_collector bash "$OUT_W" "$STDERR_W")
assert_line "case W status" "STATUS=OK" "$RESULT_W"
assert_equals "case W retry workdir" "$(cd "$WORKDIR_W" && pwd -P)" "$(cat "$PWD_LOG_W")"
unset CURSOR_STUB_PWD_LOG

OUT_X="$TMPROOT/cursor-x.txt"
prepare_outer_candidate "$OUT_X"
write_outer_meta "$OUT_X" "$REPO_ROOT/scripts/../scripts/launch-review.sh" "${OUT_X}.prompt" "$WORKDIR_Q" 'CMD_JSON=not-json'
assert_fail_closed "case-x" "$OUT_X" "Retry metadata invalid: OUTER_LAUNCHER contains .."
if [[ -e "${OUT_X%.txt}-retry.txt" ]]; then
    fail "case X should reject before creating retry output"
else
    ok "case X no retry output"
fi

# R2_FINDING_2 (-L rejection on OUTER_LAUNCHER) defense-in-depth note: a
# leaf-symlink test would require planting a symlink at the canonical
# $SCRIPT_DIR/launch-review.sh — the only path where the
# canonicalization comparison succeeds before the new -L check runs. We
# cannot pollute the live scripts/ directory from an offline harness; the
# -L code path is exercised implicitly for any non-canonical leaf-symlink
# (those are already rejected one step earlier by the canonicalization
# comparison). The code change is preserved for repos / layouts where a
# canonical-path symlink could otherwise slip past.

# Case Z (R2_FINDING_1 of /review): retry subshell must clear test-hook env
# vars before exec so a same-user attacker who sets LARCH_ALLOW_TEST_HOOKS=1
# in the collector's environment cannot smuggle arbitrary shell into the
# silent retry. We simulate by exporting both vars to a hook file that, if
# sourced, would create a sentinel file. Then run the retry; the absence of
# the sentinel proves the env was sanitized.
OUT_Z="$TMPROOT/cursor-z.txt"
STDERR_Z="$TMPROOT/case-z.stderr"
WORKDIR_Z="$TMPROOT/workdir-z"
HOOK_Z="$TMPROOT/case-z-hook.sh"
HOOK_SENTINEL_Z="$TMPROOT/case-z-hook-fired"
mkdir -p "$WORKDIR_Z"
prepare_outer_candidate "$OUT_Z"
write_outer_meta "$OUT_Z" "$REPO_ROOT/scripts/launch-review.sh" "${OUT_Z}.prompt" "$WORKDIR_Z"
printf 'touch %q\n' "$HOOK_SENTINEL_Z" > "$HOOK_Z"
export CURSOR_STUB_RESULT="POST-PROCESSED OK"
# Export the test-hook env vars in the parent shell so the collector
# subprocess inherits them naturally (an env-prefix on the same line as
# the command substitution would not propagate INTO the subshell). The
# collector's own `env -u` in the retry path must then strip them before
# launching the inner stub.
export LARCH_ALLOW_TEST_HOOKS=1
export LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$HOOK_Z"
RESULT_Z=$(PATH="$CURSOR_STUB_BIN:$PATH" run_collector bash "$OUT_Z" "$STDERR_Z")
unset LARCH_ALLOW_TEST_HOOKS LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE
assert_line "case Z status (retry succeeded)" "STATUS=OK" "$RESULT_Z"
if [[ -e "$HOOK_SENTINEL_Z" ]]; then
    fail "case Z hook sentinel exists — env-leak smuggled into retry"
else
    ok "case Z env sanitized — hook sentinel did not fire"
fi

# Case corrupt-risk: OUTER_LAUNCHER_RISK=medium (invalid value) in the .meta file
# must be normalized to 'high' and the outer launcher must still be retried
# successfully (fail-closed: unknown risk → high effort).
OUT_CORRUPT_RISK="$TMPROOT/cursor-corrupt-risk.txt"
STDERR_CORRUPT_RISK="$TMPROOT/case-corrupt-risk.stderr"
WORKDIR_CORRUPT_RISK="$TMPROOT/workdir-corrupt-risk"
mkdir -p "$WORKDIR_CORRUPT_RISK"
prepare_outer_candidate "$OUT_CORRUPT_RISK"
write_outer_meta "$OUT_CORRUPT_RISK" "$REPO_ROOT/scripts/launch-review.sh" \
    "${OUT_CORRUPT_RISK}.prompt" "$WORKDIR_CORRUPT_RISK" 'OUTER_LAUNCHER_RISK=medium'
export CURSOR_STUB_RESULT="POST-PROCESSED OK"
RESULT_CORRUPT_RISK=$(PATH="$CURSOR_STUB_BIN:$PATH" run_collector bash "$OUT_CORRUPT_RISK" "$STDERR_CORRUPT_RISK")
assert_line "case corrupt-risk status" "STATUS=OK" "$RESULT_CORRUPT_RISK"
assert_line "case corrupt-risk reviewer file" "REVIEWER_FILE=${OUT_CORRUPT_RISK%.txt}-retry.txt" "$RESULT_CORRUPT_RISK"

# Case cap_hit: output file whose first line is STATUS=cap_hit is classified
# as STATUS=cap_hit by collect-agent-results.sh and does NOT
# trigger a retry (no .meta file required, no retry output created).
OUT_CAP="$TMPROOT/cap-hit.txt"
STDERR_CAP="$TMPROOT/cap-hit.stderr"
printf 'STATUS=cap_hit\nSTATUS=cap_hit TOTAL=9999 CAP=1 STEP=cursor-review\n' > "$OUT_CAP"
printf '0\n' > "${OUT_CAP}.done"
RESULT_CAP=$(run_collector bash "$OUT_CAP" "$STDERR_CAP")
assert_line "cap_hit status" "STATUS=cap_hit" "$RESULT_CAP"
if [[ -e "${OUT_CAP%.txt}-retry.txt" ]]; then
    fail "cap_hit should not generate a retry output"
else
    ok "cap_hit no retry output"
fi

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
