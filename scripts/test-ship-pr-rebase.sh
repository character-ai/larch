#!/usr/bin/env bash
# Offline regression for ship-pr.sh CI-fix rebase path (Phase 1 #3364).
# Structural pins plus a sandbox guard for ship-pr-rrr-phase14 resume handoff.
# shellcheck disable=SC2016
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SHIP_PR="$REPO_ROOT/scripts/ship-pr.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -f "$SHIP_PR" ]] || fail "scripts/ship-pr.sh missing: $SHIP_PR"

# ---------------------------------------------------------------------------
# (A) ci-behind-count → run_rebase_rebump defer-push before CI-fix push.
# ---------------------------------------------------------------------------
grep -Fq 'run_rebase_rebump "$phase" defer-push' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must call run_rebase_rebump with defer-push when behind main"
grep -Fq 'ci-behind-count.sh' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must consult ci-behind-count.sh before defer-rebase"
grep -Fq 'if [ "$behind" -gt 0 ]; then' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must defer-rebase only when BEHIND_COUNT > 0 (concurrency acceptance pin)"

# ---------------------------------------------------------------------------
# (B) run_rebase_rebump uses rebase-push --no-push --keep-on-conflict.
# ---------------------------------------------------------------------------
grep -Fq 'rebase-push.sh" --no-push --keep-on-conflict' "$SHIP_PR" \
    || fail "(B) run_rebase_rebump must invoke rebase-push.sh --no-push --keep-on-conflict"

# ---------------------------------------------------------------------------
# (C) Phase 1–4 handoff tokens for non-bump CI-fix conflicts.
# ---------------------------------------------------------------------------
grep -Fq 'RESUME_PHASE ship-pr-rrr-phase14' "$SHIP_PR" \
    || fail "(C) missing RESUME_PHASE ship-pr-rrr-phase14 state_set"
grep -Fq 'CALLER_KIND ship_pr_pre_push' "$SHIP_PR" \
    || fail "(C) missing CALLER_KIND ship_pr_pre_push state_set"
grep -Fq 'emit_kv CONFLICT_FILES' "$SHIP_PR" \
    || fail "(C) missing CONFLICT_FILES emit_kv on conflict stall"
grep -Fq 'ship-pr-rrr-after-phase14.flag' "$SHIP_PR" \
    || fail "(C) missing ship-pr-rrr-after-phase14.flag handoff token"

# ---------------------------------------------------------------------------
# (D) Phase 1: no per-PR bump drop/rebump inside ship-pr.sh.
# ---------------------------------------------------------------------------
grep -Fq 'release classify-bump' "$SHIP_PR" \
    && fail "(D) ship-pr.sh must not invoke release classify-bump after Phase 1"

# ---------------------------------------------------------------------------
# (D1) Lint-fix main-agent handoffs and malformed CI job tokens fail safely.
# ---------------------------------------------------------------------------
grep -Fq 'exit_ship_pr_internal_lint_fix_handoff' "$SHIP_PR" \
    || fail "(D1) ship-pr.sh must centralize ship-pr-internal lint-fix handoffs"
grep -Fq 'SHIP_PR_LEDGER_TRIGGER=%s\n' "$SHIP_PR" \
    || fail "(D1) ship-pr.sh must emit ledger-ready trigger fields"
unknown_suffix_count=$(grep -Fc '[ -n "$sanitized" ] || sanitized=unknown' "$SHIP_PR")
[[ "$unknown_suffix_count" -ge 2 ]] \
    || fail "(D1) ci-local-unfixable aggregate suffix must default to unknown when sanitization empties it"

# ---------------------------------------------------------------------------
# (D2) Fork carve-out in implement-finalize postbump branch validation.
# ---------------------------------------------------------------------------
FINALIZE="$REPO_ROOT/scripts/implement-finalize.sh"
grep -Fq 'FORKED_TARGET' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must reference FORKED_TARGET in postbump branch guard"
grep -Fq 'main|master)' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must guard main/master branch names"
grep -Fq 'forked' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must include forked-target carve-out for main/master"

