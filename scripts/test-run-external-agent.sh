#!/usr/bin/env bash
# Regression test for scripts/run-external-agent.sh output-path validation.
#
# Wired into: make test-run-external-agent (Makefile shard test-harnesses-5).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/run-external-agent.sh"
HELPER="$REPO_ROOT/scripts/lib-validate-meta-path.sh"
TMPDIR="$(mktemp -d /tmp/larch-test-run-external-agent-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

PASS=0
FAIL=0
FAIL_DETAILS=()
RUN_CODE=0
RUN_STDOUT=""
RUN_STDERR=""

fail() {
    FAIL=$((FAIL + 1))
    FAIL_DETAILS+=("$1")
}

pass() {
    PASS=$((PASS + 1))
}

assert_equals() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

assert_file_content() {
    local label="$1"
    local path="$2"
    local expected="$3"
    if [[ -f "$path" && "$(cat "$path")" == "$expected" ]]; then
        pass
    else
        fail "$label: expected $path to contain '$expected'"
    fi
}

assert_grep() {
    local label="$1"
    local pattern="$2"
    local path="$3"
    if grep -q -- "$pattern" "$path"; then
        pass
    else
        fail "$label: expected $path to match $pattern"
    fi
}

run_subject() {
    local label="$1"
    local output="$2"
    shift 2
    RUN_STDOUT="$TMPDIR/${label}.stdout"
    RUN_STDERR="$TMPDIR/${label}.stderr"
    set +e
    "$WRAPPER" --tool codex --output "$output" --timeout 5 "$@" >"$RUN_STDOUT" 2>"$RUN_STDERR"
    RUN_CODE=$?
    set -e
}

assert_no_artifacts() {
    local label="$1"
    local output="$2"
    local suffix
    for suffix in "" ".done" ".meta" ".diag"; do
        if [[ -e "${output}${suffix}" ]]; then
            fail "$label: unexpected artifact ${output}${suffix}"
        else
            pass
        fi
    done
}

assert_rejected_output() {
    local label="$1"
    local output="$2"
    run_subject "$label" "$output" -- bash -c 'printf should-not-run'
    assert_equals "$label exit" "1" "$RUN_CODE"
    assert_grep "$label stderr" "ERROR: --output contains bytes outside" "$RUN_STDERR"
    assert_no_artifacts "$label no side effects" "$output"
}

assert_successful_capture() {
    local label="$1"
    local output="$2"
    mkdir -p "$(dirname "$output")"
    run_subject "$label" "$output" --capture-stdout -- bash -c 'printf hi'
    assert_equals "$label exit" "0" "$RUN_CODE"
    assert_file_content "$label output" "$output" "hi"
    assert_file_content "$label done" "${output}.done" "0"
    assert_grep "$label meta tool" "^TOOL=codex$" "${output}.meta"
    assert_grep "$label meta timeout" "^TIMEOUT=5$" "${output}.meta"
    assert_grep "$label meta capture" "^CAPTURE_STDOUT=true$" "${output}.meta"
    assert_grep "$label meta output" "^OUTPUT_FILE=$output$" "${output}.meta"
    assert_grep "$label meta command" "^CMD_JSON=" "${output}.meta"
}

# 1. Control case.
assert_successful_capture "control" "$TMPDIR/normal-output.txt"

# 2-8. Rejection cases, including LF as a single bash string.
assert_rejected_output "reject-equals" "$TMPDIR/bad=path.txt"
assert_rejected_output "reject-lf" "$TMPDIR/bad"$'\n'"output.txt"
assert_rejected_output "reject-cr" "$TMPDIR/bad"$'\r'"output.txt"
assert_rejected_output "reject-tab" "$TMPDIR/bad"$'\t'"output.txt"
assert_rejected_output "reject-del" "$TMPDIR/bad"$'\x7f'"output.txt"
assert_rejected_output "reject-space" "$TMPDIR/bad output.txt"
assert_rejected_output "reject-utf8" "$TMPDIR/bad-€-output.txt"

# 9-10. Positive path alphabet coverage.
assert_successful_capture "nested-dir" "$TMPDIR/sub/dir/normal-output.txt"
assert_successful_capture "safe-punctuation" "$TMPDIR/foo.bar-baz_qux.txt"

# 11. Empty output is rejected by required-option validation.
run_subject "reject-empty" "" -- bash -c 'printf should-not-run'
assert_equals "reject-empty exit" "1" "$RUN_CODE"
assert_grep "reject-empty stderr" "--output requires a value" "$RUN_STDERR"

# 11b. --timeout 0 is rejected before side effects (parallel to #1115 + the
# Gemini reviewer launcher's analogous rejection in test-launch-gemini-review.sh).
TIMEOUT_ZERO_OUT="$TMPDIR/timeout-zero.txt"
RUN_STDOUT="$TMPDIR/reject-timeout-zero.stdout"
RUN_STDERR="$TMPDIR/reject-timeout-zero.stderr"
set +e
"$WRAPPER" --tool codex --output "$TIMEOUT_ZERO_OUT" --timeout 0 -- bash -c 'printf should-not-run' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "reject-timeout-zero exit" "1" "$RUN_CODE"
assert_grep "reject-timeout-zero stderr" "--timeout must be a positive integer" "$RUN_STDERR"
assert_no_artifacts "reject-timeout-zero no side effects" "$TIMEOUT_ZERO_OUT"

# 12. Helper invariants.
if head -n 1 "$HELPER" | grep -qv '^#!' && [[ ! -x "$HELPER" ]]; then
    pass
else
    fail "helper should have no shebang and should not be executable"
fi

if bash -c 'source "$1"' bash "$HELPER" >"$TMPDIR/helper-source.stdout" 2>"$TMPDIR/helper-source.stderr" \
    && [[ ! -s "$TMPDIR/helper-source.stdout" ]] \
    && [[ ! -s "$TMPDIR/helper-source.stderr" ]]; then
    pass
else
    fail "helper source should emit no stdout/stderr"
fi

if bash -c 'source "$1"; source "$1"; [[ "${LARCH_VALIDATE_META_PATH_LOADED:-}" == "1" ]]' bash "$HELPER" >"$TMPDIR/helper-double.stdout" 2>"$TMPDIR/helper-double.stderr" \
    && [[ ! -s "$TMPDIR/helper-double.stdout" ]] \
    && [[ ! -s "$TMPDIR/helper-double.stderr" ]]; then
    pass
else
    fail "helper double source should be idempotent"
fi

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-run-external-agent.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-run-external-agent.sh - %s assertions passed\n' "$PASS"
