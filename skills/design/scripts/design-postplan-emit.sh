#!/usr/bin/env bash
# design-postplan-emit.sh — /design Step 2b post-plan emit phase driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "design-postplan-emit.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-postplan-emit.sh --design-tmpdir PATH [--snapshot-original] [--force-validate]'
}

parse_kv_from_output() {
    local text="${1:-}"
    local _line _key _value
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            EMIT_PLAN_STATUS) EMIT_PLAN_STATUS="$_value" ;;
            DIFF_LINES) DIFF_LINES="$_value" ;;
            VALIDATE_STATUS) VALIDATE_STATUS="$_value" ;;
            VALIDATE_DEFECT_COUNT) VALIDATE_DEFECT_COUNT="$_value" ;;
            VALIDATE_SKIPPED_COUNT) VALIDATE_SKIPPED_COUNT="$_value" ;;
            VALIDATE_UNSAFE_TOKEN_COUNT) VALIDATE_UNSAFE_TOKEN_COUNT="$_value" ;;
            VALIDATE_LOG_FILE) VALIDATE_LOG_FILE="$_value" ;;
            WARN) WARN_LINES+=("$_value") ;;
        esac
    done <<<"$text"
}

json_scalar_or_sed() {
    local file="$1" key="$2" default_value="$3" value=""
    if command -v jq >/dev/null 2>&1 && [[ -f "$file" ]]; then
        value=$(jq -r --arg key "$key" '.[$key] // ""' "$file" 2>/dev/null || echo "")
    fi
    if [[ -z "$value" && -f "$file" ]]; then
        value=$(sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$file" 2>/dev/null | head -1)
    fi
    if [[ -z "$value" ]]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$value"
    fi
}

DESIGN_TMPDIR_ARG=""
SNAPSHOT_ORIGINAL=false
FORCE_VALIDATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --snapshot-original)
            SNAPSHOT_ORIGINAL=true
            shift
            ;;
        --force-validate)
            FORCE_VALIDATE=true
            shift
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

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }
[[ -d "$DESIGN_TMPDIR_ARG" ]] || fail "design tmpdir not a directory: $DESIGN_TMPDIR_ARG"
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR

SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

RESULT_ENV="$DESIGN_TMPDIR/.design-postplan-emit-result.env"
RUN_PARAMS_PATH="$DESIGN_TMPDIR/run-params.json"
REVIEW_BUDGET="$(json_scalar_or_sed "$RUN_PARAMS_PATH" review_budget full)"
WORKFLOW_PATH="$(json_scalar_or_sed "$RUN_PARAMS_PATH" workflow_path SIMPLE)"

POSTPLAN_EMIT_STATUS=pending
EMIT_PLAN_STATUS=not-run
DIFF_LINES=""
SNAPSHOT_STATUS=not-run
VALIDATE_STATUS=not-run
VALIDATE_DEFECT_COUNT=0
VALIDATE_SKIPPED_COUNT=0
VALIDATE_UNSAFE_TOKEN_COUNT=0
VALIDATE_LOG_FILE=""
WARN_LINES=()

_postplan_write_result_and_emit() {
    local -a _kvs=()
    _kvs+=("POSTPLAN_EMIT_STATUS=$POSTPLAN_EMIT_STATUS")
    _kvs+=("EMIT_PLAN_STATUS=$EMIT_PLAN_STATUS")
    _kvs+=("DIFF_LINES=$DIFF_LINES")
    _kvs+=("SNAPSHOT_STATUS=$SNAPSHOT_STATUS")
    _kvs+=("VALIDATE_STATUS=$VALIDATE_STATUS")
    _kvs+=("VALIDATE_DEFECT_COUNT=$VALIDATE_DEFECT_COUNT")
    _kvs+=("VALIDATE_SKIPPED_COUNT=$VALIDATE_SKIPPED_COUNT")
    _kvs+=("VALIDATE_UNSAFE_TOKEN_COUNT=$VALIDATE_UNSAFE_TOKEN_COUNT")
    _kvs+=("VALIDATE_LOG_FILE=$VALIDATE_LOG_FILE")
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        _kvs+=("WARN=$_warn")
    done
    if ! phase_driver_write_result_env "$RESULT_ENV" "${_kvs[@]}"; then
        WARN_LINES+=("**⚠ design-postplan-emit: result env write failed; using stdout fallback.**")
    fi
    emit_kv POSTPLAN_EMIT_STATUS "$POSTPLAN_EMIT_STATUS"
    emit_kv EMIT_PLAN_STATUS "$EMIT_PLAN_STATUS"
    emit_kv DIFF_LINES "$DIFF_LINES"
    emit_kv SNAPSHOT_STATUS "$SNAPSHOT_STATUS"
    emit_kv VALIDATE_STATUS "$VALIDATE_STATUS"
    emit_kv VALIDATE_DEFECT_COUNT "$VALIDATE_DEFECT_COUNT"
    emit_kv VALIDATE_SKIPPED_COUNT "$VALIDATE_SKIPPED_COUNT"
    emit_kv VALIDATE_UNSAFE_TOKEN_COUNT "$VALIDATE_UNSAFE_TOKEN_COUNT"
    emit_kv VALIDATE_LOG_FILE "$VALIDATE_LOG_FILE"
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        emit_kv WARN "$_warn"
    done
}

