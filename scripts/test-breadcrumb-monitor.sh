#!/usr/bin/env bash
# test-breadcrumb-monitor.sh — offline harness for breadcrumb-monitor.sh.
# Covers the empty/non-empty sentinel paths and end-to-end coupling with
# a fake Family B script that installs larch_quiet_append_done_trap.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
unset LARCH_BREADCRUMB_STREAM LARCH_QUIET_ACTIVE LARCH_QUIET_PID \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_BREADCRUMBS_SURFACED_FILE || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MON="$REPO_ROOT/scripts/breadcrumb-monitor.sh"
LIB_QUIET="$REPO_ROOT/scripts/lib-quiet.sh"
LIB_LARCH_LOG="$REPO_ROOT/scripts/lib-larch-log.sh"
LARCH_LOG_BATCHES="$REPO_ROOT/scripts/larch-log-batches.sh"

if ! [ -x "$MON" ]; then
    echo "FAIL: $MON not executable" >&2
    exit 1
fi

# Path validation in breadcrumb-monitor.sh requires sentinels to live under
# IMPLEMENT_TMPDIR / DESIGN_TMPDIR / REVIEW_TMPDIR. Use IMPLEMENT_TMPDIR here.
IMPLEMENT_TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/test-bm.XXXXXX")"
export IMPLEMENT_TMPDIR
trap 'rm -rf "$IMPLEMENT_TMPDIR"' EXIT

FAIL=0
fail() {
    echo "FAIL: $*" >&2
    FAIL=$((FAIL + 1))
}

pid_alive() {
    kill -0 "$1" 2>/dev/null
}

assert_pid_gone() {
    local pid="$1" label="$2" poll_count=0
    while (( poll_count < 5 )); do
        poll_count=$((poll_count + 1))
        if ! pid_alive "$pid"; then
            return 0
        fi
        sleep 1
    done
    fail "$label: pid $pid is still alive"
    return 1
}

alloc_sentinels() {
    local prefix="$1"
    STREAM="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.stream.XXXXXX")"
    DONE="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.done.XXXXXX")"
    STATUS="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.status.XXXXXX")"
    QUIET="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.quiet.XXXXXX")"
    SURFACED="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.surfaced.XXXXXX")"
}

make_monitor_fixture() {
    local name="$1" redactor_mode="$2"
    local root="$IMPLEMENT_TMPDIR/$name"
    mkdir -p "$root"
    cp "$MON" "$root/breadcrumb-monitor.sh"
    cp "$LIB_QUIET" "$root/lib-quiet.sh"
    cp "$LIB_LARCH_LOG" "$root/lib-larch-log.sh"
    cp "$LARCH_LOG_BATCHES" "$root/larch-log-batches.sh"
    case "$redactor_mode" in
        pass)
            cp "$REPO_ROOT/scripts/lib-redact-streaming.sh" "$root/lib-redact-streaming.sh"
            ;;
        fail)
            cat >"$root/lib-redact-streaming.sh" <<'SH'
#!/usr/bin/env bash
cat >/dev/null
exit 1
SH
            ;;
    esac
    chmod +x "$root/breadcrumb-monitor.sh" "$root/lib-redact-streaming.sh"
    printf '%s\n' "$root/breadcrumb-monitor.sh"
}

# ---------------------------------------------------------------------------
# Test 1: non-empty surfaced sentinel → monitor exits 0 immediately (resume).
# ---------------------------------------------------------------------------
alloc_sentinels t1
printf 'surfaced\n' >"$SURFACED"
ts1=$(date +%s)
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
ts2=$(date +%s)
if [ "$ec" -ne 0 ]; then
    fail "test 1: non-empty surfaced should exit 0, got $ec (out=$out)"
fi
elapsed=$((ts2 - ts1))
if [ "$elapsed" -gt 5 ]; then
    fail "test 1: non-empty surfaced took ${elapsed}s, expected <=5s"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 2: empty surfaced sentinel + empty done sentinel + late done write.
# Monitor must wait until done becomes non-empty, then exit 0.
# ---------------------------------------------------------------------------
alloc_sentinels t2
(
    sleep 2
    printf 'EXIT_CODE=0\n' >"$STATUS"
    printf 'EXIT_CODE=0\n' >"$DONE"
) &
WRITER_PID=$!
ts1=$(date +%s)
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
ts2=$(date +%s)
wait "$WRITER_PID" 2>/dev/null || true
if [ "$ec" -ne 0 ]; then
    fail "test 2: late done write should result in exit 0, got $ec (out=$out)"