# ---------------------------------------------------------------------------
# (E) Runtime: --resume-phase ship-pr-rrr-phase14 requires handoff flag.
# ---------------------------------------------------------------------------
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-ship-pr-rebase.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

write_ci_state() {
    local path=$1 phase=$2
    cat >"$path" <<EOF
PHASE=$phase
BRANCH_NAME=feature/test-ship-pr-rebase
ISSUE_NUMBER=3364
RUN_ID=test-ship-pr-rebase
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
MERGE=true
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=true
STALL_STEP=10
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
BAIL_FAILURE_DETAIL_LOG=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=99
PR_URL=https://github.example/pr/99
PR_TITLE=Test PR
RESUME_PHASE=
CALLER_KIND=
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test_
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$TMPROOT
CI_FIX_REBASE_PENDING=false
EOF
}

assert_ship_pr_lint_handoff_case() {
    local case_name=$1 phase=$2 dispatch_first=$3 ledger_mode=$4 expected_detail=$5
    local case_dir="$TMPROOT/lint-handoff-$case_name"
    local impl="$case_dir/impl"
    local state_file="$case_dir/ship-pr-state.sh"
    local out rc expected_path
    mkdir -p "$impl"
    write_ci_state "$state_file" "$phase"
    printf 'initial redacted log\n' > "$impl/initial.redacted.log"
    printf 'captured failure\n' > "$impl/captured.log"
    printf 'ledger detail\n' > "$impl/ledger-detail.log"
    printf 'outside detail\n' > "$case_dir/outside-detail.log"

    set +e
    out=$(
        CASE_DIR="$case_dir" CASE_IMPL="$impl" CASE_STATE="$state_file" CASE_PHASE="$phase" \
            CASE_DISPATCH_FIRST="$dispatch_first" CASE_LEDGER_MODE="$ledger_mode" \
            CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash <<'EOS'
set -uo pipefail
# shellcheck source=scripts/ship-pr.sh
source "$CLAUDE_PLUGIN_ROOT/scripts/ship-pr.sh"
SCRIPT_DIR="$CLAUDE_PLUGIN_ROOT/scripts"
PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
IMPLEMENT_TMPDIR="$CASE_IMPL"
STATE_FILE="$CASE_STATE"
_RCC_PHASE="$CASE_PHASE"
_RCC_RERUN_FN=case_rerun
_RCC_SITE=ship-pr-ci-initial
_RCC_TARGET_CMD_ARGS_FILE=""
_RCC_MAX_ITER=3
_RCC_DISPATCH_FIRST="$CASE_DISPATCH_FIRST"
_RCC_INITIAL_REDACTED_LOG="$IMPLEMENT_TMPDIR/initial.redacted.log"

python3() { cat; }
larch_err() { return 0; }
failure_capture_path() {
    local phase=${1:-unknown}
    printf '%s/failure-%s.log\n' "$IMPLEMENT_TMPDIR" "$phase"
}
case_rerun() {
    _RCC_RAW_LOG_PATH="$IMPLEMENT_TMPDIR/captured.log"
    _RCC_CMD_RC=1
}
run_lint_fix_loop_capture() {
    local fail_file=$1 site=$2 redacted_log=$3 out_var=$4 rc_var=$5
    local output
    printf 'lint handoff site=%s log=%s\n' "$site" "$redacted_log" >> "$fail_file"
    output='LINT_FIX_STATUS=main-agent-required'
    if [ "$CASE_LEDGER_MODE" = inside ]; then
        output="${output}"$'\n'"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG=$IMPLEMENT_TMPDIR/ledger-detail.log"
    elif [ "$CASE_LEDGER_MODE" = outside ]; then
        output="${output}"$'\n'"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG=$CASE_DIR/outside-detail.log"
    elif [ "$CASE_LEDGER_MODE" != missing ]; then
        exit 98
    fi
    printf -v "$out_var" '%s' "$output"
    printf -v "$rc_var" '%s' 0
}

run_captured_cmd_then_fix_loop
if [ "$_RCC_STATUS" = main-agent-required ]; then
    detail_log=$(rcc_main_agent_required_detail_log)
    emit_ship_pr_ledger_ready ship-pr-internal-lint-fix "$CASE_PHASE" "$detail_log"
    exit_ship_pr_internal_lint_fix_handoff "$CASE_PHASE" "$detail_log"
fi
exit 97
EOS
    )
    rc=$?
    set -e

    [[ "$rc" -eq 3 ]] || fail "(D1-runtime $case_name) expected exit 3, got $rc; out=$out"
    grep -Fq 'SHIP_PR_LEDGER_READY=true' <<<"$out" || fail "(D1-runtime $case_name) missing ledger-ready"
    grep -Fq 'SHIP_PR_LEDGER_SITE=ship-pr-internal' <<<"$out" || fail "(D1-runtime $case_name) missing ledger site"
    grep -Fq 'SHIP_PR_LEDGER_TRIGGER=ship-pr-internal-lint-fix' <<<"$out" || fail "(D1-runtime $case_name) missing ledger trigger"
    grep -Fq 'SHIP_PR_LEDGER_STEP=8' <<<"$out" || fail "(D1-runtime $case_name) missing ledger step"
    grep -Fq "SHIP_PR_LEDGER_PHASE=$phase" <<<"$out" || fail "(D1-runtime $case_name) missing ledger phase"
    grep -Fq 'SHIP_PR_LEDGER_DISPATCHER=ship-pr' <<<"$out" || fail "(D1-runtime $case_name) missing ledger dispatcher"
    grep -Fq 'SHIP_PR_LEDGER_EXIT_CODE=3' <<<"$out" || fail "(D1-runtime $case_name) missing ledger exit code"

    expected_path=""
    case "$expected_detail" in
        ledger) expected_path="$impl/ledger-detail.log" ;;
        fallback) expected_path="$impl/failure-$phase.log" ;;
        none) expected_path="" ;;
        *) fail "(D1-runtime $case_name) unknown expected detail $expected_detail" ;;
    esac
    if [[ -n "$expected_path" ]]; then
        grep -Fq "SHIP_PR_LEDGER_FAILURE_DETAIL_LOG=$expected_path" <<<"$out" \
            || fail "(D1-runtime $case_name) missing expected detail log $expected_path in stdout: $out"
        grep -Fq "BAIL_FAILURE_DETAIL_LOG=$expected_path" "$state_file" \
            || fail "(D1-runtime $case_name) state missing expected detail log $expected_path"
    else
        ! grep -Fq 'SHIP_PR_LEDGER_FAILURE_DETAIL_LOG=' <<<"$out" \
            || fail "(D1-runtime $case_name) outside detail log must not be exported"
        grep -Fxq 'BAIL_FAILURE_DETAIL_LOG=' "$state_file" \
            || fail "(D1-runtime $case_name) state must clear outside detail log"
    fi
    grep -Fq 'BAIL_REASON=ship-pr-internal-lint-fix' "$state_file" \
        || fail "(D1-runtime $case_name) state missing bail reason"
    grep -Fq 'STALL_TRACKING=false' "$state_file" \
        || fail "(D1-runtime $case_name) state missing stall tracking false"
    grep -Fq 'EXIT_CODE=3' "$state_file" \
        || fail "(D1-runtime $case_name) state missing exit code"
}

