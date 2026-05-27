#!/usr/bin/env bash
# Regression test for scripts/run-external-agent.sh output-path validation.
#
# Wired into: make test-run-external-agent (Makefile shard test-harnesses-5).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/run-external-agent.sh"
HELPER="$REPO_ROOT/scripts/lib-validate-meta-path.sh"
TMPDIR="$(mktemp -d /tmp/larch-test-run-external-agent-XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR/execution-issues.md"
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

STDIN_PROBE="$TMPDIR/stdin-probe.sh"
cat > "$STDIN_PROBE" <<'STDIN_PROBE_EOF'
#!/usr/bin/env bash
set -euo pipefail
fd0=""
case "$(uname -s)" in
    Linux)
        fd0=$(readlink "/proc/$$/fd/0" 2>/dev/null || true)
        ;;
    Darwin)
        fd0=$(lsof -p "$$" -a -d 0 -F n 2>/dev/null | sed -n 's/^n//p' | head -1 || true)
        ;;
esac
if [[ -z "$fd0" ]]; then
    if IFS= read -r line; then
        fd0="read:$line"
    else
        fd0="eof"
    fi
fi
printf 'FD0=%s\n' "$fd0"
STDIN_PROBE_EOF
chmod +x "$STDIN_PROBE"

run_stdin_probe() {
    local label="$1"
    local tool="$2"
    local output="$3"
    shift 3
    local input="$TMPDIR/${label}.stdin"
    printf 'wrapper-stdin-%s\n' "$label" > "$input"
    RUN_STDOUT="$TMPDIR/${label}.stdout"
    RUN_STDERR="$TMPDIR/${label}.stderr"
    set +e
    "$WRAPPER" --tool "$tool" --output "$output" --timeout 5 "$@" -- "$STDIN_PROBE" < "$input" >"$RUN_STDOUT" 2>"$RUN_STDERR"
    RUN_CODE=$?
    set -e
}