fi
elapsed=$((ts2 - ts1))
if [ "$elapsed" -lt 2 ]; then
    fail "test 2: monitor returned in ${elapsed}s, expected >=2s (did it short-circuit on pre-created files?)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 3: late done write with non-zero EXIT_CODE → monitor prints failure tail.
# ---------------------------------------------------------------------------
alloc_sentinels t3
printf 'simulated failure log line\n' >"$QUIET"
(
    sleep 2
    printf 'EXIT_CODE=7\n' >"$STATUS"
    printf 'EXIT_CODE=7\n' >"$DONE"
) &
WRITER_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
wait "$WRITER_PID" 2>/dev/null || true
# Monitor itself exits 0 even when the Family B script failed; it only
# surfaces a failure tail. (The orchestrator reads the status file.)
if [ "$ec" -ne 0 ]; then
    fail "test 3: monitor should exit 0 even on script-failure, got $ec"
fi
if ! printf '%s' "$out" | grep -q "Failure tail (status=7)"; then
    fail "test 3: failure tail missing (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 4: end-to-end coupling — fake Family B script that sources lib-quiet,
# installs the done trap, sleeps, then exits. Monitor must block for the
# script's actual duration.
# ---------------------------------------------------------------------------
alloc_sentinels t4
FAKE_SCRIPT="$IMPLEMENT_TMPDIR/fake-family-b.sh"
cat >"$FAKE_SCRIPT" <<FAKE
#!/usr/bin/env bash
set -euo pipefail
source "$LIB_QUIET"
larch_quiet_append_done_trap
sleep 3
exit 0
FAKE
chmod +x "$FAKE_SCRIPT"

export LARCH_DONE_SENTINEL="$DONE"
export LARCH_STATUS_FILE="$STATUS"
# Launch the fake script in the background; pretend the orchestrator did so.
"$FAKE_SCRIPT" &
SCRIPT_PID=$!
ts1=$(date +%s)
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
ts2=$(date +%s)
wait "$SCRIPT_PID" 2>/dev/null || true
unset LARCH_DONE_SENTINEL LARCH_STATUS_FILE
if [ "$ec" -ne 0 ]; then
    fail "test 4: end-to-end coupling exit was $ec, expected 0 (out=$out)"
fi
elapsed=$((ts2 - ts1))
if [ "$elapsed" -lt 3 ]; then
    fail "test 4: monitor returned in ${elapsed}s, expected >=3s (no step-jumping permitted)"
fi
if ! grep -q "^EXIT_CODE=0" "$DONE"; then
    fail "test 4: done sentinel missing EXIT_CODE=0 content"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 5: end-to-end coupling with non-zero exit from fake script.
# ---------------------------------------------------------------------------
alloc_sentinels t5
FAKE_SCRIPT2="$IMPLEMENT_TMPDIR/fake-family-b-fail.sh"
cat >"$FAKE_SCRIPT2" <<FAKE
#!/usr/bin/env bash
set -euo pipefail
source "$LIB_QUIET"
larch_quiet_append_done_trap
sleep 1
exit 9
FAKE
chmod +x "$FAKE_SCRIPT2"

export LARCH_DONE_SENTINEL="$DONE"
export LARCH_STATUS_FILE="$STATUS"
"$FAKE_SCRIPT2" &
SCRIPT_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
wait "$SCRIPT_PID" 2>/dev/null || true
unset LARCH_DONE_SENTINEL LARCH_STATUS_FILE
if [ "$ec" -ne 0 ]; then
    fail "test 5: monitor exit was $ec, expected 0"
fi
if ! grep -q "^EXIT_CODE=9" "$STATUS"; then
    fail "test 5: status file missing EXIT_CODE=9 content"
fi
if ! grep -q "^EXIT_CODE=9" "$DONE"; then
    fail "test 5: done sentinel missing EXIT_CODE=9 content"
fi
if ! printf '%s' "$out" | grep -q "Failure tail (status=9)"; then
    fail "test 5: monitor failure tail missing"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 6: lib-quiet larch_quiet_init writes content to surfaced file when
