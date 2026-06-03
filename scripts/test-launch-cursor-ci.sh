#!/usr/bin/env bash
# test-launch-cursor-ci.sh — argv contract tests for launch-cursor-ci.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-cursor-ci-test.XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR_BASE/execution-issues.md"
export IMPLEMENT_TMPDIR="$TMPDIR_BASE"
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

: >"$TMPDIR_BASE/failure-log-fixture.log"
assert_fails "rejects_failure_log_outside_implement_tmpdir" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log /etc/passwd
assert_fails "rejects_relative_failure_log" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log relative-only.log
assert_fails "rejects_missing_failure_log_file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log "$TMPDIR_BASE/no-such-failure.log"

if grep -q -- '--conflict-files' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --conflict-files"; else fail "script supports --conflict-files"; fi
if grep -q '<<<CONFLICT_PATHS>>>' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "resolve-conflict prompt fences conflict paths"; else fail "resolve-conflict prompt fences conflict paths"; fi
if grep -q -- "--task-kind \"\$TIMING_TASK_KIND\"" "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "uses timing task kind"; else fail "uses timing task kind"; fi
if grep -q 'plan-file' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --plan-file"; else fail "script supports --plan-file"; fi
if grep -q -- '--failure-log' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --failure-log"; else fail "script supports --failure-log"; fi
if grep -q 'Local reproduction invariant' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "fix role prompt carries local reproduction invariant"; else fail "fix role prompt carries local reproduction invariant"; fi
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

kill_stall_sidecar_wrapper_if_alive() {
    local sc_path=$1
    command -v jq >/dev/null 2>&1 || return 0
    [[ -f "$sc_path" ]] || return 0
    local wp
    wp=$(jq -r '.pid // empty' "$sc_path" 2>/dev/null || true)
    [[ -n "$wp" ]] || return 0
    if kill -0 "$wp" 2>/dev/null; then
        kill -KILL "$wp" 2>/dev/null || true
    fi
}

