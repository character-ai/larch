#!/usr/bin/env bash
# design-postplan-emit.sh — /design Step 2b post-plan emit phase driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
# shellcheck source=skills/design/scripts/lib-drift-baseline.sh
source "$SCRIPT_DIR/lib-drift-baseline.sh"
larch_quiet_init

fail() {
    larch_err "design-postplan-emit.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-postplan-emit.sh --design-tmpdir PATH [--snapshot-original] [--with-plan-size]'
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
            HARD_TRIGGER_FIRED) HARD_TRIGGER_FIRED="$_value" ;;
            TRIGGER_REASONS) TRIGGER_REASONS="$_value" ;;
            PLAN_LINES) PLAN_LINES="$_value" ;;
            DIFF_ADDED) DIFF_ADDED="$_value" ;;
            DIFF_DELETED) DIFF_DELETED="$_value" ;;
            MECHANICAL_CHURN) MECHANICAL_CHURN="$_value" ;;
            SOFT_ADVISORY) SOFT_ADVISORY="$_value" ;;
            DRIFT_TRIGGER_FIRED) DRIFT_TRIGGER_FIRED="$_value" ;;
            DRIFT_MULTIPLE) DRIFT_MULTIPLE="$_value" ;;
            DRIFT_PLAN_RATIO) DRIFT_PLAN_RATIO="$_value" ;;
            DRIFT_DIFF_RATIO) DRIFT_DIFF_RATIO="$_value" ;;
            BASELINE_PLAN_LINES) BASELINE_PLAN_LINES="$_value" ;;
            BASELINE_DIFF_LINES) BASELINE_DIFF_LINES="$_value" ;;
            PLAN_SIZE_STATUS) PLAN_SIZE_STATUS="$_value" ;;
            WARN) WARN_LINES+=("$_value") ;;
        esac
    done <<<"$text"
}

DESIGN_TMPDIR_ARG=""
SNAPSHOT_ORIGINAL=false
WITH_PLAN_SIZE=false

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
        --with-plan-size)
            WITH_PLAN_SIZE=true
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
WARN_LINES=()
PARTITION_REQUESTED="$(phase_driver_json_boolean_or_sed "$RUN_PARAMS_PATH" partition_requested false)"
READ_CLASSIFICATION_SH="$PLUGIN_ROOT/python/cli.py"
if [[ -f "$READ_CLASSIFICATION_SH" ]]; then
    _classification_stderr="$DESIGN_TMPDIR/.read-design-classification.stderr.$$"
    _classification_warn_count_before=${#WARN_LINES[@]}
    set +e
    WORKFLOW_PATH=$(python3 "$READ_CLASSIFICATION_SH" session read-classification "$RUN_PARAMS_PATH" 2>"$_classification_stderr")
    _classification_rc=$?
    set -e
    if [[ -s "$_classification_stderr" ]]; then
        while IFS= read -r _classification_warn || [[ -n "$_classification_warn" ]]; do
            [[ -n "$_classification_warn" ]] && WARN_LINES+=("$_classification_warn")
        done <"$_classification_stderr"
    fi
    rm -f "$_classification_stderr"
    if [[ "$_classification_rc" -ne 0 ]]; then
        if [[ "${#WARN_LINES[@]}" -eq "$_classification_warn_count_before" ]]; then
            WARN_LINES+=("**⚠ read-design-classification: exited ${_classification_rc}; defaulting design_classification to HARD.**")
        fi
        WORKFLOW_PATH=HARD
    fi
else
    WORKFLOW_PATH=HARD
fi
case "$WORKFLOW_PATH" in SIMPLE|HARD) ;; *) WORKFLOW_PATH=HARD ;; esac

POSTPLAN_EMIT_STATUS=pending
EMIT_PLAN_STATUS=not-run
DIFF_LINES=""
SNAPSHOT_STATUS=not-run
VALIDATE_STATUS=not-run
VALIDATE_DEFECT_COUNT=0
VALIDATE_SKIPPED_COUNT=0
VALIDATE_UNSAFE_TOKEN_COUNT=0
VALIDATE_LOG_FILE=""
PLAN_SIZE_STATUS=not-run
HARD_TRIGGER_FIRED=false
TRIGGER_REASONS=""
PLAN_LINES=""
DIFF_ADDED=""
DIFF_DELETED=""
MECHANICAL_CHURN=false
SOFT_ADVISORY=false
DRIFT_TRIGGER_FIRED=false
DRIFT_MULTIPLE="${LARCH_DESIGN_DRIFT_MULTIPLE:-2}"
DRIFT_PLAN_RATIO=1
DRIFT_DIFF_RATIO=1
BASELINE_PLAN_LINES=""
BASELINE_DIFF_LINES=""
_plan_size_out=""
_plan_size_stderr=""