# FD-3 is visible (pipe path). Verify it leaves content (not just a touch).
# ---------------------------------------------------------------------------
alloc_sentinels t6
FAKE_QUIET="$IMPLEMENT_TMPDIR/fake-quiet-init.sh"
cat >"$FAKE_QUIET" <<FAKE
#!/usr/bin/env bash
set -euo pipefail
source "$LIB_QUIET"
larch_quiet_init
emit OK
FAKE
chmod +x "$FAKE_QUIET"

export LARCH_BREADCRUMBS_SURFACED_FILE="$SURFACED"
# FD-3 visible: pipe stdout through cat. Run the fake script with
# LARCH_QUIET_DISABLE explicitly unset so larch_quiet_init takes its
# normal init path (the test harness top exports DISABLE=1 to keep the
# harness's own emit output direct).
env -u LARCH_QUIET_DISABLE "$FAKE_QUIET" | cat >/dev/null
unset LARCH_BREADCRUMBS_SURFACED_FILE

if [ ! -s "$SURFACED" ]; then
    fail "test 6: larch_quiet_init left surfaced file empty; resume-safety check at line 90 will be broken"
fi

# ---------------------------------------------------------------------------
# Test 7: stream growth is surfaced before the done sentinel completes.
# ---------------------------------------------------------------------------
alloc_sentinels t7
(
    sleep 1
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=growth-visible\n' >>"$STREAM"
    sleep 1
    printf 'EXIT_CODE=0\n' >"$STATUS"
    printf 'EXIT_CODE=0\n' >"$DONE"
) &
WRITER_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --poll-interval=1 2>&1) || ec=$?
ec=${ec:-0}
wait "$WRITER_PID" 2>/dev/null || true
if [ "$ec" -ne 0 ]; then
    fail "test 7: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "growth-visible"; then
    fail "test 7: stream growth breadcrumb was not surfaced (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 8: truncation/rotation emits WARN reset and resumes from offset zero.
# ---------------------------------------------------------------------------
alloc_sentinels t8
(
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=before-reset\n' >>"$STREAM"
    sleep 2
    : >"$STREAM"
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=after-reset\n' >>"$STREAM"
    sleep 1
    printf 'EXIT_CODE=0\n' >"$STATUS"
    printf 'EXIT_CODE=0\n' >"$DONE"
) &
WRITER_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --poll-interval=1 2>&1) || ec=$?
ec=${ec:-0}
wait "$WRITER_PID" 2>/dev/null || true
if [ "$ec" -ne 0 ]; then
    fail "test 8: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "WARN reset"; then
    fail "test 8: rotation warning missing (out=$out)"
fi
if ! printf '%s' "$out" | grep -q "after-reset"; then
    fail "test 8: post-reset breadcrumb missing (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 9: failure tail redacts PEM blocks.
# ---------------------------------------------------------------------------
alloc_sentinels t9
PEM_BEGIN='-----BEGIN RSA PRIVATE ''KEY-----'
PEM_END='-----END RSA PRIVATE ''KEY-----'
{
    printf '%s\n' "$PEM_BEGIN"
    printf '%s\n' 'MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu'
    printf '%s\n' "$PEM_END"
} >"$QUIET"
printf 'EXIT_CODE=9\n' >"$STATUS"
printf 'EXIT_CODE=9\n' >"$DONE"
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
if [ "$ec" -ne 0 ]; then
    fail "test 9: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "<REDACTED-PRIVATE-KEY>"; then
    fail "test 9: PEM placeholder missing from failure tail (out=$out)"
fi
if printf '%s' "$out" | grep -q "MIIBOgIBAAJB"; then
    fail "test 9: raw PEM material leaked in failure tail"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 10: path scope rejects outside session roots.
# ---------------------------------------------------------------------------
alloc_sentinels t10
outside="${TMPDIR:-/tmp}/outside-breadcrumb-monitor.$$"
: >"$outside"
set +e
out=$("$MON" \
    --stream "$outside" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1)
ec=$?
set -e
rm -f "$outside"
if [ "$ec" -eq 2 ]; then
    :
else
    fail "test 10: outside stream path should exit 2, got $ec (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 11: final partial line is flushed after the done sentinel.
# ---------------------------------------------------------------------------
alloc_sentinels t11
(
    sleep 1
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=tail-without-newline' >>"$STREAM"
    printf 'EXIT_CODE=0\n' >"$STATUS"
    printf 'EXIT_CODE=0\n' >"$DONE"
) &
WRITER_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --poll-interval=1 2>&1) || ec=$?
ec=${ec:-0}
wait "$WRITER_PID" 2>/dev/null || true
if [ "$ec" -ne 0 ]; then
    fail "test 11: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "tail-without-newline"; then
    fail "test 11: final partial line was not flushed (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 12: RESEARCH_TMPDIR is an accepted session root.
