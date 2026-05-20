#!/usr/bin/env bash
# run-step5-review.sh - Derive /implement Step 5 review flags from tmpdir state.

set -euo pipefail

fail() {
    printf 'run-step5-review.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf 'Usage: run-step5-review.sh --implement-tmpdir PATH --round-num N\n' >&2
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

resolve_run_id() {
    local session_env_path="$1" implement_tmpdir="$2" session_id_file="$3"
    local run_id="" candidate="" manifest_count=0

    run_id="$(session_get "$session_env_path" RUN_ID "")"
    if [[ -z "$run_id" ]]; then
        run_id="$(session_get "$implement_tmpdir/parent-issue.md" RUN_ID "")"
    fi
    if [[ -z "$run_id" && -d "$implement_tmpdir/larch-logs/implement" ]]; then
        for candidate in "$implement_tmpdir"/larch-logs/implement/*/manifest.json; do
            [[ -f "$candidate" ]] || continue
            manifest_count=$((manifest_count + 1))
            run_id="$(basename "$(dirname "$candidate")")"
            if (( manifest_count > 1 )); then
                run_id=""
                break
            fi
        done
    fi
    if [[ -z "$run_id" && -s "$session_id_file" ]]; then
        run_id="$(tr -d '\r\n' < "$session_id_file" 2>/dev/null || true)"
    fi
    printf '%s\n' "$run_id"
}

count_prior_degraded_rounds() {
    local implement_tmpdir="$1" current_round="$2"
    local round=0 count=0
    local degraded_file="" degraded_value=""

    for (( round = 1; round < current_round; round++ )); do
        degraded_file="$implement_tmpdir/round-${round}/review-and-fix.env"
        degraded_value=""
        if [[ -r "$degraded_file" ]]; then
            degraded_value="$(session_get "$degraded_file" DEGRADED_ROUND false)"
        fi
        if [[ "$degraded_value" == "true" ]]; then
            count=$((count + 1))
        fi
    done
    printf '%s\n' "$count"
}

IMPLEMENT_TMPDIR_ARG=""
ROUND_NUM=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR_ARG="$2"
            shift 2
            ;;
        --round-num)
            [[ $# -ge 2 ]] || fail "--round-num requires a value"
            ROUND_NUM="$2"
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
[[ -n "$ROUND_NUM" ]] || { usage; fail "--round-num is required"; }
case "$ROUND_NUM" in
    ''|*[!0-9]*) fail "--round-num must be a positive integer" ;;
esac
(( 10#$ROUND_NUM > 0 )) || fail "--round-num must be a positive integer"

[[ -d "$IMPLEMENT_TMPDIR_ARG" ]] || fail "--implement-tmpdir not a directory: $IMPLEMENT_TMPDIR_ARG"
IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
FEATURE_FILE="$IMPLEMENT_TMPDIR/feature-description.txt"
SESSION_ID_FILE="$IMPLEMENT_TMPDIR/session-id"

[[ -r "$SESSION_ENV_PATH" ]] || fail "session-env not readable: $SESSION_ENV_PATH"
[[ -f "$FEATURE_FILE" ]] || fail "feature file not found: $FEATURE_FILE"

RUN_ID="$(resolve_run_id "$SESSION_ENV_PATH" "$IMPLEMENT_TMPDIR" "$SESSION_ID_FILE")"
[[ -n "$RUN_ID" ]] || fail "RUN_ID unresolved from session-env, parent-issue, manifest, or session-id"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_PLUGIN_ROOT "")}"
if [[ -z "$PLUGIN_ROOT" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export IMPLEMENT_TMPDIR

PLAN_FILE="$(session_get "$SESSION_ENV_PATH" PLAN_FILE "")"
WORKFLOW_PATH="$(session_get "$SESSION_ENV_PATH" POST_PLAN_WORKFLOW_PATH "")"
CODEX_PRESENT="$(session_get "$SESSION_ENV_PATH" CODEX_PRESENT false)"
CURSOR_PRESENT="$(session_get "$SESSION_ENV_PATH" CURSOR_PRESENT false)"
LARCH_TOKEN_SESSION_ID="$(session_get "$SESSION_ENV_PATH" LARCH_TOKEN_SESSION_ID "$RUN_ID")"
LARCH_CLAUDE_SOURCE_FILE="$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_SOURCE_FILE "")"
LARCH_TIMING_LEDGER="$(session_get "$SESSION_ENV_PATH" LARCH_TIMING_LEDGER "")"
DYNAMIC_ARCHETYPES="$(session_get "$SESSION_ENV_PATH" LARCH_DYNAMIC_ARCHETYPES_MAX "")"
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
REVIEW_AND_FIX_ARGS=()

if [[ -z "$PLAN_FILE" ]]; then
    # Belt-and-braces fallback: see run-step1-plan-log.sh for the rationale (#2326).
    DESIGN_EXPORT_PLAN="$IMPLEMENT_TMPDIR/design-export/plan.txt"
    if [[ -s "$DESIGN_EXPORT_PLAN" ]]; then
        printf '**⚠ run-step5-review.sh: PLAN_FILE missing from session-env; recovering from design-export/plan.txt. THIS IS A BUG — investigate the Step 1 writer (persist-post-plan-keys.sh).**\n' >&2
        PLAN_FILE="$DESIGN_EXPORT_PLAN"
    else
        fail "PLAN_FILE missing from session-env"
    fi
fi
[[ -f "$PLAN_FILE" ]] || fail "PLAN_FILE not found: $PLAN_FILE"

case "$WORKFLOW_PATH" in
    SIMPLE)
        REVIEW_PANEL="simple"
        ROUND_CAP="5"
        ;;
    HARD)
        REVIEW_PANEL="hard"
        ROUND_CAP="7"
        ;;
    *)
        fail "POST_PLAN_WORKFLOW_PATH must be SIMPLE or HARD, got: ${WORKFLOW_PATH:-<empty>}"
        ;;
esac

DEGRADED_ROUNDS="$(count_prior_degraded_rounds "$IMPLEMENT_TMPDIR" "$ROUND_NUM")"
case "$DEGRADED_ROUNDS" in
    ''|*[!0-9]*) fail "degraded round count must be numeric, got: ${DEGRADED_ROUNDS:-<empty>}" ;;
esac
ROUND_CAP="$((ROUND_CAP + DEGRADED_ROUNDS))"

case "$CODEX_PRESENT" in true|false) ;; *) fail "CODEX_PRESENT must be true or false, got: $CODEX_PRESENT" ;; esac
case "$CURSOR_PRESENT" in true|false) ;; *) fail "CURSOR_PRESENT must be true or false, got: $CURSOR_PRESENT" ;; esac

REVIEW_AND_FIX_SH="${RUN_STEP5_REVIEW_SH:-$PLUGIN_ROOT/skills/review-and-fix/scripts/review-and-fix.sh}"
[[ -x "$REVIEW_AND_FIX_SH" ]] || fail "review-and-fix.sh not executable: $REVIEW_AND_FIX_SH"

REVIEW_AND_FIX_ARGS=(
    --implement-tmpdir "$IMPLEMENT_TMPDIR"
    --mode diff
    --panel "$REVIEW_PANEL"
    --round-num "$ROUND_NUM"
    --round-cap "$ROUND_CAP"
    --session-env-path "$SESSION_ENV_PATH"
    --codex-available "$CODEX_PRESENT"
    --cursor-available "$CURSOR_PRESENT"
    --plan-file "$PLAN_FILE"
    --feature-file "$FEATURE_FILE"
)
[[ -n "$DYNAMIC_ARCHETYPES" ]] && REVIEW_AND_FIX_ARGS+=(--dynamic-archetypes "$DYNAMIC_ARCHETYPES")
REVIEW_AND_FIX_ARGS+=(--run-id "$RUN_ID")

export LARCH_QUIET_BREADCRUMBS=1
"$REVIEW_AND_FIX_SH" "${REVIEW_AND_FIX_ARGS[@]}"
