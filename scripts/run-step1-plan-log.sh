#!/usr/bin/env bash
# run-step1-plan-log.sh - Compose and write the /implement Step 1 plan batch.

set -euo pipefail

fail() {
    printf 'run-step1-plan-log.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf 'Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT\n' >&2
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
GOAL_TEXT=""
GOAL_TEXT_SET=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR_ARG="$2"
            shift 2
            ;;
        --goal-text)
            [[ $# -ge 2 ]] || fail "--goal-text requires a value"
            GOAL_TEXT="$2"
            GOAL_TEXT_SET=true
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
[[ "$GOAL_TEXT_SET" == "true" ]] || { usage; fail "--goal-text is required"; }
[[ -d "$IMPLEMENT_TMPDIR_ARG" ]] || fail "--implement-tmpdir not a directory: $IMPLEMENT_TMPDIR_ARG"

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
SESSION_ID_FILE="$IMPLEMENT_TMPDIR/session-id"
[[ -r "$SESSION_ENV_PATH" ]] || fail "session-env not readable: $SESSION_ENV_PATH"
[[ -s "$SESSION_ID_FILE" ]] || fail "session-id not found or empty: $SESSION_ID_FILE"

RUN_ID="$(tr -d '\r\n' < "$SESSION_ID_FILE" 2>/dev/null || true)"
[[ -n "$RUN_ID" ]] || fail "session-id is empty: $SESSION_ID_FILE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_PLUGIN_ROOT "")}"
if [[ -z "$PLUGIN_ROOT" ]]; then
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export IMPLEMENT_TMPDIR

PLAN_FILE="$(session_get "$SESSION_ENV_PATH" PLAN_FILE "")"
[[ -n "$PLAN_FILE" ]] || fail "PLAN_FILE missing from session-env"
[[ -f "$PLAN_FILE" ]] || fail "PLAN_FILE not found: $PLAN_FILE"

COMPOSE_SH="${RUN_STEP1_COMPOSE_SH:-$PLUGIN_ROOT/scripts/compose-plan-goals-test.sh}"
LARCH_LOG_SH="${RUN_STEP1_LARCH_LOG_SH:-$PLUGIN_ROOT/scripts/larch-log.sh}"
[[ -x "$COMPOSE_SH" ]] || fail "compose-plan-goals-test.sh not executable: $COMPOSE_SH"
[[ -x "$LARCH_LOG_SH" ]] || fail "larch-log.sh not executable: $LARCH_LOG_SH"

OUTPUT_FILE="$IMPLEMENT_TMPDIR/plan-goals-test.md"
OUTPUT_TMP="$(mktemp "$IMPLEMENT_TMPDIR/plan-goals-test.md.tmp.XXXXXX")"
cleanup() {
    rm -f "$OUTPUT_TMP"
}
trap cleanup EXIT

"$COMPOSE_SH" --plan-file "$PLAN_FILE" --goal-text "$GOAL_TEXT" > "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FILE"
trap - EXIT

"$LARCH_LOG_SH" write \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$RUN_ID" \
    --batch plan-goals-test \
    --input-file "$OUTPUT_FILE"
