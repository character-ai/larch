#!/usr/bin/env bash
# design-clarify.sh — thin /design Step 0b clarify delegation wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

SESSION_ENV_PATH=""
CLAUDE_PID=""
PHASE=""
ISSUE=""

usage() {
    printf '%s\n' 'Usage: design-clarify.sh --phase fetch|publish --issue N' >&2
}

fail() {
    printf '%s\n' "design-clarify.sh: $*" >&2
    exit 2
}

validate_positive_int() {
    local label="$1" value="$2"
    case "$value" in
        '' | *[!0-9]*) fail "$label must be a positive integer" ;;
    esac
    [[ "$value" != "0" ]] || fail "$label must be a positive integer"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --session-env-path)
            [[ $# -ge 2 ]] || fail '--session-env-path requires a value'
            SESSION_ENV_PATH="$2"
            shift 2
            ;;
        --claude-pid)
            [[ $# -ge 2 ]] || fail '--claude-pid requires a value'
            CLAUDE_PID="$2"
            shift 2
            ;;
        --phase)
            [[ $# -ge 2 ]] || fail '--phase requires a value'
            PHASE="$2"
            shift 2
            ;;
        --issue)
            [[ $# -ge 2 ]] || fail '--issue requires a value'
            ISSUE="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$PHASE" ]] || { usage; fail '--phase is required'; }
case "$PHASE" in
    fetch | publish) ;;
    *) fail '--phase must be fetch or publish' ;;
esac
[[ -n "$ISSUE" ]] || { usage; fail '--issue is required'; }
validate_positive_int --issue "$ISSUE"
[[ -z "$CLAUDE_PID" ]] || validate_positive_int --claude-pid "$CLAUDE_PID"

if [[ -n "$SESSION_ENV_PATH" && -f "$SESSION_ENV_PATH" ]]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
fi

if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT

_delegate_args=()
[ -z "${SESSION_ENV_PATH:-}" ] || _delegate_args+=(--session-env-path "$SESSION_ENV_PATH")
[ -z "${CLAUDE_PID:-}" ] || _delegate_args+=(--claude-pid "$CLAUDE_PID")
_delegate_args+=(--phase "$PHASE" --issue "$ISSUE")

exec "$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" design clarify "${_delegate_args[@]}"
