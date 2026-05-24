#!/usr/bin/env bash
# implement-bootstrap.sh — /implement Step 0 phase dispatcher (Phase 1: phase_infra).

set -uo pipefail
# Intentional: best-effort failure model. Errexit is OFF file-wide. Each leaf
# invocation captures rc via 'rc=$?' after the call; hard failures exit 2 with
# STEP_FAILED=... Do NOT enable -e without auditing every call site.

# Contract KV must land on stdout for orchestrator command substitution. Quiet
# redirection would route emit_kv to FD3 only; keep quiet disabled for this
# entrypoint so stdout carries the full KV stream. Human-facing warnings use
# stderr so parsers can treat stdout as KEY=value only.
export LARCH_QUIET_DISABLE="${LARCH_QUIET_DISABLE:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-execution-issues.sh
source "$SCRIPT_DIR/lib-execution-issues.sh"

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
export CLAUDE_PLUGIN_ROOT

UP_TO_PHASE=""
CALLER_ENV_OPT=""
ISSUE_NUMBER_OPT=""
IMPLEMENT_BAIL_REASON=""

# Parsed / derived in phase_infra (defaults for tail when phases skip)
CURRENT_BRANCH=""
IS_MAIN=""
IS_USER_BRANCH=""
USER_PREFIX=""
ENTRY_GATE=""
SKIP_BRANCH_CHECK=""
SESSION_TMPDIR=""
SESSION_ID=""
REPO=""
REPO_UNAVAILABLE=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
CODEX_BINARY_FOUND=""
CURSOR_BINARY_FOUND=""
IMPLEMENT_TMPDIR=""
CLAUDE_SOURCE_OK=""
LARCH_TOKEN_SESSION_ID=""
LARCH_CLAUDE_SOURCE_FILE=""
LARCH_TIMING_LEDGER=""
codex_available=""
cursor_available=""

usage() {
    larch_err "Usage: implement-bootstrap.sh --up-to-phase <infra|tracking|plan|coder|all> [--caller-env PATH] [--issue-number N]"
}

die_usage() {
    larch_err "implement-bootstrap.sh: $1"
    usage
    exit 2
}

# Apply one KEY=value line to known globals (best-effort).
ingest_kv_line() {
    local line=$1 key val
    line=${line%%$'\r'}
    case "$line" in
        ''|\#*) return 0 ;;
        *=*)
            key=${line%%=*}
            val=${line#*=}
            case "$key" in
                CURRENT_BRANCH) CURRENT_BRANCH=$val ;;
                IS_MAIN) IS_MAIN=$val ;;
                IS_USER_BRANCH) IS_USER_BRANCH=$val ;;
                USER_PREFIX) USER_PREFIX=$val ;;
                ENTRY_GATE) ENTRY_GATE=$val ;;
                SKIP_BRANCH_CHECK) SKIP_BRANCH_CHECK=$val ;;
                SESSION_TMPDIR) SESSION_TMPDIR=$val ;;
                SESSION_ID) SESSION_ID=$val ;;
                REPO) REPO=$val ;;
                REPO_UNAVAILABLE) REPO_UNAVAILABLE=$val ;;
                CODEX_PRESENT) CODEX_PRESENT=$val ;;
                CURSOR_PRESENT) CURSOR_PRESENT=$val ;;
                CODEX_BINARY_FOUND) CODEX_BINARY_FOUND=$val ;;
                CURSOR_BINARY_FOUND) CURSOR_BINARY_FOUND=$val ;;
            esac
            ;;
    esac
}

ingest_kv_block() {
    local data=$1 line
    while IFS= read -r line || [ -n "$line" ]; do
        ingest_kv_line "$line"
    done <<EOF
$data
EOF
}

