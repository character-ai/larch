#!/usr/bin/env bash
# test-launch-cursor-ci.sh — argv contract tests for launch-cursor-ci.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-cursor-ci-test.XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR_BASE/execution-issues.md"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

PASS=0
FAIL=0
ok() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

assert_fails() {
    local label=$1
    shift
    set +e
    "$REPO_ROOT/scripts/launch-cursor-ci.sh" "$@" > "$TMPDIR_BASE/out" 2> "$TMPDIR_BASE/err"
    local rc=$?
    set -e
    if [[ "$rc" == 2 ]]; then ok "$label"; else fail "$label"; cat "$TMPDIR_BASE/err"; fi
}

assert_fails "rejects bad role" --role nope --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo
assert_fails "rejects relative output" --role fix --output relative --run-id 1 --repo owner/repo
assert_fails "rejects unsafe output characters" --role fix --output "$TMPDIR_BASE/out with space" --run-id 1 --repo owner/repo
assert_fails "rejects relative --plan-file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --plan-file relative/plan.txt
assert_fails "rejects conflict-files with .." --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files '../etc/passwd'
assert_fails "rejects conflict-files with invalid characters" --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files 'foo bar'

if grep -q -- '--conflict-files' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --conflict-files"; else fail "script supports --conflict-files"; fi
if grep -q '<<<CONFLICT_PATHS>>>' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "resolve-conflict prompt fences conflict paths"; else fail "resolve-conflict prompt fences conflict paths"; fi
if grep -q -- "--task-kind \"\$TIMING_TASK_KIND\"" "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "uses timing task kind"; else fail "uses timing task kind"; fi
if grep -q 'plan-file' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --plan-file"; else fail "script supports --plan-file"; fi
if grep -q 'cursor-ci-fix' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then ok "timing allow-list includes cursor-ci-fix"; else fail "timing allow-list includes cursor-ci-fix"; fi

cat > "$TMPDIR_BASE/token-record" <<'EOF'
TOOL=cursor
INPUT=1
OUTPUT=2
CACHE_READ=3
CACHE_CREATE=4
TOTAL=10
RAW=cursor_ci_fix
EOF
"$REPO_ROOT/scripts/append-token-record.sh" --input "$TMPDIR_BASE/token-record" --tmpdir "$TMPDIR_BASE"
if grep -q '"tool":"cursor"' "$TMPDIR_BASE/token-report.ndjson"; then ok "append-token-record normalizes cursor sidecar"; else fail "append-token-record normalizes cursor sidecar"; fi

stall_env() {
    export CURSOR_API_KEY=test_key
    export LARCH_LIB_CURSOR_AUTH_TEST_MODE=1
    export LARCH_CURSOR_CI_STALL_THRESHOLD=3
    export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.5
    export LARCH_EXTERNAL_AUTH_RETRIES=1
}

launcher_exit_from_capture() {
    grep '^LAUNCHER_EXIT=' "$1" | tail -1 | cut -d= -f2-
}

write_cursor_stub_sleep() {
    local stub_dir=$1
    mkdir -p "$stub_dir"
    cat >"$stub_dir/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == agent ]]; then
    exec sleep 300
fi
exit 127
EOF
    chmod +x "$stub_dir/cursor"
}

write_cursor_stub_byte_then_sleep() {
    local stub_dir=$1
    mkdir -p "$stub_dir"
    cat >"$stub_dir/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == agent ]]; then
    exec python3 -u -c 'import sys,time; sys.stdout.write("x"); sys.stdout.flush(); time.sleep(300)'
fi
exit 127
EOF
    chmod +x "$stub_dir/cursor"
}

write_cursor_stub_progress_loop_ok() {
    local stub_dir=$1
    mkdir -p "$stub_dir"
    cat >"$stub_dir/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == agent ]]; then
    exec python3 -u -c 'import sys,time
for _ in range(6):
    sys.stdout.write("x")
    sys.stdout.flush()
    time.sleep(1)
sys.exit(0)
'
fi
exit 127
EOF
    chmod +x "$stub_dir/cursor"
}

write_cursor_stub_infinite_bytes() {
    local stub_dir=$1
    mkdir -p "$stub_dir"
    cat >"$stub_dir/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == agent ]]; then
    exec python3 -u -c 'import sys,time
while True:
    sys.stdout.write("x")
    sys.stdout.flush()
    time.sleep(0.5)
'
fi
exit 127
EOF
    chmod +x "$stub_dir/cursor"
}

