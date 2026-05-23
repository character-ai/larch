#!/usr/bin/env bash
# run-step5-review.sh - Derive /implement Step 5 review flags from tmpdir state.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-implement-round-cap.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-implement-round-cap.sh"

fail() {
    printf 'run-step5-review.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf 'Usage: run-step5-review.sh --implement-tmpdir PATH [options]\n' >&2
    printf '  --mode loop|single|mav-apply   Dispatch mode (default: loop if --round-num omitted; single if --round-num set without --mode)\n' >&2
    printf '  --round-num N                  Required for --mode single and mav-apply; omitted for loop\n' >&2
    printf '  --starting-round N             Loop resume starting round (default 1; passthrough to review-and-fix.sh)\n' >&2
    printf '  --findings-file PATH           Required for --mode mav-apply (accepted findings path)\n' >&2
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

IMPLEMENT_TMPDIR_ARG=""
ROUND_NUM=""
STEP5_MODE=""
STARTING_ROUND="1"
FINDINGS_FILE_MAV=""

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
        --mode)
            [[ $# -ge 2 ]] || fail "--mode requires a value"
            STEP5_MODE="$2"
            shift 2
            ;;
        --starting-round)
            [[ $# -ge 2 ]] || fail "--starting-round requires a value"
            STARTING_ROUND="$2"
            shift 2
            ;;
        --findings-file)
            [[ $# -ge 2 ]] || fail "--findings-file requires a value"
            FINDINGS_FILE_MAV="$2"
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

if [[ -z "$STEP5_MODE" ]]; then
    if [[ -n "$ROUND_NUM" ]]; then
        STEP5_MODE="single"
    else
        STEP5_MODE="loop"
    fi
fi

case "$STEP5_MODE" in
    loop|single|mav-apply) ;;
    *) fail "--mode must be loop, single, or mav-apply (got: $STEP5_MODE)" ;;
esac

case "$STEP5_MODE" in
    single|mav-apply)
        [[ -n "$ROUND_NUM" ]] || { usage; fail "--round-num is required for --mode $STEP5_MODE"; }
        ;;
    loop)
        [[ -z "$ROUND_NUM" ]] || fail "--mode loop does not take --round-num (got: $ROUND_NUM)"
        ;;
esac

case "$STARTING_ROUND" in
    ''|*[!0-9]*) fail "--starting-round must be a positive integer" ;;
esac
(( 10#$STARTING_ROUND > 0 )) || fail "--starting-round must be a positive integer"

if [[ "$STEP5_MODE" == "mav-apply" ]]; then
    [[ -n "$FINDINGS_FILE_MAV" ]] || fail "--findings-file is required for --mode mav-apply"
fi

case "$ROUND_NUM" in
    ''|*[!0-9]*) ;;
    *)
        (( 10#$ROUND_NUM > 0 )) || fail "--round-num must be a positive integer"
        ;;
esac

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
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export IMPLEMENT_TMPDIR

PLAN_FILE="$IMPLEMENT_TMPDIR/plan.txt"
CODEX_PRESENT="$(session_get "$SESSION_ENV_PATH" CODEX_PRESENT false)"
CURSOR_PRESENT="$(session_get "$SESSION_ENV_PATH" CURSOR_PRESENT false)"
LARCH_TOKEN_SESSION_ID="$(session_get "$SESSION_ENV_PATH" LARCH_TOKEN_SESSION_ID "$RUN_ID")"
LARCH_CLAUDE_SOURCE_FILE="$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_SOURCE_FILE "")"
LARCH_TIMING_LEDGER="$(session_get "$SESSION_ENV_PATH" LARCH_TIMING_LEDGER "")"
DYNAMIC_ARCHETYPES="$(session_get "$SESSION_ENV_PATH" LARCH_DYNAMIC_ARCHETYPES_MAX "")"
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
REVIEW_AND_FIX_ARGS=()

[[ -f "$PLAN_FILE" ]] || fail "plan file not found at conventional path: $PLAN_FILE"
[[ -s "$PLAN_FILE" ]] || fail "plan file is empty at conventional path: $PLAN_FILE"

case "$CODEX_PRESENT" in true|false) ;; *) fail "CODEX_PRESENT must be true or false, got: $CODEX_PRESENT" ;; esac
case "$CURSOR_PRESENT" in true|false) ;; *) fail "CURSOR_PRESENT must be true or false, got: $CURSOR_PRESENT" ;; esac