# ---------------------------------------------------------------------------
RESEARCH_TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/test-bm-research.XXXXXX")"
export RESEARCH_TMPDIR
STREAM="$(mktemp "$RESEARCH_TMPDIR/t11.stream.XXXXXX")"
DONE="$(mktemp "$RESEARCH_TMPDIR/t11.done.XXXXXX")"
STATUS="$(mktemp "$RESEARCH_TMPDIR/t11.status.XXXXXX")"
QUIET="$(mktemp "$RESEARCH_TMPDIR/t11.quiet.XXXXXX")"
SURFACED="$(mktemp "$RESEARCH_TMPDIR/t11.surfaced.XXXXXX")"
printf 'EXIT_CODE=0\n' >"$STATUS"
printf 'EXIT_CODE=0\n' >"$DONE"
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
rm -rf "$RESEARCH_TMPDIR"
unset RESEARCH_TMPDIR
if [ "$ec" -ne 0 ]; then
    fail "test 12: RESEARCH_TMPDIR path should be accepted, got $ec (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 13: symlink stream paths are rejected.
# ---------------------------------------------------------------------------
alloc_sentinels t13
link_stream="$IMPLEMENT_TMPDIR/t13.symlink"
ln -s "$STREAM" "$link_stream"
set +e
out=$("$MON" \
    --stream "$link_stream" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1)
ec=$?
set -e
if [ "$ec" -eq 2 ]; then
    :
else
    fail "test 13: symlink stream path should exit 2, got $ec (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 14: invalid breadcrumb categories are dropped.
# ---------------------------------------------------------------------------
alloc_sentinels t13
{
    printf 'larch:bc t=now d=0 p=1 s=test c=invalid text=must-not-print\n'
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=must-print\n'
} >"$STREAM"
printf 'EXIT_CODE=0\n' >"$STATUS"
printf 'EXIT_CODE=0\n' >"$DONE"
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
if [ "$ec" -ne 0 ]; then
    fail "test 14: monitor exit was $ec, expected 0"
fi
if printf '%s' "$out" | grep -q "must-not-print"; then
    fail "test 14: invalid category was emitted"
fi
if ! printf '%s' "$out" | grep -q "must-print"; then
    fail "test 14: valid category was not emitted"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 15: partial line is retained until a newline arrives.
# ---------------------------------------------------------------------------
alloc_sentinels t14
(
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=partial' >>"$STREAM"
    sleep 2
    printf -- '-complete\n' >>"$STREAM"
    sleep 1
    printf 'EXIT_CODE=0\n' >"$STATUS"
    printf 'EXIT_CODE=0\n' >"$DONE"
) &
WRITER_PID=$!
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --poll-interval=1 2>&1) || ec=$?
ec=${ec:-0}
wait "$WRITER_PID" 2>/dev/null || true
if [ "$ec" -ne 0 ]; then
    fail "test 15: monitor exit was $ec, expected 0"
fi
if printf '%s' "$out" | grep -q "text=partial$"; then
    fail "test 15: partial line surfaced before newline"
fi
if ! printf '%s' "$out" | grep -q "partial-complete"; then
    fail "test 15: completed line missing (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 16: redactor failure drops streamed line and surfaces a warning.