_postplan_fatal() {
    local status="${1:-emit-failed}"
    shift
    POSTPLAN_EMIT_STATUS="$status"
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_emit_rc1_diagnostic
        WARN_LINES+=("design-postplan-emit.sh: $*")
        _postplan_flush || exit 1
        exit 1
    fi
    if ((${#WARN_LINES[@]})); then
        _postplan_write_result_and_emit
    fi
    larch_err "design-postplan-emit.sh: $*"
    exit 2
}

_postplan_emit_warn_display() {
    local _warn _line
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            [[ -n "$_line" ]] && emit "$(printf '%s' "$_line" | sanitize_diagnostic_line)"
        done <<<"$_warn"
    done
}

_postplan_build_kvs() {
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
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _kvs+=("PLAN_SIZE_STATUS=$PLAN_SIZE_STATUS")
        _kvs+=("HARD_TRIGGER_FIRED=$HARD_TRIGGER_FIRED")
        _kvs+=("TRIGGER_REASONS=$TRIGGER_REASONS")
        _kvs+=("PLAN_LINES=$PLAN_LINES")
        _kvs+=("DIFF_ADDED=$DIFF_ADDED")
        _kvs+=("DIFF_DELETED=$DIFF_DELETED")
        _kvs+=("MECHANICAL_CHURN=$MECHANICAL_CHURN")
        _kvs+=("SOFT_ADVISORY=$SOFT_ADVISORY")
        _kvs+=("PARTITION_REQUESTED=$PARTITION_REQUESTED")
        _kvs+=("DRIFT_TRIGGER_FIRED=$DRIFT_TRIGGER_FIRED")
        _kvs+=("DRIFT_MULTIPLE=$DRIFT_MULTIPLE")
        _kvs+=("DRIFT_PLAN_RATIO=$DRIFT_PLAN_RATIO")
        _kvs+=("DRIFT_DIFF_RATIO=$DRIFT_DIFF_RATIO")
        _kvs+=("BASELINE_PLAN_LINES=$BASELINE_PLAN_LINES")
        _kvs+=("BASELINE_DIFF_LINES=$BASELINE_DIFF_LINES")
    fi
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        _kvs+=("WARN=$_warn")
    done
    printf '%s\n' "${_kvs[@]}"
}

_postplan_write_result_merged() {
    local -a _kvs=()
    while IFS= read -r _kv || [[ -n "$_kv" ]]; do
        _kvs+=("$_kv")
    done < <(_postplan_build_kvs)
    if ! phase_driver_write_result_env "$RESULT_ENV" "${_kvs[@]}"; then
        emit "**⚠ design-postplan-emit: result env write failed; aborting before action dispatch.**"
        return 1
    fi
    _postplan_emit_warn_display
    return 0
}

_postplan_write_result_and_emit() {
    local -a _kvs=()
    while IFS= read -r _kv || [[ -n "$_kv" ]]; do
        _kvs+=("$_kv")
    done < <(_postplan_build_kvs)
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
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        emit_kv WARN "$_warn"
    done
}

_postplan_flush() {
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_write_result_merged
    else
        _postplan_write_result_and_emit
    fi
}

_postplan_emit_rc1_diagnostic() {
    case "${POSTPLAN_EMIT_STATUS:-}" in
        missing-diff-lines)
            emit "**⚠ 2b: plan.txt is missing a final diff_lines metadata line; repair plan.txt before Step 2b.5 / Step 3.**"
            ;;
        snapshot-failed)
            emit "**⚠ 2b: failed to snapshot plan.txt-original for HARD review flow; aborting before Step 3.**"
            ;;
        validate-driver-failed)
            emit "**⚠ 2b: plan-command validator infrastructure failed; aborting before Step 3.**"
            ;;
        *)
            emit "**⚠ 2b: post-plan emit failed (${POSTPLAN_EMIT_STATUS:-unknown}); repair plan.txt before Step 2b.5 / Step 3.**"
            ;;
    esac
}