assert_ship_pr_lint_handoff_case check-first ci-initial 0 inside ledger
assert_ship_pr_lint_handoff_case dispatch-first ci-merge 1 missing fallback
assert_ship_pr_lint_handoff_case outside-detail ci-initial 0 outside none

state="$TMPROOT/ship-pr-state.sh"
write_ci_state "$state" ci-initial

set +e
out=$(
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$SHIP_PR" \
        --state-file "$state" \
        --implement-tmpdir "$TMPROOT" \
        --merge true \
        --draft false \
        --forked false \
        --repo owner/repo \
        --no-admin-fallback true \
        --no-logs-commit true \
        --resume-phase ship-pr-rrr-phase14 \
        2>&1
)
rc=$?
set -e

[[ "$rc" -eq 2 ]] || fail "(E) expected exit 2 for missing handoff flag, got $rc"
grep -Fq 'ship-pr-rrr-after-phase14.flag' <<<"$out" \
    || fail "(E) expected die_usage mentioning ship-pr-rrr-after-phase14.flag"

# ---------------------------------------------------------------------------
# (F) Runtime: legacy --resume-phase step8b_rebase tolerates pre-Phase-1 argv.
# ---------------------------------------------------------------------------
write_bump_state() {
    local path=$1
    cat >"$path" <<EOF
PHASE=bump
BRANCH_NAME=feature/test-ship-pr-rebase
ISSUE_NUMBER=3364
RUN_ID=test-ship-pr-rebase
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
MERGE=true
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=false
STALL_STEP=
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
BAIL_FAILURE_DETAIL_LOG=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=
PR_URL=
PR_TITLE=
RESUME_PHASE=step8b_rebase
CALLER_KIND=ship_pr_pre_push
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test_
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$TMPROOT
CI_FIX_REBASE_PENDING=false
EOF
}

