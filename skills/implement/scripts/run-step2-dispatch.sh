#!/usr/bin/env bash
# run-step2-dispatch.sh - Derive /implement Step 2 dispatcher flags.

set -euo pipefail

fail() {
    printf 'run-step2-dispatch.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf 'Usage: run-step2-dispatch.sh --implement-tmpdir PATH --coder CODER [--answers PATH]\n' >&2
}

session_get() {
    local file="$1" key="$2" default_value="${3-}" value
    value=$(awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true)
    if [[ -z "$value" ]]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$value"
    fi
}

IMPLEMENT_TMPDIR_ARG=""
CODER=""
ANSWERS_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR_ARG="$2"
            shift 2
            ;;
        --coder)
            [[ $# -ge 2 ]] || fail "--coder requires a value"
            CODER="$2"
            shift 2
            ;;
        --answers)
            [[ $# -ge 2 ]] || fail "--answers requires a value"
            ANSWERS_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$IMPLEMENT_TMPDIR_ARG" ]] || { usage; fail "--implement-tmpdir is required"; }
[[ -n "$CODER" ]] || { usage; fail "--coder is required"; }
[[ -d "$IMPLEMENT_TMPDIR_ARG" ]] || fail "--implement-tmpdir not a directory: $IMPLEMENT_TMPDIR_ARG"

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
FEATURE_FILE="$IMPLEMENT_TMPDIR/feature-description.txt"
[[ -r "$SESSION_ENV_PATH" ]] || fail "session-env not readable: $SESSION_ENV_PATH"
[[ -f "$FEATURE_FILE" ]] || fail "feature file not found: $FEATURE_FILE"

if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    fail "--answers path does not exist: $ANSWERS_FILE"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_PLUGIN_ROOT "")}"
if [[ -z "$PLUGIN_ROOT" ]]; then
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export IMPLEMENT_TMPDIR

# Source lib-quiet only for larch_quiet_append_done_trap; do NOT call
# larch_quiet_init here because existing diagnostics use >&2 directly and
# initializing quiet mode would redirect them to a log file.
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_append_done_trap

PLAN_FILE="$IMPLEMENT_TMPDIR/plan.txt"
CURSOR_PRESENT="$(session_get "$SESSION_ENV_PATH" CURSOR_PRESENT false)"
WORKFLOW_PATH="HARD"

[[ -f "$PLAN_FILE" ]] || fail "plan file not found at conventional path: $PLAN_FILE"
case "$CURSOR_PRESENT" in true|false) ;; *) fail "CURSOR_PRESENT must be true or false, got: $CURSOR_PRESENT" ;; esac
case "$WORKFLOW_PATH" in SIMPLE|HARD) ;; *) fail "WORKFLOW_PATH must be SIMPLE or HARD, got: ${WORKFLOW_PATH:-<empty>}" ;; esac
if [[ "$CODER" == "cursor" && "$CURSOR_PRESENT" != "true" ]]; then
    fail "cursor coder selected at Step 0 but CURSOR_PRESENT=$CURSOR_PRESENT in session-env; refusing Step 2 dispatch because that would silently override bootstrap routing"
fi

DISPATCHER_SH="${RUN_STEP2_IMPLEMENT_SH:-$PLUGIN_ROOT/skills/implement/scripts/step2-implement.sh}"
[[ -x "$DISPATCHER_SH" ]] || fail "step2-implement.sh not executable: $DISPATCHER_SH"

argv=(
    --tmpdir "$IMPLEMENT_TMPDIR"
    --plan-file "$PLAN_FILE"
    --feature-file "$FEATURE_FILE"
    --coder "$CODER"
    --cursor-present "$CURSOR_PRESENT"
    --workflow "$WORKFLOW_PATH"
)

if [[ -n "$ANSWERS_FILE" ]]; then
    argv+=(--answers "$ANSWERS_FILE")
fi

"$DISPATCHER_SH" "${argv[@]}"
