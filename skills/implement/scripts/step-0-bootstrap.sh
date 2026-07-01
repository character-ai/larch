#!/usr/bin/env bash
# step-0-bootstrap.sh — /implement Step 0 initial/resume bootstrap wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
PY_CLI="$PLUGIN_ROOT/python/cli.py"
MODE=""
ISSUE_NUMBER_ARG=""
PREFLIGHT_TMPDIR_ARG=""
CODER_ARG=""
FORCE_REQUESTED_ARG=""
SELF_REVIEW_ARG=""
SELF_IMPLEMENT_ARG=""
FORKED_TARGET_ARG=""
MERGE_REQUESTED_ARG=""
DRAFT_REQUESTED_ARG=""
NO_ADMIN_FALLBACK_ARG=""
NO_LOGS_COMMIT_ARG=""
UPSTREAM_REPO_ARG=""
RUN_ID_ARG=""
CALLER_ENV_ARG=""
SESSION_ENV_ARG=""
NON_INTERACTIVE_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --mode) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --mode requires a value' >&2; exit 2; }; MODE=$2; shift 2 ;;
        --issue-number) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --issue-number requires a value' >&2; exit 2; }; ISSUE_NUMBER_ARG=$2; shift 2 ;;
        --preflight-tmpdir) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --preflight-tmpdir requires a value' >&2; exit 2; }; PREFLIGHT_TMPDIR_ARG=$2; shift 2 ;;
        --coder) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --coder requires a value' >&2; exit 2; }; CODER_ARG=$2; shift 2 ;;
        --force-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --force-requested requires a value' >&2; exit 2; }; FORCE_REQUESTED_ARG=$2; shift 2 ;;
        --self-review-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --self-review-requested requires a value' >&2; exit 2; }; SELF_REVIEW_ARG=$2; shift 2 ;;
        --self-implement-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --self-implement-requested requires a value' >&2; exit 2; }; SELF_IMPLEMENT_ARG=$2; shift 2 ;;
        --forked-target) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --forked-target requires a value' >&2; exit 2; }; FORKED_TARGET_ARG=$2; shift 2 ;;
        --merge-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --merge-requested requires a value' >&2; exit 2; }; MERGE_REQUESTED_ARG=$2; shift 2 ;;
        --draft-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --draft-requested requires a value' >&2; exit 2; }; DRAFT_REQUESTED_ARG=$2; shift 2 ;;
        --no-admin-fallback) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --no-admin-fallback requires a value' >&2; exit 2; }; NO_ADMIN_FALLBACK_ARG=$2; shift 2 ;;
        --no-logs-commit) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --no-logs-commit requires a value' >&2; exit 2; }; NO_LOGS_COMMIT_ARG=$2; shift 2 ;;
        --upstream-repo) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --upstream-repo requires a value' >&2; exit 2; }; UPSTREAM_REPO_ARG=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --run-id requires a value' >&2; exit 2; }; RUN_ID_ARG=$2; shift 2 ;;
        --caller-env) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --caller-env requires a value' >&2; exit 2; }; CALLER_ENV_ARG=$2; shift 2 ;;
        --session-env) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --session-env requires a value' >&2; exit 2; }; SESSION_ENV_ARG=$2; shift 2 ;;
        --non-interactive) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --non-interactive requires a value' >&2; exit 2; }; NON_INTERACTIVE_ARG=$2; shift 2 ;;
        --help) printf '%s
' 'Usage: step-0-bootstrap.sh --mode initial|resume [--issue-number N] [--preflight-tmpdir PATH] [--coder claude|codex|cursor] [--force-requested true|false] [--self-review-requested true|false] [--self-implement-requested true|false] [--forked-target true|false] [--merge-requested true|false] [--draft-requested true|false] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--upstream-repo OWNER/REPO] [--run-id ID] [--caller-env PATH] [--session-env PATH]'; exit 0 ;;
        *) printf '%s
' "step-0-bootstrap.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$MODE" in initial|resume) ;; *) printf '%s
' 'step-0-bootstrap.sh: --mode initial|resume is required' >&2; exit 2 ;; esac
case "$FORCE_REQUESTED_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --force-requested must be true or false' >&2; exit 2 ;; esac
case "$SELF_REVIEW_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --self-review-requested must be true or false' >&2; exit 2 ;; esac
case "$SELF_IMPLEMENT_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --self-implement-requested must be true or false' >&2; exit 2 ;; esac
case "$FORKED_TARGET_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --forked-target must be true or false' >&2; exit 2 ;; esac
case "$MERGE_REQUESTED_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --merge-requested must be true or false' >&2; exit 2 ;; esac
case "$DRAFT_REQUESTED_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --draft-requested must be true or false' >&2; exit 2 ;; esac
case "$NO_ADMIN_FALLBACK_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --no-admin-fallback must be true or false' >&2; exit 2 ;; esac
case "$NO_LOGS_COMMIT_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --no-logs-commit must be true or false' >&2; exit 2 ;; esac
case "$NON_INTERACTIVE_ARG" in ""|true|false) ;; *) printf '%s
' 'step-0-bootstrap.sh: --non-interactive must be true or false' >&2; exit 2 ;; esac


rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$PY_CLI" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
export IMPLEMENT_TMPDIR
[ -n "$ISSUE_NUMBER_ARG" ] && TARGET_ISSUE_NUMBER="$ISSUE_NUMBER_ARG"
[ -n "$PREFLIGHT_TMPDIR_ARG" ] && PREFLIGHT_TMPDIR="$PREFLIGHT_TMPDIR_ARG"
[ -n "$CODER_ARG" ] && coder="$CODER_ARG"
case "$FORCE_REQUESTED_ARG" in true|false) force_requested="$FORCE_REQUESTED_ARG" ;; esac
case "$SELF_REVIEW_ARG" in true|false) self_review="$SELF_REVIEW_ARG" ;; esac
case "$SELF_IMPLEMENT_ARG" in true|false) self_implement="$SELF_IMPLEMENT_ARG" ;; esac
case "$FORKED_TARGET_ARG" in true|false) forked_target="$FORKED_TARGET_ARG" ;; esac
case "$MERGE_REQUESTED_ARG" in true|false) merge="$MERGE_REQUESTED_ARG" ;; esac
case "$DRAFT_REQUESTED_ARG" in true|false) draft="$DRAFT_REQUESTED_ARG" ;; esac
case "$NO_ADMIN_FALLBACK_ARG" in true|false) no_admin_fallback="$NO_ADMIN_FALLBACK_ARG" ;; esac
case "$NO_LOGS_COMMIT_ARG" in true|false) no_logs_commit="$NO_LOGS_COMMIT_ARG" ;; esac
[ -n "$UPSTREAM_REPO_ARG" ] && UPSTREAM_REPO="$UPSTREAM_REPO_ARG"
[ -n "$RUN_ID_ARG" ] && RUN_ID="$RUN_ID_ARG"
[ -n "$CALLER_ENV_ARG" ] && CALLER_ENV_PATH="$CALLER_ENV_ARG"
[ -n "$SESSION_ENV_ARG" ] && SESSION_ENV_PATH="$SESSION_ENV_ARG"
_non_interactive=false
case "$NON_INTERACTIVE_ARG" in
    true) _non_interactive=true ;;
    false) _non_interactive=false ;;
    "")
        _resolved=$(python3 "$PY_CLI" bootstrap resolve-non-interactive 2>/dev/null || printf '%s' false)
        case "$_resolved" in true) _non_interactive=true ;; esac
        ;;