bump_state="$TMPROOT/ship-pr-bump-state.sh"
write_bump_state "$bump_state"

set +e
legacy_out=$(
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$SHIP_PR" \
        --state-file "$bump_state" \
        --implement-tmpdir "$TMPROOT" \
        --merge true \
        --draft false \
        --forked false \
        --repo owner/repo \
        --no-admin-fallback true \
        --no-logs-commit true \
        --resume-phase step8b_rebase \
        2>&1
)
legacy_rc=$?
set -e

grep -Fq 'unknown --resume-phase' <<<"$legacy_out" \
    && fail "(F) legacy --resume-phase step8b_rebase must not die_usage (got rc=$legacy_rc)"

# ---------------------------------------------------------------------------
# (G) CI-fix vendor waterfall ingests failed-tier sidecars before rollback.
# ---------------------------------------------------------------------------
(
    set -euo pipefail
    CASE_DIR="$TMPROOT/sidecar-waterfall"
    mkdir -p "$CASE_DIR/scripts" "$CASE_DIR/impl"
    # shellcheck source=scripts/ship-pr.sh
    source "$SHIP_PR"
    SCRIPT_DIR="$CASE_DIR/scripts"
    IMPLEMENT_TMPDIR="$CASE_DIR/impl"
    STATE_FILE="$CASE_DIR/state"
    CALL_LOG="$CASE_DIR/calls.log"
    : >"$STATE_FILE"
    : >"$CALL_LOG"

    python3() {
        local verb="" input="" out=""
        case " $* " in
            *" append-record "*) verb=append-record ;;
            *" record-vendor-sidecar "*) verb=record-vendor-sidecar ;;
            *" agent launch-codex-ci "*)
                # Simulate codex CI launcher: create token-record and emit TOKEN_RECORD=
                while [ "$#" -gt 0 ]; do
                    case "$1" in
                        --output) out=$2; shift 2 ;;
                        *) shift ;;
                    esac
                done
                if [[ -n "$out" ]]; then
                    printf '%s\n' 'TOOL=codex' 'INPUT=1' 'OUTPUT=2' 'TOTAL=3' 'RAW=codex_ci_fix' > "${out}.token-record"
                    printf 'LAUNCHER_EXIT=1\nTOKEN_RECORD=%s\n' "${out}.token-record"
                fi
                return 0
                ;;
            *" agent launch-cursor-ci "*)
                # Simulate cursor CI launcher: create token-record and emit TOKEN_RECORD=
                while [ "$#" -gt 0 ]; do
                    case "$1" in
                        --output) out=$2; shift 2 ;;
                        *) shift ;;
                    esac
                done
                if [[ -n "$out" ]]; then
                    printf '%s\n' 'TOOL=cursor' 'INPUT=4' 'OUTPUT=5' 'TOTAL=9' 'RAW=cursor_ci_fix' > "${out}.token-record"
                    printf 'LAUNCHER_EXIT=0\nTOKEN_RECORD=%s\n' "${out}.token-record"
                fi
                return 0
                ;;
        esac
        while [ "$#" -gt 0 ]; do
            case "$1" in
                --input) input=$2; shift 2 ;;
                *) shift ;;
            esac
        done
        printf '%s|%s|%s\n' "$verb" "$input" "${IMPLEMENT_TMPDIR:-}" >>"$CALL_LOG"
        return 0
    }
    git() {
        case "${1:-} ${2:-}" in
            "rev-parse HEAD") printf '%s\n' "not-a-real-head" ;;
            *) return 0 ;;
        esac
    }
    read_state() {
        case "$1" in
            REPO) printf '%s\n' "owner/repo" ;;
            *) printf '\n' ;;
        esac
    }
    resolve_plan_file() { return 0; }
    failure_capture_path() { printf '%s/failure-%s-%s.log\n' "$CASE_DIR" "$1" "$RANDOM"; }
    record_failure() { printf 'RECORD|%s|%s\n' "$2" "$3" >>"$CALL_LOG"; }
    capture_tracked_dirty_paths() { return 0; }
    capture_untracked_dirty_paths() { return 0; }
    _ci_fix_rollback() { printf 'ROLLBACK\n' >>"$CALL_LOG"; }
    _surface_ci_stderr_tail() { return 0; }
    ship_pr_read_launcher_failure_class() { printf '%s\n' health; }
    _verify_failed_jobs_locally() { return 0; }
    _stage_and_push_ci_fixes() { printf 'STAGE|%s\n' "$2" >>"$CALL_LOG"; return 0; }
    larch_err() { return 0; }

    run_ci_fix_vendor ci-merge run-1 "" 1 ""
    codex_append_line=$(grep -n 'append-record|.*\.codex\.token-record' "$CALL_LOG" | cut -d: -f1)
    codex_vendor_line=$(grep -n 'record-vendor-sidecar|.*\.codex\.token-record' "$CALL_LOG" | cut -d: -f1)
    rollback_line=$(grep -n '^ROLLBACK$' "$CALL_LOG" | cut -d: -f1)
    [[ -n "$codex_append_line" && -n "$codex_vendor_line" && -n "$rollback_line" ]] \
        || fail "(G) expected codex append/vendor ingest before rollback; log=$(cat "$CALL_LOG")"
    [[ "$codex_append_line" -lt "$rollback_line" && "$codex_vendor_line" -lt "$rollback_line" ]] \
        || fail "(G) codex sidecar ingest must happen before rollback; log=$(cat "$CALL_LOG")"
    [[ "$(grep -c 'append-record|.*\.codex\.token-record' "$CALL_LOG")" -eq 1 ]] \
        || fail "(G) codex append-record should run once; log=$(cat "$CALL_LOG")"
    [[ "$(grep -c 'record-vendor-sidecar|.*\.codex\.token-record' "$CALL_LOG")" -eq 1 ]] \
        || fail "(G) codex record-vendor-sidecar should run once; log=$(cat "$CALL_LOG")"
    [[ "$(grep -c 'append-record|.*\.cursor\.token-record' "$CALL_LOG")" -eq 1 ]] \
        || fail "(G) cursor append-record should run once; log=$(cat "$CALL_LOG")"
    [[ "$(grep -c 'record-vendor-sidecar|.*\.cursor\.token-record|'"$IMPLEMENT_TMPDIR" "$CALL_LOG")" -eq 1 ]] \
        || fail "(G) cursor vendor ingest should export IMPLEMENT_TMPDIR; log=$(cat "$CALL_LOG")"
)