_postplan_exit_merged_failure() {
    _postplan_emit_rc1_diagnostic
    _postplan_flush || exit 1
    exit 1
}

_postplan_emit_soft_advisory() {
    if [[ "$SOFT_ADVISORY" != true ]]; then
        return 0
    fi
    if [[ "$HARD_TRIGGER_FIRED" == true ]]; then
        emit "⏩ 2b.5: plan-size — mechanical-churn advisory: diff gate downgraded (DIFF_ADDED=${DIFF_ADDED:-} DIFF_DELETED=${DIFF_DELETED:-} DIFF_LINES=${DIFF_LINES:-}); plan-body gate still requires Split/Cancel"
    else
        emit "⏩ 2b.5: plan-size — mechanical-churn advisory: diff gate downgraded (DIFF_ADDED=${DIFF_ADDED:-} DIFF_DELETED=${DIFF_DELETED:-} DIFF_LINES=${DIFF_LINES:-}); proceeding"
    fi
}

_postplan_emit_hard_section() {
    emit "## Plan Size — Hard Trigger"
    emit "PLAN_LINES=${PLAN_LINES:-} DIFF_LINES=${DIFF_LINES:-}"
    if [[ -n "${DIFF_ADDED:-}" ]]; then
        emit "DIFF_ADDED=${DIFF_ADDED}"
    fi
    if [[ -n "${DIFF_DELETED:-}" ]]; then
        emit "DIFF_DELETED=${DIFF_DELETED}"
    fi
}


_postplan_snapshot_drift_baseline() {
    [[ "$SNAPSHOT_ORIGINAL" == true ]] || return 0
    [[ -n "${PLAN_LINES:-}" && -n "${DIFF_LINES:-}" ]] || return 0
    larch_drift_baseline_write_once "$DESIGN_TMPDIR" "$PLAN_LINES" "$DIFF_LINES" || true
}

_postplan_emit_partition_section() {
    emit "## Plan Size — Partition requested"
    emit "trigger=partition-flag PLAN_LINES=${PLAN_LINES:-} DIFF_LINES=${DIFF_LINES:-}"
}

_postplan_append_plan_size_warning() {
    local _plan_size_rc="$1" _validation_log="$DESIGN_TMPDIR/check-plan-size.validation.log"
    local _combined_cap _status_label
    {
        printf '%s\n' "${_plan_size_out:-}"
        [[ -s "$_plan_size_stderr" ]] && cat "$_plan_size_stderr"
    } >"$_validation_log" 2>/dev/null || true
    _status_label="${PLAN_SIZE_STATUS:-unknown}"
    if [[ "$_plan_size_rc" -eq 3 ]]; then
        _status_label=argv-error
    fi
    WARN_LINES+=("**⚠ 2b.5: check-plan-size — ${_status_label}; proceeding without threshold check**")
    set +e
    _combined_cap=$(mktemp "${TMPDIR:-/tmp}/design-postplan-plan-size.XXXXXX")
    cp -f "$_validation_log" "$_combined_cap" 2>/dev/null || printf '%s\n' "${_plan_size_out:-}" >"$_combined_cap"
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 2b.5" \
        --tool "check-plan-size.sh" \
        --exit-code "$_plan_size_rc" \
        --category Warnings \
        --output-file "$_combined_cap" \
        --redact \
        >/dev/null 2>&1 || true
    rm -f "$_combined_cap" 2>/dev/null || true
    set -e
}