# ---------------------------------------------------------------------------
alloc_sentinels t15
MON_FAIL=$(make_monitor_fixture monitor-fail-line fail)
printf 'larch:bc t=now d=0 p=1 s=test c=progress text=top-secret\n' >"$STREAM"
printf 'EXIT_CODE=0\n' >"$STATUS"
printf 'EXIT_CODE=0\n' >"$DONE"
out=$("$MON_FAIL" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
if [ "$ec" -ne 0 ]; then
    fail "test 16: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "WARN redact-drop-line"; then
    fail "test 16: redactor failure warning missing (out=$out)"
fi
if printf '%s' "$out" | grep -q "top-secret"; then
    fail "test 16: raw streamed line leaked on redactor failure"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 17: failure-tail redactor failure warns and leaks no raw quiet-log bytes.
# ---------------------------------------------------------------------------
alloc_sentinels t16
MON_FAIL=$(make_monitor_fixture monitor-fail-tail fail)
printf 'very-secret-tail\n' >"$QUIET"
printf 'EXIT_CODE=7\n' >"$STATUS"
printf 'EXIT_CODE=7\n' >"$DONE"
out=$("$MON_FAIL" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
if [ "$ec" -ne 0 ]; then
    fail "test 17: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "WARN redact-drop-line"; then
    fail "test 17: failure-tail warning missing (out=$out)"
fi
if printf '%s' "$out" | grep -q "very-secret-tail"; then
    fail "test 17: raw failure-tail content leaked on redactor failure"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 18: non-breadcrumb lines are dropped and warned, never surfaced.
# ---------------------------------------------------------------------------
alloc_sentinels t18
printf 'not-a-breadcrumb secret\n' >"$STREAM"
printf 'EXIT_CODE=0\n' >"$STATUS"
printf 'EXIT_CODE=0\n' >"$DONE"
out=$("$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" 2>&1) || ec=$?
ec=${ec:-0}
if [ "$ec" -ne 0 ]; then
    fail "test 18: monitor exit was $ec, expected 0"
fi
if ! printf '%s' "$out" | grep -q "WARN drop-non-breadcrumb-line"; then
    fail "test 18: non-breadcrumb warning missing (out=$out)"
fi
if printf '%s' "$out" | grep -q "not-a-breadcrumb secret"; then
    fail "test 18: non-breadcrumb line leaked"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 19: timeout with paired PID sends TERM and exits 4.
# ---------------------------------------------------------------------------
alloc_sentinels t19
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t19.paired.XXXXXX")"
sleep 30 &
TARGET_PID=$!
printf '%s\n' "$TARGET_PID" >"$PAIRED_PID"
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
assert_pid_gone "$TARGET_PID" "test 19"
wait "$TARGET_PID" 2>/dev/null || true
if [ "$ec" -ne 4 ]; then
    fail "test 19: timeout should exit 4, got $ec (out=$out)"
fi
if printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
    fail "test 19: valid paired pid should not warn (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 20: TERM-ignoring child is KILLed after the grace window.
# ---------------------------------------------------------------------------
alloc_sentinels t20
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t20.paired.XXXXXX")"
bash -c 'trap "" TERM; while sleep 1; do :; done' &
TARGET_PID=$!
printf '%s\n' "$TARGET_PID" >"$PAIRED_PID"
ts1=$(date +%s)
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
ts2=$(date +%s)
assert_pid_gone "$TARGET_PID" "test 20"
wait "$TARGET_PID" 2>/dev/null || true
if [ "$ec" -ne 4 ]; then
    fail "test 20: timeout should exit 4, got $ec (out=$out)"
fi
elapsed=$((ts2 - ts1))
if [ "$elapsed" -lt 5 ]; then
    fail "test 20: TERM-ignoring child exited before KILL grace elapsed (${elapsed}s)"
fi
unset ec

# ---------------------------------------------------------------------------
# Tests 21-25+: missing and malformed paired PID files warn but still exit 4.
# ---------------------------------------------------------------------------
for malformed_case in missing empty alpha multiline crlf zero overcap nonascii; do
    alloc_sentinels "t21-${malformed_case}"
    PAIRED_PID="$IMPLEMENT_TMPDIR/t21-${malformed_case}.paired"
    case "$malformed_case" in
        missing) rm -f "$PAIRED_PID" ;;
        empty) : >"$PAIRED_PID" ;;
        alpha) printf 'not-a-number\n' >"$PAIRED_PID" ;;
        multiline) printf '12345\nstuff\npadding-padding-padding\n' >"$PAIRED_PID" ;;
        crlf) printf '12345\r\n' >"$PAIRED_PID" ;;
        zero) printf '0\n' >"$PAIRED_PID" ;;
        overcap) printf '123456789012345678901234567890123' >"$PAIRED_PID" ;;
        nonascii) printf '12\303\251\n' >"$PAIRED_PID" ;;
    esac
    set +e
    out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
        --stream "$STREAM" \
        --done-sentinel "$DONE" \
        --status-file "$STATUS" \
        --quiet-log "$QUIET" \
        --surfaced-sentinel "$SURFACED" \
        --paired-pid-file "$PAIRED_PID" 2>&1)
    ec=$?
    set -e
    if [ "$ec" -ne 4 ]; then
        fail "test 21-${malformed_case}: timeout should exit 4, got $ec (out=$out)"
    fi
    if ! printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
        fail "test 21-${malformed_case}: malformed pid warning missing (out=$out)"
    fi
    unset ec