assert_no_artifacts() {
    local label="$1"
    local output="$2"
    local suffix
    for suffix in "" ".done" ".inner.done" ".meta" ".diag"; do
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
# Review launcher rejection is covered in test-launch-review.sh.
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

# 13. jq CMD_JSON serialization failure path: the EXIT trap must write the
# real exit code (1) to <output>.done, not the pre-launch default sentinel
# (99). Regression guard for the EXIT_CODE=1 line preceding `exit 1` on the
# jq-failure branch in run-external-agent.sh.
JQ_FAIL_OUT="$TMPDIR/jq-fail-output.txt"
JQ_SHIM_DIR="$TMPDIR/jq-shim"
mkdir -p "$JQ_SHIM_DIR"
cat > "$JQ_SHIM_DIR/jq" <<'JQ_SHIM_EOF'
#!/bin/sh
echo "stub jq: forced failure" >&2
exit 1
JQ_SHIM_EOF
chmod +x "$JQ_SHIM_DIR/jq"
RUN_STDOUT="$TMPDIR/jq-fail.stdout"
RUN_STDERR="$TMPDIR/jq-fail.stderr"
set +e
PATH="$JQ_SHIM_DIR:$PATH" "$WRAPPER" --tool codex --output "$JQ_FAIL_OUT" --timeout 5 -- bash -c 'printf should-not-run' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "jq-fail exit" "1" "$RUN_CODE"
assert_grep "jq-fail stderr" "ERROR: jq failed to serialize argv to CMD_JSON" "$RUN_STDERR"
assert_file_content "jq-fail done" "${JQ_FAIL_OUT}.done" "1"
if [[ -e "${JQ_FAIL_OUT}.meta" ]]; then
    fail "jq-fail no meta: ${JQ_FAIL_OUT}.meta should not exist on jq-failure path"
else
    pass
fi

# 14. Inner-sentinel mode writes <output>.inner.done and leaves the public
# <output>.done for a wrapping launcher to publish after post-processing.
INNER_OUT="$TMPDIR/inner-mode.txt"
RUN_STDOUT="$TMPDIR/inner-mode.stdout"
RUN_STDERR="$TMPDIR/inner-mode.stderr"
set +e
RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done "$WRAPPER" --tool codex --output "$INNER_OUT" --timeout 5 --capture-stdout -- bash -c 'printf inner' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "inner-mode exit" "0" "$RUN_CODE"
assert_file_content "inner-mode output" "$INNER_OUT" "inner"
assert_file_content "inner-mode inner done" "${INNER_OUT}.inner.done" "0"
if [[ -e "${INNER_OUT}.done" ]]; then
    fail "inner-mode public done should not exist"
else
    pass
fi

# 15. Default mode keeps today's public .done behavior and does not leave an
# inner sentinel.
DEFAULT_OUT="$TMPDIR/default-mode.txt"
run_subject "default-mode" "$DEFAULT_OUT" --capture-stdout -- bash -c 'printf default'
assert_equals "default-mode exit" "0" "$RUN_CODE"
assert_file_content "default-mode done" "${DEFAULT_OUT}.done" "0"
if [[ -e "${DEFAULT_OUT}.inner.done" ]]; then
    fail "default-mode inner sentinel should not exist"
else
    pass
fi

# 15b-15f. Codex-specific stdin redirect applies to every spawn branch while
# non-Codex tools continue to inherit wrapper stdin.
STDIN_DEFAULT_OUT="$TMPDIR/stdin-default.txt"
run_stdin_probe "stdin-codex-default" codex "$STDIN_DEFAULT_OUT"
assert_equals "stdin-codex-default exit" "0" "$RUN_CODE"
assert_grep "stdin-codex-default fd0" "/dev/null" "$RUN_STDOUT"

STDIN_CAPTURE_OUT="$TMPDIR/stdin-capture.txt"
run_stdin_probe "stdin-codex-capture" codex "$STDIN_CAPTURE_OUT" --capture-stdout
assert_equals "stdin-codex-capture exit" "0" "$RUN_CODE"
assert_grep "stdin-codex-capture fd0" "/dev/null" "$STDIN_CAPTURE_OUT"

STDIN_CAPTURE_ONLY_OUT="$TMPDIR/stdin-capture-only.txt"
run_stdin_probe "stdin-codex-capture-only" codex "$STDIN_CAPTURE_ONLY_OUT" --capture-stdout-only
assert_equals "stdin-codex-capture-only exit" "0" "$RUN_CODE"
assert_grep "stdin-codex-capture-only fd0" "/dev/null" "$STDIN_CAPTURE_ONLY_OUT"

if command -v stdbuf >/dev/null 2>&1; then
    STDIN_STDBUF_OUT="$TMPDIR/stdin-capture-only-stdbuf.txt"
    RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF=1 run_stdin_probe "stdin-codex-capture-only-stdbuf" codex "$STDIN_STDBUF_OUT" --capture-stdout-only
    assert_equals "stdin-codex-capture-only-stdbuf exit" "0" "$RUN_CODE"
    assert_grep "stdin-codex-capture-only-stdbuf fd0" "/dev/null" "$STDIN_STDBUF_OUT"
else
    printf 'SKIP: stdbuf not on PATH\n'
fi

STDIN_CURSOR_OUT="$TMPDIR/stdin-cursor.txt"
run_stdin_probe "stdin-cursor-control" cursor "$STDIN_CURSOR_OUT"
assert_equals "stdin-cursor-control exit" "0" "$RUN_CODE"
assert_grep "stdin-cursor-control meta tool" "^TOOL=cursor$" "${STDIN_CURSOR_OUT}.meta"

# 16. Pre-launch cleanup removes stale public and inner sentinels in either mode.
CLEANUP_OUT="$TMPDIR/cleanup-mode.txt"
printf 'stale-public\n' > "${CLEANUP_OUT}.done"
printf 'stale-inner\n' > "${CLEANUP_OUT}.inner.done"
run_subject "cleanup-default" "$CLEANUP_OUT" --capture-stdout -- bash -c 'printf cleanup'
assert_equals "cleanup-default exit" "0" "$RUN_CODE"
assert_file_content "cleanup-default done" "${CLEANUP_OUT}.done" "0"
if [[ -e "${CLEANUP_OUT}.inner.done" ]]; then
    fail "cleanup-default stale inner sentinel should be removed"
else
    pass
fi

CLEANUP_INNER_OUT="$TMPDIR/cleanup-inner-mode.txt"
printf 'stale-public\n' > "${CLEANUP_INNER_OUT}.done"
printf 'stale-inner\n' > "${CLEANUP_INNER_OUT}.inner.done"
RUN_STDOUT="$TMPDIR/cleanup-inner.stdout"
RUN_STDERR="$TMPDIR/cleanup-inner.stderr"
set +e
RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done "$WRAPPER" --tool codex --output "$CLEANUP_INNER_OUT" --timeout 5 --capture-stdout -- bash -c 'printf cleanup-inner' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "cleanup-inner exit" "0" "$RUN_CODE"
assert_file_content "cleanup-inner inner done" "${CLEANUP_INNER_OUT}.inner.done" "0"
if [[ -e "${CLEANUP_INNER_OUT}.done" ]]; then
    fail "cleanup-inner stale public sentinel should be removed"
else
    pass
fi

# 17. Unsupported inner-sentinel suffixes fail before side effects.
BOGUS_OUT="$TMPDIR/bogus-inner-mode.txt"
RUN_STDOUT="$TMPDIR/bogus-inner.stdout"
RUN_STDERR="$TMPDIR/bogus-inner.stderr"
set +e
RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.bogus "$WRAPPER" --tool codex --output "$BOGUS_OUT" --timeout 5 --capture-stdout -- bash -c 'printf should-not-run' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "bogus-inner exit" "1" "$RUN_CODE"
assert_grep "bogus-inner stderr" "ERROR: invalid RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX value '.bogus'; expected '.inner.done'" "$RUN_STDERR"
assert_no_artifacts "bogus-inner no side effects" "$BOGUS_OUT"

# 18. Wrapper timeout diagnostics stay on stderr so capture-stdout-only output
# remains parseable JSONL.
TIMEOUT_OUT="$TMPDIR/timeout-events.jsonl"
RUN_STDOUT="$TMPDIR/timeout-events.stdout"
RUN_STDERR="$TMPDIR/timeout-events.stderr"
set +e
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 "$WRAPPER" --tool codex --output "$TIMEOUT_OUT" --timeout 1 --capture-stdout-only -- \
    bash -c 'printf "{\"type\":\"token_usage\"}\n"; sleep 2' >"$RUN_STDOUT" 2>"$RUN_STDERR"
RUN_CODE=$?
set -e
assert_equals "timeout-events exit" "124" "$RUN_CODE"
assert_grep "timeout-events stderr start" "TIMED OUT after 0 minutes, killing" "$RUN_STDERR"
assert_grep "timeout-events stderr final" "TIMED OUT (exit code 124" "$RUN_STDERR"
assert_file_content "timeout-events output" "$TIMEOUT_OUT" '{"type":"token_usage"}'
if grep -Fq 'TIMED OUT' "$TIMEOUT_OUT"; then
    fail "timeout-events output must stay free of wrapper diagnostics"
else
    pass
fi
assert_grep "timeout-events diag" "limit: 1s" "${TIMEOUT_OUT}.diag"

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-run-external-agent.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-run-external-agent.sh - %s assertions passed\n' "$PASS"