# ---------------------------------------------------------------------------
# (H) Stage-and-push CI fixes ingests the winning sidecar once.
# ---------------------------------------------------------------------------
(
    set -euo pipefail
    CASE_DIR="$TMPROOT/sidecar-stage"
    mkdir -p "$CASE_DIR/scripts" "$CASE_DIR/impl"
    # shellcheck source=scripts/ship-pr.sh
    source "$SHIP_PR"
    SCRIPT_DIR="$CASE_DIR/scripts"
    IMPLEMENT_TMPDIR="$CASE_DIR/impl"
    STATE_FILE="$CASE_DIR/state"
    CALL_LOG="$CASE_DIR/calls.log"
    TOKEN_RECORD="$CASE_DIR/winner.token-record"
    : >"$STATE_FILE"
    : >"$CALL_LOG"
    printf '%s\n' 'TOOL=cursor' 'INPUT=4' 'OUTPUT=5' 'TOTAL=9' 'RAW=cursor_ci_fix' > "$TOKEN_RECORD"

    cat >"$SCRIPT_DIR/ci-behind-count.sh" <<'EOF'
#!/usr/bin/env bash
printf 'BEHIND_COUNT=0\n'
EOF
    chmod +x "$SCRIPT_DIR/ci-behind-count.sh"
    cat >"$SCRIPT_DIR/git-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "$SCRIPT_DIR/git-push.sh"

    python3() {
        local verb="" input=""
        case " $* " in
            *" append-record "*) verb=append-record ;;
            *" record-vendor-sidecar "*) verb=record-vendor-sidecar ;;
            *) return 0 ;;
        esac
        while [ "$#" -gt 0 ]; do
            case "$1" in
                --input) input=$2; shift 2 ;;
                *) shift ;;
            esac
        done
        printf '%s|%s|%s\n' "$verb" "$input" "${IMPLEMENT_TMPDIR:-}" >>"$CALL_LOG"
        return 0
    }
    git() {
        case "${1:-} ${2:-}" in
            "rev-parse HEAD") printf '%040d\n' 1 ;;
            *) return 0 ;;
        esac
    }
    read_state() {
        case "$1" in
            FORKED_TARGET) printf '%s\n' false ;;
            *) printf '\n' ;;
        esac
    }
    failure_capture_path() { printf '%s/failure-%s-%s.log\n' "$CASE_DIR" "$1" "$RANDOM"; }
    record_failure() { printf 'RECORD|%s|%s\n' "$2" "$3" >>"$CALL_LOG"; }
    capture_tracked_dirty_paths() { return 0; }
    capture_untracked_dirty_paths() { return 0; }
    run_checks_with_lint_fix_loop() { LAST_LINT_FIX_DELTA_PATHS_FILE=""; return 0; }
    _commit_ci_fix_stage_paths() { return 0; }
    _ci_fix_pending_clear() { CI_FIX_REBASE_PENDING=false; }

    CI_FIX_REBASE_PENDING=false
    SHIP_PR_INGESTED_TOKEN_RECORDS=()
    _stage_and_push_ci_fixes ci-initial "$TOKEN_RECORD" step10 ""
    [[ "$(grep -c "append-record|$TOKEN_RECORD" "$CALL_LOG")" -eq 1 ]] \
        || fail "(H) stage append-record should run once; log=$(cat "$CALL_LOG")"
    [[ "$(grep -c "record-vendor-sidecar|$TOKEN_RECORD|$IMPLEMENT_TMPDIR" "$CALL_LOG")" -eq 1 ]] \
        || fail "(H) stage vendor ingest should run once with IMPLEMENT_TMPDIR; log=$(cat "$CALL_LOG")"
)

echo "PASS: test-ship-pr-rebase.sh — CI-fix rebase structural pins, lint handoff KVs, fork postbump guard, legacy resume, sidecar ingest, and resume guard hold (A-H, D1-runtime, D2)"