esac
rehydrate_plugin_root
read_run_flag_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/run-flags.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$PY_CLI" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}
if [ "$MODE" = resume ] && [ -n "${IMPLEMENT_TMPDIR:-}" ]; then
    if [ -z "${PREFLIGHT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/preflight-tmpdir.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/preflight-tmpdir.env"
    fi
    if [ -z "${forked_target:-}" ]; then
        _session_forked=$(read_session_key FORKED_TARGET "false")
        case "$_session_forked" in true|false) forked_target="$_session_forked" ;; esac
    fi
    case "${force_requested:-}" in true|false) ;; *)
        _run_force=$(read_run_flag_key FORCE_REQUESTED "")
        case "$_run_force" in true|false) force_requested="$_run_force" ;; esac
        ;;
    esac
    case "${self_review:-}" in true|false) ;; *)
        _run_self_review=$(read_run_flag_key SELF_REVIEW_REQUESTED "")
        case "$_run_self_review" in true|false) self_review="$_run_self_review" ;; esac
        ;;
    esac
    case "${self_implement:-}" in true|false) ;; *)
        _run_self_implement=$(read_run_flag_key SELF_IMPLEMENT_REQUESTED "")
        case "$_run_self_implement" in true|false) self_implement="$_run_self_implement" ;; esac
        ;;
    esac
    read_ship_seed_key() {
        local key=$1 default_value=$2 file
        file="${IMPLEMENT_TMPDIR:-}/ship-seed-input.env"
        if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
            python3 "$PY_CLI" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
        else
            printf '%s\n' "$default_value"
        fi
    }
    for _ship_flag in MERGE DRAFT NO_ADMIN_FALLBACK NO_LOGS_COMMIT; do
        case "$_ship_flag" in
            MERGE) [ -z "${merge:-}" ] && merge=$(read_ship_seed_key MERGE false) ;;
            DRAFT) [ -z "${draft:-}" ] && draft=$(read_ship_seed_key DRAFT false) ;;
            NO_ADMIN_FALLBACK) [ -z "${no_admin_fallback:-}" ] && no_admin_fallback=$(read_ship_seed_key NO_ADMIN_FALLBACK false) ;;
            NO_LOGS_COMMIT) [ -z "${no_logs_commit:-}" ] && no_logs_commit=$(read_ship_seed_key NO_LOGS_COMMIT false) ;;
        esac
    done
    if [ -z "${TARGET_ISSUE_NUMBER:-}" ] && [ -z "${ISSUE_NUMBER:-}" ]; then
        _sentinel="$IMPLEMENT_TMPDIR/parent-issue.md"
        if [ -f "$_sentinel" ]; then
            _sentinel_out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue read --sentinel "$_sentinel" 2>/dev/null || true)
            _sentinel_issue=$(printf '%s\n' "$_sentinel_out" | grep '^ISSUE_NUMBER=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
            _sentinel_run_id=$(printf '%s\n' "$_sentinel_out" | grep '^RUN_ID=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
            [ -n "$_sentinel_issue" ] && TARGET_ISSUE_NUMBER="$_sentinel_issue" && ISSUE_NUMBER="$_sentinel_issue"
            if [ -z "${RUN_ID:-}" ] && [ -n "$_sentinel_run_id" ]; then
                RUN_ID="$_sentinel_run_id"
            fi
        fi
        if [ -z "${TARGET_ISSUE_NUMBER:-}" ]; then
            _session_issue=$(read_session_key ISSUE_NUMBER "")
            [ -n "$_session_issue" ] && TARGET_ISSUE_NUMBER="$_session_issue" && ISSUE_NUMBER="$_session_issue"
        fi
    fi
    if [ -z "${RUN_ID:-}" ]; then
        _session_run_id=$(read_session_key RUN_ID "")
        [ -n "$_session_run_id" ] && RUN_ID="$_session_run_id"
    fi
fi
if [ "${forked_target:-false}" = "true" ] && [ -z "${UPSTREAM_REPO:-}" ]; then
    set +e
    _fork_env_out=$(python3 "$PY_CLI" admission fork-env)
    _fork_env_rc=$?
    set -e
    if [ "$_fork_env_rc" -ne 0 ]; then
        printf '%s\n' "$_fork_env_out"
        exit "$_fork_env_rc"
    fi
    while IFS= read -r _fork_env_line || [ -n "$_fork_env_line" ]; do
        case "$_fork_env_line" in
            CALLER_ENV_PATH=*) CALLER_ENV_PATH=${_fork_env_line#*=} ;;
            UPSTREAM_REPO=*) UPSTREAM_REPO=${_fork_env_line#*=} ;;
            FORK_REPO=*) FORK_REPO=${_fork_env_line#*=} ;;
            FORK_OWNER=*) FORK_OWNER=${_fork_env_line#*=} ;;
            FORKED_TARGET=*) forked_target=${_fork_env_line#*=} ;;
        esac
    done <<EOF
$_fork_env_out
EOF
    printf '%s\n' "$_fork_env_out"
fi
if [ -n "${IMPLEMENT_TMPDIR:-}" ]; then
    rehydrate_larch_triplet
fi
export forked_target force_requested self_review self_implement coder RUN_ID PREFLIGHT_TMPDIR
export merge draft no_admin_fallback no_logs_commit
export CALLER_ENV_PATH SESSION_ENV_PATH TARGET_ISSUE_NUMBER ISSUE_NUMBER UPSTREAM_REPO FORK_REPO FORK_OWNER
export LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"
if [ -n "${PREFLIGHT_TMPDIR:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ]; then
    printf 'PREFLIGHT_TMPDIR=%s\n' "$PREFLIGHT_TMPDIR" >"$IMPLEMENT_TMPDIR/preflight-tmpdir.env.tmp"
    mv -f "$IMPLEMENT_TMPDIR/preflight-tmpdir.env.tmp" "$IMPLEMENT_TMPDIR/preflight-tmpdir.env"
fi
set +e
_inv_out=$(python3 "$PY_CLI" bootstrap invoke --mode "$MODE"     --issue-number "${TARGET_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"     --preflight-tmpdir "${PREFLIGHT_TMPDIR:-}"     --coder "${coder:-}"     --force-requested "${force_requested:-false}"     --self-review-requested "${self_review:-false}"     --self-implement-requested "${self_implement:-false}"     --forked-target "${forked_target:-false}"     --merge-requested "${merge:-false}"     --draft-requested "${draft:-false}"     --no-admin-fallback "${no_admin_fallback:-false}"     --no-logs-commit "${no_logs_commit:-false}"     --upstream-repo "${UPSTREAM_REPO:-}"     --run-id "${RUN_ID:-}"     --caller-env "${CALLER_ENV_PATH:-${SESSION_ENV_PATH:-}}"     --non-interactive "$_non_interactive")
_inv_rc=$?
set -e
if [ "$_inv_rc" -eq 2 ]; then
    exit 2
fi
if [ "$_inv_rc" -ne 0 ]; then
    exit "$_inv_rc"
fi
if [ "$MODE" != resume ]; then
    printf '%s
' 'progress: type p (or progress) at any time'
fi
printf '%s
' "$_inv_out"