_postplan_resolve_issue() {
    local _issue="${ISSUE_NUMBER:-}"
    # Use awk-only extraction: sourcing source-env.sh executes arbitrary shell code.
    if [[ -z "$_issue" && -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
        _issue=$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+ISSUE_NUMBER=/ {v=$0; sub(/^export[[:space:]]+ISSUE_NUMBER=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
    fi
    printf '%s\n' "$_issue"
}

_postplan_pause_checkpoint() {
    if [[ -f "$DESIGN_TMPDIR/.pause-requested" ]]; then
        local _issue
        _issue="$(_postplan_resolve_issue)"
        [[ -n "$_issue" ]] || fail 'pause requested but ISSUE_NUMBER could not be resolved'
        # Write result env before exec so the orchestrator's mandatory-key check
        # sees POSTPLAN_EMIT_STATUS=paused rather than an empty-result abort when
        # this driver is called via $() capture (exec replaces the subshell only).
        POSTPLAN_EMIT_STATUS=paused
        _postplan_write_result_and_emit
        exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$_issue"
    fi
}

[[ -s "$DESIGN_TMPDIR/plan.txt" ]] || fail 'plan.txt missing or empty'

_postplan_pause_checkpoint
set +e
_emit_out=$(printf 'ACTION=EMIT_PLAN\n' | "$PLUGIN_ROOT/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR" 2>&1)
_emit_rc=$?
set -e
parse_kv_from_output "$_emit_out"
if [[ "$_emit_rc" -ne 0 || "$EMIT_PLAN_STATUS" == missing-diff-lines ]]; then
    if [[ "$EMIT_PLAN_STATUS" == missing-diff-lines ]]; then
        POSTPLAN_EMIT_STATUS=missing-diff-lines
    else
        POSTPLAN_EMIT_STATUS=emit-failed
    fi
    [[ -n "$EMIT_PLAN_STATUS" ]] || EMIT_PLAN_STATUS=not-run
    _postplan_write_result_and_emit
    exit 1
fi
if [[ "$EMIT_PLAN_STATUS" != ok ]]; then
    POSTPLAN_EMIT_STATUS=emit-failed
    _postplan_write_result_and_emit
    exit 1
fi

_postplan_pause_checkpoint
if [[ "$SNAPSHOT_ORIGINAL" == true ]]; then
    if [[ "$WORKFLOW_PATH" == HARD ]]; then
        _snapshot_dest="$DESIGN_TMPDIR/plan.txt-original"
        _snapshot_existed=false
        [[ -e "$_snapshot_dest" ]] && _snapshot_existed=true
        set +e
        _snap_out=$("$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh" write-original --design-tmpdir "$DESIGN_TMPDIR" 2>&1)
        _snap_rc=$?
        set -e
        if [[ "$_snap_rc" -ne 0 ]]; then
            SNAPSHOT_STATUS=failed
            POSTPLAN_EMIT_STATUS=snapshot-failed
            _postplan_write_result_and_emit
            exit 1
        fi
        if [[ "$_snapshot_existed" == true ]]; then
            SNAPSHOT_STATUS=preserved
        else
            SNAPSHOT_STATUS=taken
        fi
    else
        SNAPSHOT_STATUS=skipped-not-hard
    fi
else
    SNAPSHOT_STATUS=skipped-suppressed
fi

_postplan_pause_checkpoint
if [[ "$REVIEW_BUDGET" == quick && "$FORCE_VALIDATE" != true ]]; then
    VALIDATE_STATUS=skipped-quick
else
    set +e
    _val_out=$("$PLUGIN_ROOT/skills/design/scripts/invoke-plan-validator.sh" "$DESIGN_TMPDIR/plan.txt" 2>&1)
    _val_rc=$?
    set -e
    parse_kv_from_output "$_val_out"
    if [[ "$_val_rc" -ne 0 && "$VALIDATE_STATUS" != defects-found ]]; then
        POSTPLAN_EMIT_STATUS=validate-driver-failed
        _postplan_write_result_and_emit
        exit 1
    fi
    if [[ -z "$VALIDATE_STATUS" || "$VALIDATE_STATUS" == not-run ]]; then
        POSTPLAN_EMIT_STATUS=validate-driver-failed
        _postplan_write_result_and_emit
        exit 1
    fi
fi

POSTPLAN_EMIT_STATUS=ok
_postplan_write_result_and_emit
exit 0