_postplan_run_plan_size() {
    local _check_sh="$PLUGIN_ROOT/skills/design/scripts/check-plan-size.sh"
    [[ -x "$_check_sh" ]] || fail "check-plan-size.sh not executable: $_check_sh"
    _plan_size_stderr="$DESIGN_TMPDIR/.check-plan-size.stderr.$$"
    _plan_size_out=""
    set +e
    _plan_size_out=$(env LARCH_QUIET_DISABLE=1 "$_check_sh" --design-tmpdir "$DESIGN_TMPDIR" 2>"$_plan_size_stderr")
    _plan_size_rc=$?
    set -e
    PLAN_SIZE_STATUS=ok
    if [[ "$_plan_size_rc" -eq 0 ]]; then
        parse_kv_from_output "$_plan_size_out"
        rm -f "$_plan_size_stderr" 2>/dev/null || true
        return 0
    fi
    if [[ "$_plan_size_rc" -eq 2 || "$_plan_size_rc" -eq 3 ]]; then
        parse_kv_from_output "$_plan_size_out"
        PLAN_SIZE_STATUS="${PLAN_SIZE_STATUS:-unknown}"
        [[ "$PLAN_SIZE_STATUS" == not-run ]] && PLAN_SIZE_STATUS=unknown
        _postplan_append_plan_size_warning "$_plan_size_rc"
        HARD_TRIGGER_FIRED=false
        TRIGGER_REASONS=""
        SOFT_ADVISORY=false
        rm -f "$_plan_size_stderr" 2>/dev/null || true
        if [[ "$WITH_PLAN_SIZE" == true ]]; then
            POSTPLAN_EMIT_STATUS=plan-size-failed
            PLAN_SIZE_STATUS=failed
            _postplan_exit_merged_failure
        fi
        return 2
    fi
    rm -f "$_plan_size_stderr" 2>/dev/null || true
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        POSTPLAN_EMIT_STATUS=plan-size-failed
        PLAN_SIZE_STATUS=failed
        _postplan_exit_merged_failure
    fi
    fail "check-plan-size.sh failed unexpectedly (exit ${_plan_size_rc})"
}

_postplan_finish_merged_plan_size() {
    local _plan_size_rc=$1
    local _defects_exit="${2:-}"
    if [[ "$_plan_size_rc" -ne 0 ]]; then
        POSTPLAN_EMIT_STATUS=plan-size-failed
        PLAN_SIZE_STATUS=failed
        _postplan_exit_merged_failure
    fi
    _postplan_emit_soft_advisory
    if [[ "$HARD_TRIGGER_FIRED" == true ]]; then
        _postplan_emit_hard_section
        POSTPLAN_EMIT_STATUS=ok
        PLAN_SIZE_STATUS=hard-trigger
        _postplan_flush || exit 1
        exit 12
    fi
    if [[ "$PARTITION_REQUESTED" == true ]]; then
        _postplan_emit_partition_section
        POSTPLAN_EMIT_STATUS=ok
        PLAN_SIZE_STATUS=partition-requested
        _postplan_flush || exit 1
        exit 13
    fi
    if [[ -n "$_defects_exit" ]]; then
        POSTPLAN_EMIT_STATUS=ok
        PLAN_SIZE_STATUS=skipped-defects
        _postplan_flush || exit 1
        exit "$_defects_exit"
    fi
    if [[ "$DRIFT_TRIGGER_FIRED" == true ]]; then
        local _drift_log
        set +e
        _drift_log=$(mktemp "${TMPDIR:-/tmp}/design-postplan-drift.XXXXXX")
        if [[ -n "$_drift_log" ]]; then
            printf '%s\n' "**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=${PLAN_LINES:-} (baseline ${BASELINE_PLAN_LINES:-}, ratio ${DRIFT_PLAN_RATIO:-1}) / DIFF_LINES=${DIFF_LINES:-} (baseline ${BASELINE_DIFF_LINES:-}, ratio ${DRIFT_DIFF_RATIO:-1}) ≥ ×${DRIFT_MULTIPLE:-2}, under absolute limits; proceeding.**" >"$_drift_log" 2>/dev/null || true
            "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
                --log "$DESIGN_TMPDIR/execution-issues.md" \
                --site "design Step 2b.5" \
                --tool "check-plan-size.sh (drift)" \
                --exit-code 0 \
                --category Warnings \
                --output-file "$_drift_log" \
                --redact \
                >/dev/null 2>&1 || true
            rm -f "$_drift_log" 2>/dev/null || true
        fi
        set -e
        POSTPLAN_EMIT_STATUS=ok
        PLAN_SIZE_STATUS=drift-advisory
        _postplan_flush || exit 1
        emit "⏩ 2b.5: plan-size — drift advisory (PLAN_LINES=${PLAN_LINES:-} DIFF_LINES=${DIFF_LINES:-}); proceeding"
        exit 0
    fi
    POSTPLAN_EMIT_STATUS=ok
    PLAN_SIZE_STATUS=under-threshold
    _postplan_flush || exit 1
    emit "⏩ 2b.5: plan-size — under thresholds (PLAN_LINES=${PLAN_LINES:-} DIFF_LINES=${DIFF_LINES:-})"
    exit 0
}