REVIEW_AND_FIX_SH="${RUN_STEP5_REVIEW_SH:-$PLUGIN_ROOT/skills/review-and-fix/scripts/review-and-fix.sh}"
[[ -x "$REVIEW_AND_FIX_SH" ]] || fail "review-and-fix.sh not executable: $REVIEW_AND_FIX_SH"

# Fixed base Step 5 round cap (unified hard workflow contract); see scripts/run-step5-review.md.
ROUND_CAP_BASE="5"

case "$STEP5_MODE" in
    loop)
        REVIEW_AND_FIX_ARGS=(
            --implement-tmpdir "$IMPLEMENT_TMPDIR"
            --mode loop
            --round-cap "$ROUND_CAP_BASE"
            --starting-round "$STARTING_ROUND"
            --session-env-path "$SESSION_ENV_PATH"
            --codex-available "$CODEX_PRESENT"
            --cursor-available "$CURSOR_PRESENT"
            --plan-file "$PLAN_FILE"
            --feature-file "$FEATURE_FILE"
        )
        ;;
    single)
        DEGRADED_ROUNDS="$(count_prior_degraded_rounds "$IMPLEMENT_TMPDIR" "$ROUND_NUM")"
        case "$DEGRADED_ROUNDS" in
            ''|*[!0-9]*) fail "degraded round count must be numeric, got: ${DEGRADED_ROUNDS:-<empty>}" ;;
        esac
        ROUND_CAP_INFLATED="$((ROUND_CAP_BASE + DEGRADED_ROUNDS))"
        if [[ "$ROUND_NUM" == "1" ]]; then
            printf "run-step5-review.sh: base Step 5 review round cap is %s; degraded prior rounds extend the effective cap (this round: %s).\n" \
                "$ROUND_CAP_BASE" "$ROUND_CAP_INFLATED" >&2
        fi
        REVIEW_AND_FIX_ARGS=(
            --implement-tmpdir "$IMPLEMENT_TMPDIR"
            --mode diff
            --round-num "$ROUND_NUM"
            --round-cap "$ROUND_CAP_INFLATED"
            --session-env-path "$SESSION_ENV_PATH"
            --codex-available "$CODEX_PRESENT"
            --cursor-available "$CURSOR_PRESENT"
            --plan-file "$PLAN_FILE"
            --feature-file "$FEATURE_FILE"
        )
        ;;
    mav-apply)
        REVIEW_AND_FIX_ARGS=(
            --implement-tmpdir "$IMPLEMENT_TMPDIR"
            --mode mav-apply
            --round-num "$ROUND_NUM"
            --findings-file "$FINDINGS_FILE_MAV"
            --session-env-path "$SESSION_ENV_PATH"
            --codex-available "$CODEX_PRESENT"
            --cursor-available "$CURSOR_PRESENT"
            --plan-file "$PLAN_FILE"
            --feature-file "$FEATURE_FILE"
        )
        ;;
esac

[[ -n "$DYNAMIC_ARCHETYPES" ]] && REVIEW_AND_FIX_ARGS+=(--dynamic-archetypes "$DYNAMIC_ARCHETYPES")
REVIEW_AND_FIX_ARGS+=(--run-id "$RUN_ID")

export LARCH_QUIET_BREADCRUMBS=1
"$REVIEW_AND_FIX_SH" "${REVIEW_AND_FIX_ARGS[@]}"
