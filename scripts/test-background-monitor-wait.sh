#!/usr/bin/env bash
# Regression harness for the Family B background-writer + breadcrumb-monitor wait contract.

set -uo pipefail

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-test-bgmw-XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
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

FAKE_WRITER="$TMPROOT/fake-writer.sh"
cat >"$FAKE_WRITER" <<'FAKE_WRITER_EOF'
#!/usr/bin/env bash
set -uo pipefail
trap 'exit 143' TERM
printf '%s\n' "$$" > "$LARCH_PAIRED_PID_FILE"
printf 'EXIT_CODE=%s\n' "${FAKE_EXIT:-0}" > "$LARCH_STATUS_FILE"
printf 'EXIT_CODE=%s\n' "${FAKE_EXIT:-0}" > "$LARCH_DONE_SENTINEL"
_remaining=$(( ${FAKE_SLEEP:-5} * 10 ))
while [ "$_remaining" -gt 0 ]; do
    if [ -n "${TMPDIR_WRITER_STOP_FILE:-}" ] && [ -f "$TMPDIR_WRITER_STOP_FILE" ]; then
        exit 143
    fi
    _remaining=$((_remaining - 1))
    sleep 0.1
done
touch "$TMPDIR_WRITER_DONE_MARKER"
exit "${FAKE_EXIT:-0}"
FAKE_WRITER_EOF
chmod +x "$FAKE_WRITER"

FAKE_MONITOR="$TMPROOT/fake-monitor.sh"
cat >"$FAKE_MONITOR" <<'FAKE_MONITOR_EOF'
#!/usr/bin/env bash
set -uo pipefail
while [ ! -s "$LARCH_DONE_SENTINEL" ]; do
    sleep 0.05
done
if [ "${FAKE_MONITOR_EXIT:-0}" = "4" ]; then
    if [ -n "${TMPDIR_WRITER_STOP_FILE:-}" ]; then
        : > "$TMPDIR_WRITER_STOP_FILE"
    fi
    _wait_pid_tries=0
    while [ ! -s "$LARCH_PAIRED_PID_FILE" ] && [ "$_wait_pid_tries" -lt 20 ]; do
        _wait_pid_tries=$((_wait_pid_tries + 1))
        sleep 0.05
    done
    if [ -s "$LARCH_PAIRED_PID_FILE" ]; then
        kill "$(cat "$LARCH_PAIRED_PID_FILE")" 2>/dev/null || true
    fi
fi
exit "${FAKE_MONITOR_EXIT:-0}"
FAKE_MONITOR_EOF
chmod +x "$FAKE_MONITOR"

run_wrapper() {
    local label="$1" fake_exit="$2" fake_monitor_exit="$3" fake_sleep="$4" no_wait="$5"
    local case_dir="$TMPROOT/$label"
    mkdir -p "$case_dir"
    export LARCH_DONE_SENTINEL="$case_dir/done"
    export LARCH_STATUS_FILE="$case_dir/status"
    export LARCH_PAIRED_PID_FILE="$case_dir/pid"
    export TMPDIR_WRITER_DONE_MARKER="$case_dir/writer-finished"
    export TMPDIR_WRITER_STOP_FILE="$case_dir/writer-stop"
    : > "$LARCH_DONE_SENTINEL"
    : > "$LARCH_STATUS_FILE"
    : > "$LARCH_PAIRED_PID_FILE"

    set +e
    FAKE_EXIT="$fake_exit" FAKE_MONITOR_EXIT="$fake_monitor_exit" FAKE_SLEEP="$fake_sleep" \
        FAKE_WRITER="$FAKE_WRITER" FAKE_MONITOR="$FAKE_MONITOR" NO_WAIT="$no_wait" \
        bash -s <<'WRAPPER_EOF'
"$FAKE_WRITER" &
WRITER_PID=$!

monitor_rc=0
"$FAKE_MONITOR" || monitor_rc=$?

if [ "$NO_WAIT" = "1" ]; then
    exit "$monitor_rc"
fi

if [ "$monitor_rc" -eq 0 ]; then
    writer_rc=0
    wait "$WRITER_PID" || writer_rc=$?
    exit "$writer_rc"
else
    wait "$WRITER_PID" 2>/dev/null || true
    exit "$monitor_rc"
fi
WRAPPER_EOF
    local rc=$?
    set -e
    RUN_WRAPPER_RC="$rc"
}

assert_wrapper_exit_and_marker() {
    local code="$1"
    local rc
    run_wrapper "exit-$code" "$code" 0 1 0
    rc="$RUN_WRAPPER_RC"
    if [ "$rc" -eq "$code" ]; then
        ok "wrapper propagates writer exit $code"
    else
        fail "wrapper exit for writer $code: expected $code got $rc"
    fi
    if [ -f "$TMPROOT/exit-$code/writer-finished" ]; then
        ok "wrapper waited for writer marker $code"
    else
        fail "wrapper returned before writer marker $code"
    fi
}

for code in 0 3 4 5 6; do
    assert_wrapper_exit_and_marker "$code"
done

run_wrapper "monitor-2" 0 2 1 0
rc="$RUN_WRAPPER_RC"
if [ "$rc" -eq 2 ]; then
    ok "monitor failure exit 2 is preserved"
else
    fail "monitor failure exit: expected 2 got $rc"
fi

start=$(date +%s)
run_wrapper "monitor-4" 0 4 30 0
rc="$RUN_WRAPPER_RC"
end=$(date +%s)
elapsed=$((end - start))
if [ "$rc" -eq 4 ] && [ "$elapsed" -le 12 ]; then
    ok "monitor timeout branch is bounded"
else
    fail "monitor timeout branch expected rc=4 elapsed<=12s, got rc=$rc elapsed=${elapsed}s"
fi

run_wrapper "no-wait-negative" 0 0 5 1
rc="$RUN_WRAPPER_RC"
if [ "$rc" -eq 0 ] && [ ! -f "$TMPROOT/no-wait-negative/writer-finished" ]; then
    ok "negative control returns before writer marker without wait"
else
    fail "negative control did not expose missing-wait bug"
fi
if [ -s "$TMPROOT/no-wait-negative/pid" ]; then
    kill "$(cat "$TMPROOT/no-wait-negative/pid")" 2>/dev/null || true
fi

if [ "$FAIL" -ne 0 ]; then
    printf '\nFAIL: test-background-monitor-wait.sh (%d failure(s))\n' "$FAIL" >&2
    printf ' - %s\n' "${FAILED[@]}" >&2
    exit 1
fi

echo "PASS: test-background-monitor-wait.sh"
