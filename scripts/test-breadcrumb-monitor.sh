#!/usr/bin/env bash
# test-breadcrumb-monitor.sh — offline harness for breadcrumb-monitor.sh.
# Covers the empty/non-empty sentinel paths and end-to-end coupling with
# a fake Family B script that installs larch_quiet_append_done_trap.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MON="$REPO_ROOT/scripts/breadcrumb-monitor.sh"
LIB_QUIET="$REPO_ROOT/scripts/lib-quiet.sh"

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

alloc_sentinels() {
    local prefix="$1"
    STREAM="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.stream.XXXXXX")"
    DONE="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.done.XXXXXX")"
    STATUS="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.status.XXXXXX")"
    QUIET="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.quiet.XXXXXX")"
    SURFACED="$(mktemp "$IMPLEMENT_TMPDIR/${prefix}.surfaced.XXXXXX")"
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
if [ "$elapsed" -gt 2 ]; then
    fail "test 1: non-empty surfaced took ${elapsed}s, expected <=2s"
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
if [ "$FAIL" -gt 0 ]; then
    echo "TESTS FAILED: $FAIL" >&2
    exit 1
fi
echo "OK: all breadcrumb-monitor.sh tests passed"
