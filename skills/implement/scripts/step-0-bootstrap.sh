#!/usr/bin/env bash
# step-0-bootstrap.sh — /implement Step 0 initial/resume bootstrap wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
MODE=""
ISSUE_NUMBER_ARG=""
PREFLIGHT_TMPDIR_ARG=""
CODER_ARG=""
EMERGENCY_REQUESTED_ARG=""
SELF_REVIEW_ARG=""
FORKED_TARGET_ARG=""
UPSTREAM_REPO_ARG=""
RUN_ID_ARG=""
CALLER_ENV_ARG=""
SESSION_ENV_ARG=""
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
        --emergency-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --emergency-requested requires a value' >&2; exit 2; }; EMERGENCY_REQUESTED_ARG=$2; shift 2 ;;
        --self-review-requested) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --self-review-requested requires a value' >&2; exit 2; }; SELF_REVIEW_ARG=$2; shift 2 ;;
        --forked-target) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --forked-target requires a value' >&2; exit 2; }; FORKED_TARGET_ARG=$2; shift 2 ;;
        --upstream-repo) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --upstream-repo requires a value' >&2; exit 2; }; UPSTREAM_REPO_ARG=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --run-id requires a value' >&2; exit 2; }; RUN_ID_ARG=$2; shift 2 ;;
        --caller-env) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --caller-env requires a value' >&2; exit 2; }; CALLER_ENV_ARG=$2; shift 2 ;;
        --session-env) [ $# -ge 2 ] || { printf '%s
' 'step-0-bootstrap.sh: --session-env requires a value' >&2; exit 2; }; SESSION_ENV_ARG=$2; shift 2 ;;
        --help) printf '%s
' 'Usage: step-0-bootstrap.sh --mode initial|resume [--issue-number N] [--preflight-tmpdir PATH] [--coder claude|codex|cursor] [--emergency-requested true|false] [--self-review-requested true|false] [--forked-target true|false] [--upstream-repo OWNER/REPO] [--run-id ID] [--caller-env PATH] [--session-env PATH]'; exit 0 ;;
        *) printf '%s
' "step-0-bootstrap.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$MODE" in initial|resume) ;; *) printf '%s
' 'step-0-bootstrap.sh: --mode initial|resume is required' >&2; exit 2 ;; esac


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
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
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
case "$EMERGENCY_REQUESTED_ARG" in true|false) emergency_requested="$EMERGENCY_REQUESTED_ARG" ;; esac
case "$SELF_REVIEW_ARG" in true|false) self_review="$SELF_REVIEW_ARG" ;; esac
case "$FORKED_TARGET_ARG" in true|false) forked_target="$FORKED_TARGET_ARG" ;; esac
[ -n "$UPSTREAM_REPO_ARG" ] && UPSTREAM_REPO="$UPSTREAM_REPO_ARG"
[ -n "$RUN_ID_ARG" ] && RUN_ID="$RUN_ID_ARG"
[ -n "$CALLER_ENV_ARG" ] && CALLER_ENV_PATH="$CALLER_ENV_ARG"
[ -n "$SESSION_ENV_ARG" ] && SESSION_ENV_PATH="$SESSION_ENV_ARG"
rehydrate_plugin_root
if [ "$MODE" = initial ] && [ "${forked_target:-false}" = "true" ] && [ -z "${UPSTREAM_REPO:-}" ]; then
    set +e
    _fork_env_out=$("$CLAUDE_PLUGIN_ROOT/scripts/implement-fork-env.sh")
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
export forked_target emergency_requested self_review coder RUN_ID PREFLIGHT_TMPDIR
export CALLER_ENV_PATH SESSION_ENV_PATH TARGET_ISSUE_NUMBER ISSUE_NUMBER UPSTREAM_REPO FORK_REPO FORK_OWNER
export LARCH_CLAUDE_PID="${PPID}"
set +e
_inv_out=$("$CLAUDE_PLUGIN_ROOT/scripts/implement-bootstrap-invoke.sh" --mode "$MODE")
_inv_rc=$?
set -e
if [ "$_inv_rc" -eq 2 ]; then
    exit 2
fi
if [ "$_inv_rc" -ne 0 ]; then
    exit "$_inv_rc"
fi
# shellcheck source=scripts/parse-bootstrap-routing-envelope.sh
if [ "$MODE" = resume ]; then
    . "$CLAUDE_PLUGIN_ROOT/scripts/parse-bootstrap-routing-envelope.sh" --preserve-coder
else
    . "$CLAUDE_PLUGIN_ROOT/scripts/parse-bootstrap-routing-envelope.sh"
    printf '%s
' 'progress: type p (or progress) at any time'
fi
printf '%s
' "$_inv_out"