phase_infra() {
    local gate_err setup_out setup_err branch_out gate_out
    local branch_rc gate_rc setup_rc
    local dynamic_archetypes_value="" caller_dynamic_archetypes
    local session_env_args _source_exit

    branch_out=$("$SCRIPT_DIR/create-branch.sh" --check)
    branch_rc=$?
    if [ "$branch_rc" -ne 0 ]; then
        emit_kv STEP_FAILED create-branch
        exit 2
    fi
    ingest_kv_block "$branch_out"

    gate_err=$(mktemp "${TMPDIR:-/tmp}/larch-ib-gate.XXXXXX")
    gate_out=$("$SCRIPT_DIR/session-entry-gate.sh" \
        --mode implement \
        --current-branch "$CURRENT_BRANCH" \
        --is-main "$IS_MAIN" \
        --is-user-branch "$IS_USER_BRANCH" \
        --user-prefix "$USER_PREFIX" 2>"$gate_err")
    gate_rc=$?
    if [ "$gate_rc" -ne 0 ]; then
        if [ -s "$gate_err" ]; then
            _gh_out=$(grep '^GATE_ERROR=' "$gate_err" 2>/dev/null | head -n 1 || true)
            if [ -n "$_gh_out" ]; then
                printf '%s\n' "$_gh_out"
            else
                while IFS= read -r _gln || [ -n "$_gln" ]; do
                    larch_err "$_gln"
                done <"$gate_err"
            fi
        fi
        emit_kv STEP_FAILED session-entry-gate
        rm -f "$gate_err"
        exit 2
    fi
    rm -f "$gate_err"
    ingest_kv_block "$gate_out"

    local setup_cmd
    setup_cmd=("$SCRIPT_DIR/session-setup.sh" --prefix claude-implement --check-reviewers)
    if [ "$SKIP_BRANCH_CHECK" = "true" ]; then
        setup_cmd+=(--skip-branch-check)
    fi
    if [ -n "$CALLER_ENV_OPT" ]; then
        setup_cmd+=(--caller-env "$CALLER_ENV_OPT")
    fi

    setup_err=$(mktemp "${TMPDIR:-/tmp}/larch-ib-setup.XXXXXX")
    setup_out=$("${setup_cmd[@]}" 2>"$setup_err")
    setup_rc=$?
    if [ "$setup_rc" -ne 0 ]; then
        printf '%s\n' "$setup_out"
        emit_kv STEP_FAILED session-setup
        rm -f "$setup_err"
        exit 2
    fi
    rm -f "$setup_err"
    ingest_kv_block "$setup_out"

    IMPLEMENT_TMPDIR="$SESSION_TMPDIR"
    export IMPLEMENT_TMPDIR

    "$SCRIPT_DIR/write-session-id.sh" --output "$IMPLEMENT_TMPDIR/session-id"
    LARCH_TOKEN_SESSION_ID=$(tr -d '\r\n' <"$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
    export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"

    if "$SCRIPT_DIR/token-claude-source.sh" \
        >"$IMPLEMENT_TMPDIR/claude-source.env" \
        2>"$IMPLEMENT_TMPDIR/claude-source-error.log"; then
        LARCH_CLAUDE_SOURCE_FILE="$IMPLEMENT_TMPDIR/claude-source.env"
        CLAUDE_SOURCE_OK=true
    else
        _source_exit=$?
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "Step 0" \
            --tool "token-claude-source.sh" \
            --exit-code "$_source_exit" \
            --category Warnings \
            --output-file "$IMPLEMENT_TMPDIR/claude-source-error.log" \
            --redact || true
        CLAUDE_SOURCE_OK=false
        LARCH_CLAUDE_SOURCE_FILE=""
    fi

    dynamic_archetypes_value=""
    if [ -z "${dynamic_archetypes_value:-}" ] && [ -n "${CALLER_ENV_OPT:-}" ] && [ -r "$CALLER_ENV_OPT" ]; then
        caller_dynamic_archetypes=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$CALLER_ENV_OPT" --key LARCH_DYNAMIC_ARCHETYPES_MAX --default "")
        case "$caller_dynamic_archetypes" in
            "") ;;
            [0-8]) dynamic_archetypes_value=$caller_dynamic_archetypes ;;
            *)
                larch_err '**⚠ /implement: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller session-env (must be 0..8).**'
                ;;
        esac
    fi

    session_env_args=(
        --output "$IMPLEMENT_TMPDIR/session-env.sh"
        --repo "$REPO"
        --repo-unavailable "$REPO_UNAVAILABLE"
        --codex-present "$CODEX_PRESENT"
        --cursor-present "$CURSOR_PRESENT"
        --codex-binary-found "$CODEX_BINARY_FOUND"
        --cursor-binary-found "$CURSOR_BINARY_FOUND"
        --timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"
        --token-session-id "$LARCH_TOKEN_SESSION_ID"
        --prev-implement-tmpdir "$IMPLEMENT_TMPDIR"
    )
    [ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" ] && session_env_args+=(--claude-source-file "$LARCH_CLAUDE_SOURCE_FILE")
    [ -n "${dynamic_archetypes_value:-}" ] && session_env_args+=(--dynamic-archetypes "$dynamic_archetypes_value")
    "$SCRIPT_DIR/write-session-env.sh" "${session_env_args[@]}"
    "$SCRIPT_DIR/token-ledger.sh" mark "Step 0 — preflight" || true
    "$SCRIPT_DIR/timing-ledger.sh" mark "Step 0 — preflight" || true

    LARCH_TOKEN_SESSION_ID=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
    LARCH_CLAUDE_SOURCE_FILE=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
    LARCH_TIMING_LEDGER=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")

    if [ "$REPO_UNAVAILABLE" = "true" ]; then
        larch_err '**⚠ Could not determine repository name. CI monitoring (Steps 10, 12) and merge (Step 12b) will be skipped.**'
    fi

    local _cb _cp
    _cb=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default "false")
    _cp=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_PRESENT --default "false")
    if [ "$_cb" != "true" ]; then
        larch_err '**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**'
    elif [ "$_cp" != "true" ]; then
        larch_err '**⚠ Codex not healthy for this session (runtime probe failed, skipped probe, auth error, or timeout). Using Claude replacement.**'
    fi
    local _cub _cup
    _cub=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default "false")
    _cup=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_PRESENT --default "false")
    if [ "$_cub" != "true" ]; then
        larch_err '**⚠ Cursor not available (binary not found). Proceeding without Cursor reviewer.**'
    elif [ "$_cup" != "true" ]; then
        larch_err '**⚠ Cursor not healthy for this session (runtime probe failed, skipped probe, auth error, or timeout). Using Claude replacement.**'
    fi

    if [ "$_cb" = "true" ] && [ "$_cp" = "true" ]; then
        codex_available=true
    else
        codex_available=false
    fi
    if [ "$_cub" = "true" ] && [ "$_cup" = "true" ]; then
        cursor_available=true
    else
        cursor_available=false
    fi

    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        emit_breadcrumb "→ step0: infra ready (tmpdir=$IMPLEMENT_TMPDIR session=$SESSION_ID)"
    fi

    return 0
}