done

# ---------------------------------------------------------------------------
# Test 26: stale syntactically valid PID does not abort or warn.
# ---------------------------------------------------------------------------
alloc_sentinels t26
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t26.paired.XXXXXX")"
sleep 0.1 &
TARGET_PID=$!
wait "$TARGET_PID" 2>/dev/null || true
printf '%s\n' "$TARGET_PID" >"$PAIRED_PID"
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
if [ "$ec" -ne 4 ]; then
    fail "test 26: stale pid timeout should exit 4, got $ec (out=$out)"
fi
if printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
    fail "test 26: stale but valid pid should not warn (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 26b: max-width PID plus trailing newline is accepted after strip.
# ---------------------------------------------------------------------------
alloc_sentinels t26b
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t26b.paired.XXXXXX")"
printf '12345678901234567890123456789012\n' >"$PAIRED_PID"
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
if [ "$ec" -ne 4 ]; then
    fail "test 26b: max-width pid timeout should exit 4, got $ec (out=$out)"
fi
if printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
    fail "test 26b: max-width pid should not warn (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
# Test 27: nested overwrite regression documents last-writer PID semantics.
# ---------------------------------------------------------------------------
alloc_sentinels t27
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t27.paired.XXXXXX")"
sleep 30 &
PARENT_PID=$!
printf '%s\n' "$PARENT_PID" >"$PAIRED_PID"
sleep 1 &
CHILD_PID=$!
printf '%s\n' "$CHILD_PID" >"$PAIRED_PID"
wait "$CHILD_PID" 2>/dev/null || true
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
if [ "$ec" -ne 4 ]; then
    fail "test 27: nested overwrite timeout should exit 4, got $ec (out=$out)"
fi
if printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
    fail "test 27: stale overwritten pid should not warn (out=$out)"
fi
if ! pid_alive "$PARENT_PID"; then
    fail "test 27: parent pid was signaled despite pid file containing child pid"
fi
assert_pid_gone "$CHILD_PID" "test 27"
kill "$PARENT_PID" 2>/dev/null || true
wait "$PARENT_PID" 2>/dev/null || true
unset ec

# ---------------------------------------------------------------------------
# Test 28: lib-quiet paired PID writer integrates with timeout signaling.
# ---------------------------------------------------------------------------
alloc_sentinels t28
PAIRED_PID="$(mktemp "$IMPLEMENT_TMPDIR/t28.paired.XXXXXX")"
FAKE_SCRIPT3="$IMPLEMENT_TMPDIR/fake-family-b-paired.sh"
cat >"$FAKE_SCRIPT3" <<FAKE
#!/usr/bin/env bash
set -euo pipefail
source "$LIB_QUIET"
export IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR}"
export LARCH_PAIRED_PID_FILE="${PAIRED_PID}"
larch_quiet_write_paired_pid_file
trap '' TERM
sleep 30
FAKE
chmod +x "$FAKE_SCRIPT3"
"$FAKE_SCRIPT3" &
TARGET_PID=$!
for _ in 1 2 3 4 5; do
    [[ -s "$PAIRED_PID" ]] && break
    sleep 0.1
done
set +e
out=$(LARCH_BM_TEST_MODE=1 LARCH_BM_TEST_TIMEOUT_SECONDS=1 "$MON" \
    --stream "$STREAM" \
    --done-sentinel "$DONE" \
    --status-file "$STATUS" \
    --quiet-log "$QUIET" \
    --surfaced-sentinel "$SURFACED" \
    --paired-pid-file "$PAIRED_PID" 2>&1)
ec=$?
set -e
assert_pid_gone "$TARGET_PID" "test 28"
wait "$TARGET_PID" 2>/dev/null || true
if [ "$ec" -ne 4 ]; then
    fail "test 28: timeout should exit 4, got $ec (out=$out)"
fi
if printf '%s' "$out" | grep -q "WARN paired-pid-file-missing"; then
    fail "test 28: real writer pid should not warn (out=$out)"
fi
unset ec

# ---------------------------------------------------------------------------
if [ "$FAIL" -gt 0 ]; then
    echo "TESTS FAILED: $FAIL" >&2
    exit 1
fi
echo "OK: all breadcrumb-monitor.sh tests passed"