assert_stall_sidecar_stable_contract() {
    local f=$1 label=$2
    if jq -e '
        (.channel|type=="string")
        and (.pid|type=="number")
        and (.time_since_last_progress|type=="number")
        and (.time_since_last_progress >= 3)
        and (.capture_phase == "post_sigterm")
        and (.transcript_tail_capture_phase|type=="string")
        and (.diag_capture_note|type=="string")
        and (.ps|type=="string")
        and ((.ps|contains("stall ps snapshot")) or (.ps|contains("omitted:")) or (.ps|length > 30))
        and (.lsof|type=="string")
        and (.git_state|type=="object")
        and (.git_state.status_porcelain|type=="string")
        and (.git_state.rebase_patch_excerpt|type=="string")
        and (.transcript_tail_contract|type=="string")
        and (.last_transcript_lines|type=="array")
    ' "$f" >/dev/null 2>&1; then
        ok "$label stall sidecar stable contract"
    else
        fail "$label stall sidecar stable contract"
    fi
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
    # Wall-clock assertion widened to <30s — under heavy parallel test load,
    # fork/exec and child-reaping latency can stretch the post-stall-kill cleanup
    # noticeably. The launcher's own stall-detect fires at LARCH_CURSOR_CI_STALL_THRESHOLD,
    # so <30s still catches regressions where stall-detect doesn't fire at all.
    if [[ $((end2 - start2)) -lt 30 ]]; then ok "stall fixture 2 elapsed <30s"; else fail "stall fixture 2 elapsed <30s ($((end2 - start2)))"; fi

    # --- Stall fixture 3: tree channel (resolve-conflict) ---
    MINIGIT="$TMPDIR_BASE/minigit"
    mkdir -p "$MINIGIT"
    git -C "$MINIGIT" -c user.email=t@e -c user.name=t init
    # Repeat identity on commit: `git init`'s -c flags do not persist, and CI
    # runners often have no global user.name/user.email (fixture 3 regression).
    git -C "$MINIGIT" -c user.email=t@e -c user.name=t commit --allow-empty -m init
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
    if [[ $((end3 - start3)) -lt 40 ]]; then ok "stall fixture 3 elapsed <40s"; else fail "stall fixture 3 elapsed <40s ($((end3 - start3)))"; fi

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
    if [[ $((end5 - start5)) -lt 30 ]]; then ok "stall fixture 5 elapsed <30s"; else fail "stall fixture 5 elapsed <30s ($((end5 - start5)))"; fi
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

    # --- Stall fixtures 7–8: JSON sidecar (jq-dependent assertions; skip when jq absent) ---
    if [[ -n "${GITHUB_ACTIONS:-}" || "${CI:-}" == true ]] && ! command -v jq >/dev/null 2>&1; then
        echo "test-launch-cursor-ci: jq is required in CI for stall JSON regression coverage" >&2
        exit 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        ok "stall fixtures 7–8 skipped (jq not installed; stall JSON sidecars require jq — CI must provide jq; see scripts/launch-cursor-ci.md Harness)"
    else
        # --- Stall fixture 7: JSON sidecar under IMPLEMENT_TMPDIR/round-1 ---
        STUB7="$TMPDIR_BASE/stub7"
        write_cursor_stub_sleep "$STUB7"
        OUT7="$TMPDIR_BASE/out7.json"
        CAP7="$TMPDIR_BASE/cap7.txt"
        IMPL7="$TMPDIR_BASE/impl7"
        mkdir -p "$IMPL7/round-1"
        stall_env
        export IMPLEMENT_TMPDIR="$IMPL7"
        set +e
        ( cd "$REPO_ROOT" && PATH="$STUB7:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
            --role fix --output "$OUT7" --run-id s7 --repo owner/repo --timeout 1800 ) >"$CAP7" 2>&1
        set -e
        unset IMPLEMENT_TMPDIR
        shopt -s nullglob
        sidecars=( "$IMPL7/round-1"/cursor-ci-stall-*.json )
        shopt -u nullglob
        if [[ ${#sidecars[@]} -ge 1 ]]; then ok "stall fixture 7 sidecar json emitted"; else fail "stall fixture 7 sidecar missing"; fi
        sc0="${sidecars[0]}"
        ch7=$(jq -r '.channel' "$sc0" 2>/dev/null || echo "")
        ps_nonempty=$(jq -r '.ps' "$sc0" 2>/dev/null | wc -c | tr -d ' ')
        if [[ "$ch7" == "stdout" ]]; then ok "stall fixture 7 channel stdout"; else fail "stall fixture 7 channel (got $ch7)"; fi
        if [[ "${ps_nonempty:-0}" -gt 20 ]]; then ok "stall fixture 7 ps payload"; else fail "stall fixture 7 ps too small ($ps_nonempty)"; fi
        if ! jq -e '.git_state | type == "object" and (.status_porcelain | type == "string") and (.rebase_patch_excerpt | type == "string")' "$sc0" >/dev/null 2>&1; then fail "stall fixture 7 git_state shape"; else ok "stall fixture 7 git_state shape"; fi
        if command -v lsof >/dev/null 2>&1 && { command -v timeout >/dev/null 2>&1 || command -v gtimeout >/dev/null 2>&1; }; then
            self_lsof_c=0
            if command -v timeout >/dev/null 2>&1; then
                self_lsof_c=$(timeout 2 lsof -nP -p $$ 2>/dev/null | wc -c | tr -d ' ')
            else
                self_lsof_c=$(gtimeout 2 lsof -nP -p $$ 2>/dev/null | wc -c | tr -d ' ')
            fi
            if [[ "${self_lsof_c:-0}" -lt 30 ]]; then
                ok "stall fixture 7 lsof skipped (self-probe inconclusive)"
            else
                lz=$(jq -r '.lsof // empty' "$sc0" 2>/dev/null | wc -c | tr -d ' ')
                if [[ "${lz:-0}" -gt 10 ]]; then ok "stall fixture 7 lsof captured"; else fail "stall fixture 7 lsof empty despite working lsof ($lz)"; fi
            fi
        else
            ok "stall fixture 7 lsof skipped (lsof or timeout/gtimeout unavailable)"
        fi
        ttph=$(jq -r '.transcript_tail_capture_phase // empty' "$sc0" 2>/dev/null || echo "")
        if [[ "$ttph" == "pre_sigterm" ]]; then ok "stall fixture 7 transcript_tail_capture_phase pre_sigterm"; else fail "stall fixture 7 transcript_tail_capture_phase (got $ttph)"; fi
        lt_lines=$(jq '.last_transcript_lines | length' "$sc0" 2>/dev/null || echo 0)
        if [[ "${lt_lines:-0}" -ge 1 ]]; then ok "stall fixture 7 last_transcript_lines"; else fail "stall fixture 7 last_transcript_lines empty"; fi
        cp7=$(jq -r '.capture_phase // empty' "$sc0" 2>/dev/null || echo "")
        if [[ "$cp7" == "post_sigterm" ]]; then ok "stall fixture 7 capture_phase post_sigterm"; else fail "stall fixture 7 capture_phase (got $cp7)"; fi
        assert_stall_sidecar_stable_contract "$sc0" "stall fixture 7"
        kill_stall_sidecar_wrapper_if_alive "$sc0"

        # --- Stall fixture 8: tree channel sidecar path + channel prefix ---
        MINIGIT8="$TMPDIR_BASE/minigit8"
        mkdir -p "$MINIGIT8"
        git -C "$MINIGIT8" -c user.email=t@e -c user.name=t init
        git -C "$MINIGIT8" -c user.email=t@e -c user.name=t commit --allow-empty -m init
        STUB8="$TMPDIR_BASE/stub8"
        write_cursor_stub_sleep "$STUB8"
        IMPL8="$TMPDIR_BASE/impl8"
        mkdir -p "$IMPL8/round-1"
        OUT8="$IMPL8/round-1/out8.json"
        CAP8="$TMPDIR_BASE/cap8.txt"
        stall_env
        export IMPLEMENT_TMPDIR="$IMPL8"
        set +e
        start8=$(date +%s)
        ( cd "$MINIGIT8" && PATH="$STUB8:$PATH" bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
            --role resolve-conflict --output "$OUT8" --run-id s8 --repo owner/repo --timeout 1800 ) >"$CAP8" 2>&1
        set -e
        end8=$(date +%s)
        unset IMPLEMENT_TMPDIR
        shopt -s nullglob
        sidecars8=( "$IMPL8/round-1"/cursor-ci-stall-*.json )
        shopt -u nullglob
        if [[ ${#sidecars8[@]} -ge 1 ]]; then ok "stall fixture 8 tree sidecar under round-1"; else fail "stall fixture 8 tree sidecar missing"; fi
        sc8="${sidecars8[0]}"
        ch8=$(jq -r '.channel' "$sc8" 2>/dev/null || echo "")
        case "$ch8" in tree:*) ok "stall fixture 8 channel tree prefix"; ;; *) fail "stall fixture 8 channel (got $ch8)"; ;; esac
        if [[ $((end8 - start8)) -lt 25 ]]; then ok "stall fixture 8 elapsed <25s"; else fail "stall fixture 8 elapsed <25s ($((end8 - start8)))"; fi
        assert_stall_sidecar_stable_contract "$sc8" "stall fixture 8"
        kill_stall_sidecar_wrapper_if_alive "$sc8"
    fi
fi

# CI-fix pattern fragment: fix role includes topology.tsv sentinel; non-fix roles omit it.
stub_bin="$TMPDIR_BASE/ci-fix-stub-bin"
mkdir -p "$stub_bin"
cat > "$stub_bin/cursor" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_bin/cursor"
OUT_FIX="$TMPDIR_BASE/ci-fix-prompt-fix"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" --role fix --output "$OUT_FIX" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_FIX}.prompt" 2>/dev/null; then
    ok "fix role prompt includes topology.tsv sentinel"
else
    fail "fix role prompt includes topology.tsv sentinel"
fi
role=resolve-conflict
OUT_NF="$TMPDIR_BASE/ci-fix-prompt-$role"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-cursor-ci.sh" --role "$role" --output "$OUT_NF" --run-id r1 --repo owner/repo \
    --conflict-files README.md --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_NF}.prompt" 2>/dev/null; then
    fail "non-fix role $role must not include topology.tsv"
else
    ok "non-fix role $role omits topology.tsv"
fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-cursor-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-cursor-ci: $PASS pass(es)"