phase_tracking() {
    IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-2
    return 0
}

phase_plan_materialize() {
    IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3
    return 0
}

phase_coder_select() {
    IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-4
    return 0
}

emit_infra_kv_block() {
    emit_kv CURRENT_BRANCH "${CURRENT_BRANCH:-}"
    emit_kv IS_MAIN "${IS_MAIN:-}"
    emit_kv IS_USER_BRANCH "${IS_USER_BRANCH:-}"
    emit_kv USER_PREFIX "${USER_PREFIX:-}"
    emit_kv ENTRY_GATE "${ENTRY_GATE:-}"
    emit_kv SKIP_BRANCH_CHECK "${SKIP_BRANCH_CHECK:-}"
    emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
    emit_kv SESSION_ID "${SESSION_ID:-}"
    emit_kv CODEX_PRESENT "${CODEX_PRESENT:-}"
    emit_kv CURSOR_PRESENT "${CURSOR_PRESENT:-}"
    emit_kv CODEX_BINARY_FOUND "${CODEX_BINARY_FOUND:-}"
    emit_kv CURSOR_BINARY_FOUND "${CURSOR_BINARY_FOUND:-}"
    emit_kv REPO "${REPO:-}"
    emit_kv REPO_UNAVAILABLE "${REPO_UNAVAILABLE:-}"
    emit_kv CLAUDE_SOURCE_OK "${CLAUDE_SOURCE_OK:-}"
    emit_kv LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}"
    emit_kv LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}"
    emit_kv LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}"
    emit_kv codex_available "${codex_available:-}"
    emit_kv cursor_available "${cursor_available:-}"
}

emit_final_tail() {
    emit_infra_kv_block
    emit_kv ISSUE_NUMBER "${ISSUE_NUMBER_OPT:-}"
    emit_kv RUN_ID ""
    emit_kv BRANCH_NAME ""
    emit_kv PLAN_FILE ""
    emit_kv coder ""
    emit_kv coder_fallback ""
    emit_kv IMPLEMENT_BAIL_REASON "${IMPLEMENT_BAIL_REASON:-}"
}

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --up-to-phase)
                [ $# -ge 2 ] || die_usage "--up-to-phase requires a value"
                UP_TO_PHASE=$2
                shift 2
                ;;
            --caller-env)
                [ $# -ge 2 ] || die_usage "--caller-env requires a value"
                CALLER_ENV_OPT=$2
                shift 2
                ;;
            --issue-number)
                [ $# -ge 2 ] || die_usage "--issue-number requires a value"
                ISSUE_NUMBER_OPT=$2
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die_usage "unknown argument: $1"
                ;;
        esac
    done

    [ -n "$UP_TO_PHASE" ] || die_usage "--up-to-phase is required"

    phase_infra

    case "$UP_TO_PHASE" in
        infra) ;;
        tracking)
            phase_tracking
            ;;
        plan)
            phase_tracking
            phase_plan_materialize
            ;;
        coder)
            phase_tracking
            phase_plan_materialize
            phase_coder_select
            ;;
        all)
            phase_tracking
            phase_plan_materialize
            phase_coder_select
            ;;
        *)
            die_usage "invalid --up-to-phase: $UP_TO_PHASE (expected infra|tracking|plan|coder|all)"
            ;;
    esac

    emit_final_tail
    exit 0
}

main "$@"
