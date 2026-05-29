#!/usr/bin/env bash
# test-ci-wait.sh — Offline regression tests for scripts/ci-wait.sh.
# Tests the poll-count timeout, suspend-resilience, and happy paths.
# Wired via: make test-ci-wait

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE="$(mktemp -d -t ci-wait-test.XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
unset LARCH_BREADCRUMB_STREAM LARCH_QUIET_ACTIVE LARCH_QUIET_PID \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_BREADCRUMBS_SURFACED_FILE || true
export LARCH_EXECUTION_ISSUES_LOG="$TMP_BASE/execution-issues.md"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() { rm -rf "$TMP_BASE"; }
trap cleanup EXIT

ok()   { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Build a minimal stub tree for ci-wait.sh: ci-status.sh and ci-decide.sh.
make_env() {
    local name=$1
    local root="$TMP_BASE/$name"
    mkdir -p "$root/scripts"
    cp "$REPO_ROOT/scripts/ci-wait.sh" "$root/scripts/ci-wait.sh"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    chmod +x "$root/scripts/ci-wait.sh"
    printf '%s\n' "$root"
}

write_ci_status_stub() {
    local root=$1
    # STUB_STATUSES is a colon-separated list of CI_STATUS values to return
    # sequentially. After the list is exhausted, return the last value.
    # Uses a call-count file under the root to track invocations.
    cat > "$root/scripts/ci-status.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
count_file="$(dirname "$0")/../.ci-status-count"
count=$(cat "$count_file" 2>/dev/null || echo 0)
count=$((count + 1))
printf '%s\n' "$count" > "$count_file"
IFS=: read -ra statuses <<< "${STUB_STATUSES:-pass}"
idx=$((count - 1))
[ "$idx" -ge "${#statuses[@]}" ] && idx=$(( ${#statuses[@]} - 1 ))
status="${statuses[$idx]}"

# Simulate a slow iteration if requested (STUB_SLOW_CALL_N=N; slowness = STUB_SLOW_SECS seconds)
slow_n="${STUB_SLOW_CALL_N:-0}"
slow_secs="${STUB_SLOW_SECS:-0}"
if [ "$slow_n" -gt 0 ] && [ "$count" -eq "$slow_n" ] && [ "$slow_secs" -gt 0 ]; then
    sleep "$slow_secs"
fi

printf 'CI_STATUS=%s\nBEHIND_COUNT=0\nFAILED_RUN_ID=\n' "$status"
SH
    chmod +x "$root/scripts/ci-status.sh"
}

write_ci_decide_stub() {
    local root=$1
    cat > "$root/scripts/ci-decide.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
# Read --status argument
while [[ $# -gt 0 ]]; do
    [[ "$1" == --status ]] && { CI_STATUS="$2"; shift 2; continue; }
    shift
done
CI_STATUS="${CI_STATUS:-pending}"
case "$CI_STATUS" in
    pass)   printf 'ACTION=merge\nBAIL_REASON=\n' ;;
    fail)   printf 'ACTION=bail\nBAIL_REASON=CI failed\n' ;;
    *)      printf 'ACTION=wait\nBAIL_REASON=\n' ;;
esac
SH
    chmod +x "$root/scripts/ci-decide.sh"
}

write_noop_sleep_stub() {
    local root=$1
    cat > "$root/scripts/fake-sleep.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
    chmod +x "$root/scripts/fake-sleep.sh"
    ln -sf "$root/scripts/fake-sleep.sh" "$root/scripts/sleep"
}

run_subject() {
    local root=$1 rc_file=$2
    shift 2
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" "$root/scripts/ci-wait.sh" --pr 1 --repo owner/repo "$@" > "$root/.stdout" 2>"$root/.stderr")
    local rc=$?
    set -e
    printf '%s' "$rc" > "$rc_file"
}

assert_stdout_contains() {
    local root=$1 pattern=$2 label=$3
    if grep -q "$pattern" "$root/.stdout"; then
        ok "$label"
    else
        fail "$label (pattern '$pattern' not found in stdout)"
        sed 's/^/    stdout: /' "$root/.stdout"
    fi
}

assert_stderr_contains() {
    local root=$1 pattern=$2 label=$3
    if grep -q "$pattern" "$root/.stderr"; then
        ok "$label"
    else
        fail "$label (pattern '$pattern' not found in stderr)"
        sed 's/^/    stderr: /' "$root/.stderr"
    fi
}

assert_rc() {
    local file=$1 expected=$2 label=$3 actual
    actual=$(cat "$file")
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

assert_stream_contains() {
    local file=$1 pattern=$2 label=$3
    if grep -q "$pattern" "$file"; then
        ok "$label"
    else
        fail "$label (pattern '$pattern' not found in stream)"
        sed 's/^/    stream: /' "$file"
    fi
}

assert_stderr_compact_matches() {
    local root=$1 pattern=$2 label=$3 actual
    actual=$(tr -d '\n' <"$root/.stderr")
    if [[ "$actual" =~ $pattern ]]; then
        ok "$label"
    else
        fail "$label (expected pattern [$pattern], got [$actual])"
    fi
}

# --- Case 1: happy path — ci-status returns pass on first call ---
root=$(make_env happy_path)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
STUB_STATUSES=pass run_subject "$root" "$root/.rc" --timeout 60
assert_rc "$root/.rc" 0 "happy path: exits 0"
assert_stdout_contains "$root" "ACTION=merge" "happy path: ACTION=merge"

# --- Case 2: pending-then-pass — 3x pending then pass ---
root=$(make_env pending_then_pass)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
# Override sleep to be instantaneous so the 3 pending polls don't take 30s real time
write_noop_sleep_stub "$root"
STUB_STATUSES=pending:pending:pending:pass run_subject "$root" "$root/.rc" --timeout 120
assert_rc "$root/.rc" 0 "pending-then-pass: exits 0"
assert_stdout_contains "$root" "ACTION=merge" "pending-then-pass: ACTION=merge"
assert_stderr_compact_matches "$root" '^⏳ CI: waiting\.\.\.✓ CI passed \([0-9]+s, 3 polls\)$' \
    "pending-then-pass: stderr progress format"
call_count=$(cat "$root/.ci-status-count" 2>/dev/null || echo 0)
if [[ "$call_count" -eq 4 ]]; then
    ok "pending-then-pass: exactly 4 ci-status calls"
else
    fail "pending-then-pass: expected 4 ci-status calls, got $call_count"
fi

# --- Case 3: suspend simulation — first iteration is slow but loop continues ---
# We use STUB_SLOW_CALL_N=1 STUB_SLOW_SECS=65 to make ci-status.sh sleep 65s on
# call 1, simulating a suspended laptop. The iter_delta check in ci-wait.sh
# should detect this and not count that iteration toward the budget.
# To keep tests fast we can't literally sleep 65s, so instead we override the
# 'date' command to return a large delta for the first post-sleep call.
root=$(make_env suspend_sim)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"

# Wrap 'date' to simulate a large elapsed time on the first iteration's post-sleep call.
# ci-wait.sh calls: date +%s (iter_start) then date +%s (iter_delta calc after sleep).
# We make the second date call return iter_start + 70 the first time around.
REAL_DATE=$(command -v date)
# After the iter_start/sleep/iter_delta fix, ci-wait.sh calls date twice per iteration:
# call 1: iter_start (just before sleep) → return current ts (save as base)
# call 2: after sleep, for delta → return base+70 (simulate 70s sleep = suspend)
# Subsequent calls return real ts so the loop proceeds normally.
cat > "$root/scripts/date" <<SH
#!/usr/bin/env bash
count_file="\$(dirname "\$0")/../.date-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s\\n' "\$count" > "\$count_file"
base_file="\$(dirname "\$0")/../.date-base"
real_ts=\$("$REAL_DATE" +%s)
if [ "\$count" -eq 1 ]; then
    printf '%s\\n' "\$real_ts" > "\$base_file"
    printf '%s\\n' "\$real_ts"
elif [ "\$count" -eq 2 ]; then
    base=\$(cat "\$base_file" 2>/dev/null || echo "\$real_ts")
    printf '%s\\n' "\$((base + 70))"
else
    printf '%s\\n' "\$real_ts"
fi
SH
chmod +x "$root/scripts/date"

# Override sleep to be instantaneous; the fake date stub already simulates 70s
# elapsed on the 2nd date call, so suspend detection fires without a real 10s wait.
cat > "$root/scripts/fake-sleep.sh" <<'SH'
#!/usr/bin/env bash
# no-op sleep stub
exit 0
SH
chmod +x "$root/scripts/fake-sleep.sh"
ln -sf "$root/scripts/fake-sleep.sh" "$root/scripts/sleep"

# Run with a short timeout and two status calls: pending (slow), then pass.
STUB_STATUSES=pending:pass run_subject "$root" "$root/.rc" --timeout 30
assert_rc "$root/.rc" 0 "suspend sim: exits 0 (slow iteration does not exhaust budget)"
assert_stdout_contains "$root" "ACTION=merge" "suspend sim: ACTION=merge after suspended iteration"
if grep -q "suspend detected" "$root/.stderr" 2>/dev/null; then
    ok "suspend sim: suspend detected warning emitted"
else
    fail "suspend sim: expected 'suspend detected' warning on stderr"
    sed 's/^/    stderr: /' "$root/.stderr"
fi

# --- Case 4: genuine timeout — always pending, timeout 30 → MAX_POLLS=3 ---
root=$(make_env genuine_timeout)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
# Override sleep to be instantaneous so test completes quickly
write_noop_sleep_stub "$root"

STUB_STATUSES=pending run_subject "$root" "$root/.rc" --timeout 30
assert_rc "$root/.rc" 0 "genuine timeout: exits 0"
assert_stdout_contains "$root" "ACTION=bail" "genuine timeout: ACTION=bail"
if grep -q "Poll budget" "$root/.stdout"; then
    ok "genuine timeout: BAIL_REASON contains Poll budget"
else
    fail "genuine timeout: expected BAIL_REASON containing Poll budget"
    sed 's/^/    stdout: /' "$root/.stdout"
fi
call_count=$(cat "$root/.ci-status-count" 2>/dev/null || echo 0)
# MAX_POLLS=30/10=3; each poll increments checks before the guard (checks starts at 0,
# becomes 1 after first iteration, ... bails when checks >= 3).
if [[ "$call_count" -le 4 ]]; then
    ok "genuine timeout: ci-status called at most 4 times (MAX_POLLS=3)"
else
    fail "genuine timeout: expected ≤4 ci-status calls, got $call_count"
fi

# --- Case 5: larch_errf progress appears on stderr ---
root=$(make_env breadcrumb_stderr)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
STUB_STATUSES=pass run_subject "$root" "$root/.rc" --timeout 60
assert_rc "$root/.rc" 0 "breadcrumb stderr: exits 0"
assert_stdout_contains "$root" "ACTION=merge" "breadcrumb stderr: ACTION=merge"
assert_stderr_compact_matches "$root" '^⏳ CI: waiting✓ CI passed \([0-9]+s, 0 polls\)$' \
    "breadcrumb stderr: immediate pass stays inline without stray newline"

# --- Case 6: inline dot progress on stderr across pending polls ---
root=$(make_env breadcrumb_stderr_pending_dots)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
write_noop_sleep_stub "$root"
STUB_STATUSES=pending:pending:pass run_subject "$root" "$root/.rc" --timeout 60
assert_rc "$root/.rc" 0 "breadcrumb dots: exits 0"
assert_stdout_contains "$root" "ACTION=merge" "breadcrumb dots: ACTION=merge"
assert_stderr_compact_matches "$root" '^⏳ CI: waiting\.\.✓ CI passed \([0-9]+s, 2 polls\)$' \
    "breadcrumb dots: pending dots stay inline until success banner"

# --- Case 7: timeout bail warning on stderr ---
root=$(make_env breadcrumb_stderr_timeout_bail)
write_ci_status_stub "$root"
write_ci_decide_stub "$root"
write_noop_sleep_stub "$root"
STUB_STATUSES=pending run_subject "$root" "$root/.rc" --timeout 20
assert_rc "$root/.rc" 0 "breadcrumb timeout bail: exits 0"
assert_stdout_contains "$root" "ACTION=bail" "breadcrumb timeout bail: ACTION=bail"
assert_stderr_contains "$root" "⚠ CI wait timed out after 2 polls" "breadcrumb timeout bail: timeout warning on stderr"

if [[ "$FAIL_COUNT" -ne 0 ]]; then
    echo "test-ci-wait: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-ci-wait: $PASS_COUNT pass(es)"