_postplan_resolve_issue() {
    local _issue="${ISSUE_NUMBER:-}"
    if [[ -z "$_issue" && -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
        _issue=$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+ISSUE_NUMBER=/ {v=$0; sub(/^export[[:space:]]+ISSUE_NUMBER=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
    fi
    printf '%s\n' "$_issue"
}

_postplan_resolve_repo() {
    local _repo=""
    if [[ -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
        _repo=$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+REPO=/ {v=$0; sub(/^export[[:space:]]+REPO=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
    fi
    printf '%s\n' "$_repo"
}

_postplan_pause_checkpoint() {
    if [[ ! -f "$DESIGN_TMPDIR/.pause-requested" ]]; then
        return 0
    fi
    local _issue _repo
    _issue="$(_postplan_resolve_issue)"
    _repo="$(_postplan_resolve_repo)"
    [[ -n "$_issue" ]] || _postplan_fatal emit-failed 'pause requested but ISSUE_NUMBER could not be resolved'
    if [[ -n "$_repo" && "$_repo" == -* ]]; then
        POSTPLAN_EMIT_STATUS=pause-failed
        if [[ "$WITH_PLAN_SIZE" == true ]]; then
            _postplan_flush || exit 1
            emit "PAUSE_OK=false"
            emit "ERROR=invalid-repo"
        else
            _postplan_write_result_and_emit
            emit_kv PAUSE_OK false
            emit_kv ERROR invalid-repo
        fi
        exit 1
    fi
    POSTPLAN_EMIT_STATUS=paused
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_flush || exit 1
        emit "**⏸ /design Step 2b: pause requested; saving design state.**"
        exit 11
    fi
    _postplan_write_result_and_emit
    exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$_issue" ${_repo:+--repo "$_repo"}
}

[[ -s "$DESIGN_TMPDIR/plan.txt" ]] || _postplan_fatal missing-plan 'plan.txt missing or empty'

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
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_exit_merged_failure
    fi
    _postplan_write_result_and_emit
    exit 1
fi
if [[ "$EMIT_PLAN_STATUS" != ok ]]; then
    POSTPLAN_EMIT_STATUS=emit-failed
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_exit_merged_failure
    fi
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
            if [[ "$WITH_PLAN_SIZE" == true ]]; then
                _postplan_exit_merged_failure
            fi
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
set +e
_val_out=$("$PLUGIN_ROOT/skills/design/scripts/invoke-plan-validator.sh" "$DESIGN_TMPDIR/plan.txt" 2>&1)
_val_rc=$?
set -e
parse_kv_from_output "$_val_out"
if [[ "$_val_rc" -ne 0 && "$VALIDATE_STATUS" != defects-found ]]; then
    POSTPLAN_EMIT_STATUS=validate-driver-failed
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_exit_merged_failure
    fi
    _postplan_write_result_and_emit
    exit 1
fi
if [[ -z "$VALIDATE_STATUS" || "$VALIDATE_STATUS" == not-run ]]; then
    POSTPLAN_EMIT_STATUS=validate-driver-failed
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _postplan_exit_merged_failure
    fi
    _postplan_write_result_and_emit
    exit 1
fi

if [[ "$WITH_PLAN_SIZE" != true ]]; then
    POSTPLAN_EMIT_STATUS=ok
    _postplan_write_result_and_emit
    exit 0
fi

POSTPLAN_EMIT_STATUS=ok
if [[ "$VALIDATE_STATUS" == defects-found ]]; then
    if [[ "$WITH_PLAN_SIZE" == true ]]; then
        _plan_size_run_rc=0
        _postplan_run_plan_size || _plan_size_run_rc=$?
        if [[ "$_plan_size_run_rc" -eq 0 ]]; then
            _postplan_snapshot_drift_baseline
        fi
        _postplan_finish_merged_plan_size "$_plan_size_run_rc" 10
    fi
    PLAN_SIZE_STATUS=skipped-defects
    _postplan_flush || exit 1
    exit 10
fi

_postplan_pause_checkpoint
_plan_size_run_rc=0
_postplan_run_plan_size || _plan_size_run_rc=$?
if [[ "$_plan_size_run_rc" -eq 0 ]]; then
    _postplan_snapshot_drift_baseline
fi
_postplan_finish_merged_plan_size "$_plan_size_run_rc"
