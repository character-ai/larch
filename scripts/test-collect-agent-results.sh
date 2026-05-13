#!/usr/bin/env bash
# Regression coverage for collect-agent-results.sh transient-network retry routing.

set -uo pipefail

export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-collect-agent-results-XXXXXX")"
trap 'rm -rf "$TMPROOT" 2>/dev/null' EXIT

PASS=0
FAIL=0
FAILED=()

ok() {
    PASS=$((PASS + 1))
    echo "  ok: $1"
}

fail() {
    FAIL=$((FAIL + 1))
    FAILED+=("$1")
    echo "  FAIL: $1" >&2
}

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

assert_line_regex() {
    local label="$1"
    local pattern="$2"
    local haystack="$3"
    if printf '%s\n' "$haystack" | grep -Eq "$pattern"; then
        ok "$label"
    else
        fail "$label: missing pattern '$pattern'"
        printf '%s\n' "$haystack" >&2
    fi
}

assert_no_retry_file() {
    local label="$1"
    local output="$2"
    local retry_output="${output%.txt}-retry.txt"
    if [[ -e "$retry_output" || -e "${retry_output}.done" ]]; then
        fail "$label: retry artifacts should not exist"
    else
        ok "$label"
    fi
}

require_tool jq

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'CURSOR_STUB'
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
[[ -n "$helper" ]] || exit 40
exec bash "$helper" "${args[@]}"
CURSOR_STUB
chmod +x "$STUB_BIN/cursor"
PATH="$STUB_BIN:$PATH"
export PATH

SUCCESS_HELPER="$TMPROOT/retry-success.sh"
cat > "$SUCCESS_HELPER" <<'SUCCESS_HELPER_EOF'
#!/usr/bin/env bash
set -euo pipefail
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
printf 'retry produced usable reviewer output\n' > "$out"
SUCCESS_HELPER_EOF
chmod +x "$SUCCESS_HELPER"

FAIL_HELPER="$TMPROOT/retry-fail.sh"
cat > "$FAIL_HELPER" <<'FAIL_HELPER_EOF'
#!/usr/bin/env bash
exit 7
FAIL_HELPER_EOF
chmod +x "$FAIL_HELPER"

json_array() {
    local helper="$1"
    local output="$2"
    jq -cn --args '$ARGS.positional' -- cursor agent --workspace "$TMPROOT" --helper "$helper" --output "$output"
}

write_meta() {
    local output="$1"
    local helper="$2"
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$(json_array "$helper" "$output")"
    } > "${output}.meta"
}

run_collector() {
    local timeout="$1"
    local output="$2"
    local health
    health="$TMPROOT/$(basename "$output").health"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout "$timeout" --write-health "$health" "$output" 2>"${health}.stderr"
}

# C_T1: initial FAILED with transient network diagnostic retries and recovers.
OUT_T1="$TMPROOT/cursor-t1.txt"
: > "$OUT_T1"
printf '1\n' > "${OUT_T1}.done"
printf 'Could not resolve host: example.invalid\n' > "${OUT_T1}.diag"
write_meta "$OUT_T1" "$SUCCESS_HELPER"
RESULT_T1=$(run_collector 5 "$OUT_T1")
assert_line "C_T1 retry file" "REVIEWER_FILE=${OUT_T1%.txt}-retry.txt" "$RESULT_T1"
assert_line "C_T1 status" "STATUS=OK" "$RESULT_T1"
assert_line "C_T1 healthy" "HEALTHY=true" "$RESULT_T1"

# C_T2: transient initial FAILED retries, but retry failure is reported as EMPTY_OUTPUT.
OUT_T2="$TMPROOT/cursor-t2.txt"
: > "$OUT_T2"
printf '1\n' > "${OUT_T2}.done"
printf 'Could not resolve host: example.invalid\n' > "${OUT_T2}.diag"
write_meta "$OUT_T2" "$FAIL_HELPER"
RESULT_T2=$(run_collector 5 "$OUT_T2")
assert_line "C_T2 status" "STATUS=EMPTY_OUTPUT" "$RESULT_T2"
assert_line "C_T2 healthy" "HEALTHY=false" "$RESULT_T2"
assert_line_regex "C_T2 retry failure reason" '^FAILURE_REASON=Retry also failed:' "$RESULT_T2"

# C_T3: non-transient FAILED does not retry even with valid metadata.
OUT_T3="$TMPROOT/cursor-t3.txt"
: > "$OUT_T3"
printf '1\n' > "${OUT_T3}.done"
printf 'reviewer prompt malformed\n' > "${OUT_T3}.diag"
write_meta "$OUT_T3" "$SUCCESS_HELPER"
RESULT_T3=$(run_collector 5 "$OUT_T3")
assert_line "C_T3 status" "STATUS=FAILED" "$RESULT_T3"
assert_line "C_T3 healthy" "HEALTHY=false" "$RESULT_T3"
assert_no_retry_file "C_T3 no retry" "$OUT_T3"

# C_T4: SENTINEL_TIMEOUT with transient diagnostic enters retry and recovers.
OUT_T4="$TMPROOT/cursor-t4.txt"
: > "$OUT_T4"
printf 'TLS handshake failed while connecting\n' > "${OUT_T4}.diag"
write_meta "$OUT_T4" "$SUCCESS_HELPER"
RESULT_T4=$(run_collector 1 "$OUT_T4")
assert_line "C_T4 retry file" "REVIEWER_FILE=${OUT_T4%.txt}-retry.txt" "$RESULT_T4"
assert_line "C_T4 status" "STATUS=OK" "$RESULT_T4"
assert_line "C_T4 healthy" "HEALTHY=true" "$RESULT_T4"

# C_T5: SENTINEL_TIMEOUT without a transient diagnostic remains a timeout.
OUT_T5="$TMPROOT/cursor-t5.txt"
: > "$OUT_T5"
write_meta "$OUT_T5" "$SUCCESS_HELPER"
RESULT_T5=$(run_collector 1 "$OUT_T5")
assert_line "C_T5 status" "STATUS=SENTINEL_TIMEOUT" "$RESULT_T5"
assert_line "C_T5 healthy" "HEALTHY=false" "$RESULT_T5"
assert_no_retry_file "C_T5 no retry" "$OUT_T5"

if [[ "$FAIL" -ne 0 ]]; then
    printf '\nFAIL: test-collect-agent-results.sh (%d failure(s))\n' "$FAIL" >&2
    printf ' - %s\n' "${FAILED[@]}" >&2
    exit 1
fi

echo "PASS: test-collect-agent-results.sh - transient collector retry routing pinned"