if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 required for stall-detection fixtures"
else
    # --- Stall fixture 1: stdout role, zero-byte stall ---
    STUB1="$TMPDIR_BASE/stub1"
    write_cursor_stub_sleep "$STUB1"
    OUT1="$TMPDIR_BASE/out1.json"
    CAP1="$TMPDIR_BASE/cap1.txt"
    stall_env
    set +e
    start1=$(date +%s)
    ( cd "$REPO_ROOT" && PATH="$STUB1:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role fix --output "$OUT1" --run-id s1 --repo owner/repo --timeout 1800 ) >"$CAP1" 2>&1
    rc_wrap=$?
    set -e
    end1=$(date +%s)
    le1=$(launcher_exit_from_capture "$CAP1" || echo missing)
    if [[ "$rc_wrap" -eq 0 ]]; then ok "stall fixture 1 wrapper exit 0"; else fail "stall fixture 1 wrapper exit 0 (got $rc_wrap)"; fi
    if [[ "$le1" != 0 && "$le1" != "missing" ]]; then ok "stall fixture 1 LAUNCHER_EXIT non-zero ($le1)"; else fail "stall fixture 1 LAUNCHER_EXIT non-zero (got $le1)"; fi
    if [[ -f "${OUT1}.diag" ]] && grep -q 'Stall detected' "${OUT1}.diag"; then ok "stall fixture 1 diag Stall detected"; else fail "stall fixture 1 diag Stall detected"; fi
    if [[ $((end1 - start1)) -lt 20 ]]; then ok "stall fixture 1 elapsed <20s"; else fail "stall fixture 1 elapsed <20s ($((end1 - start1)))"; fi

    # --- Stall fixture 2: progress then stall ---
    STUB2="$TMPDIR_BASE/stub2"
    write_cursor_stub_byte_then_sleep "$STUB2"
    OUT2="$TMPDIR_BASE/out2.json"
    CAP2="$TMPDIR_BASE/cap2.txt"
    stall_env
    set +e
    start2=$(date +%s)
    ( cd "$REPO_ROOT" && PATH="$STUB2:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role fix --output "$OUT2" --run-id s2 --repo owner/repo --timeout 1800 ) >"$CAP2" 2>&1
    set -e
    end2=$(date +%s)
    le2=$(launcher_exit_from_capture "$CAP2" || echo missing)
    if [[ "$le2" != 0 && "$le2" != "missing" ]]; then ok "stall fixture 2 LAUNCHER_EXIT non-zero"; else fail "stall fixture 2 LAUNCHER_EXIT non-zero (got $le2)"; fi
    if grep -q 'Stall detected' "${OUT2}.diag"; then ok "stall fixture 2 diag Stall detected"; else fail "stall fixture 2 diag Stall detected"; fi
    if [[ $((end2 - start2)) -lt 15 ]]; then ok "stall fixture 2 elapsed <15s"; else fail "stall fixture 2 elapsed <15s ($((end2 - start2)))"; fi

    # --- Stall fixture 3: tree channel (resolve-conflict) ---
    MINIGIT="$TMPDIR_BASE/minigit"
    mkdir -p "$MINIGIT"
    git -C "$MINIGIT" -c user.email=t@e -c user.name=t init
    git -C "$MINIGIT" commit --allow-empty -m init
    STUB3="$TMPDIR_BASE/stub3"
    write_cursor_stub_sleep "$STUB3"
    OUT3="$TMPDIR_BASE/out3.json"
    CAP3="$TMPDIR_BASE/cap3.txt"
    stall_env
    set +e
    start3=$(date +%s)
    ( cd "$MINIGIT" && PATH="$STUB3:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role resolve-conflict --output "$OUT3" --run-id s3 --repo owner/repo --timeout 1800 ) >"$CAP3" 2>&1
    set -e
    end3=$(date +%s)
    le3=$(launcher_exit_from_capture "$CAP3" || echo missing)
    if [[ "$le3" != 0 && "$le3" != "missing" ]]; then ok "stall fixture 3 LAUNCHER_EXIT non-zero"; else fail "stall fixture 3 LAUNCHER_EXIT non-zero (got $le3)"; fi
    if grep -q 'Stall detected' "${OUT3}.diag"; then ok "stall fixture 3 diag Stall detected"; else fail "stall fixture 3 diag Stall detected"; fi
    if [[ $((end3 - start3)) -lt 20 ]]; then ok "stall fixture 3 elapsed <20s"; else fail "stall fixture 3 elapsed <20s ($((end3 - start3)))"; fi

    # --- Stall fixture 4: steady progress, no stall kill ---
    STUB4="$TMPDIR_BASE/stub4"
    write_cursor_stub_progress_loop_ok "$STUB4"
    OUT4="$TMPDIR_BASE/out4.json"
    CAP4="$TMPDIR_BASE/cap4.txt"
    stall_env
    set +e
    ( cd "$REPO_ROOT" && PATH="$STUB4:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role fix --output "$OUT4" --run-id s4 --repo owner/repo --timeout 1800 ) >"$CAP4" 2>&1
    set -e
    le4=$(launcher_exit_from_capture "$CAP4" || echo missing)
    if [[ "$le4" == 0 ]]; then ok "stall fixture 4 LAUNCHER_EXIT 0"; else fail "stall fixture 4 LAUNCHER_EXIT 0 (got $le4)"; fi
    if grep -q 'Stall detected' "${OUT4}.diag" 2>/dev/null; then fail "stall fixture 4 must not stall"; else ok "stall fixture 4 no Stall detected in diag"; fi

    # --- Stall fixture 5: wall-clock timeout wins (not stall-killed) ---
    # Use a large stall budget here: tiny stdout writes through bash's redirect
    # can lag on-disk size growth enough to false-trigger a 3s stall window
    # before run-external-agent's wall-clock timeout on runners without stdbuf(1)
    # (typical macOS). Other fixtures keep LARCH_CURSOR_CI_STALL_THRESHOLD=3.
    STUB5="$TMPDIR_BASE/stub5"
    write_cursor_stub_infinite_bytes "$STUB5"
    OUT5="$TMPDIR_BASE/out5.json"
    CAP5="$TMPDIR_BASE/cap5.txt"
    stall_env
    export LARCH_CURSOR_CI_STALL_THRESHOLD=300
    set +e
    start5=$(date +%s)
    ( cd "$REPO_ROOT" && PATH="$STUB5:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role fix --output "$OUT5" --run-id s5 --repo owner/repo --timeout 5 ) >"$CAP5" 2>&1
    set -e
    end5=$(date +%s)
    le5=$(launcher_exit_from_capture "$CAP5" || echo missing)
    if [[ "$le5" == 124 ]]; then ok "stall fixture 5 LAUNCHER_EXIT 124"; else fail "stall fixture 5 LAUNCHER_EXIT 124 (got $le5)"; fi
    if [[ $((end5 - start5)) -lt 15 ]]; then ok "stall fixture 5 elapsed <15s"; else fail "stall fixture 5 elapsed <15s ($((end5 - start5)))"; fi
    if grep -q 'Stall detected' "${OUT5}.diag" 2>/dev/null; then fail "stall fixture 5 should not be stall-killed"; else ok "stall fixture 5 no stall kill"; fi
    unset LARCH_CURSOR_CI_STALL_THRESHOLD

    # --- Stall fixture 6: diagnostic shape + execution-issues ---
    STUB6="$TMPDIR_BASE/stub6"
    write_cursor_stub_sleep "$STUB6"
    OUT6="$TMPDIR_BASE/out6.json"
    CAP6="$TMPDIR_BASE/cap6.txt"
    IMPL6="$TMPDIR_BASE/impl6"
    mkdir -p "$IMPL6"
    stall_env
    export IMPLEMENT_TMPDIR="$IMPL6"
    set +e
    ( cd "$REPO_ROOT" && PATH="$STUB6:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
        --role fix --output "$OUT6" --run-id s6 --repo owner/repo --timeout 1800 ) >"$CAP6" 2>&1
    set -e
    unset IMPLEMENT_TMPDIR
    if grep -q 'channel=stdout' "${OUT6}.diag"; then ok "stall fixture 6 channel=stdout"; else fail "stall fixture 6 channel=stdout"; fi
    if grep -q 'time_since_last_progress=' "${OUT6}.diag"; then ok "stall fixture 6 time_since_last_progress"; else fail "stall fixture 6 time_since_last_progress"; fi
    if [[ -f "$IMPL6/execution-issues.md" ]] && grep -q 'cursor-ci' "$IMPL6/execution-issues.md"; then ok "stall fixture 6 execution-issues cursor-ci"; else fail "stall fixture 6 execution-issues cursor-ci"; fi
fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-cursor-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-cursor-ci: $PASS pass(es)"
