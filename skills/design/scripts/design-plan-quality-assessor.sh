#!/usr/bin/env bash
# design-plan-quality-assessor.sh — /design Step 3.6 plan-quality assessor phase driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "design-plan-quality-assessor.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-plan-quality-assessor.sh --design-tmpdir PATH --codex-present true|false --cursor-present true|false [--timeout SECS]'
}

parse_kv_from_output() {
    local text="${1:-}"
    local _line _key _value
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            ASSESSOR_STATUS) ASSESSOR_STATUS="$_value" ;;
            ASSESSOR_VERDICT) ASSESSOR_VERDICT="$_value" ;;
            EFFECTIVE_ASSESSORS) EFFECTIVE_ASSESSORS="$_value" ;;
            ASSESSOR_VERDICT_FILE) ASSESSOR_VERDICT_FILE="$_value" ;;
            ASSESSOR_VERDICT_ENV) ASSESSOR_VERDICT_ENV="$_value" ;;
            ROUND_NUM) ROUND_NUM="$_value" ;;
            ROUND_CURSOR) ROUND_NUM="$_value" ;;
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
CODEX_PRESENT=""
CURSOR_PRESENT=""
TIMEOUT="1860"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --codex-present)
            [[ $# -ge 2 ]] || fail '--codex-present requires a value'
            CODEX_PRESENT="$2"
            shift 2
            ;;
        --cursor-present)
            [[ $# -ge 2 ]] || fail '--cursor-present requires a value'
            CURSOR_PRESENT="$2"
            shift 2
            ;;
        --timeout)
            [[ $# -ge 2 ]] || fail '--timeout requires a value'
            TIMEOUT="$2"
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

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }
[[ -n "$CODEX_PRESENT" ]] || fail '--codex-present is required'
[[ -n "$CURSOR_PRESENT" ]] || fail '--cursor-present is required'
[[ -d "$DESIGN_TMPDIR_ARG" ]] || fail "design tmpdir not a directory: $DESIGN_TMPDIR_ARG"
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR

SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

SNAPSHOT_SH="${LARCH_SNAPSHOT_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh}"
ASSESS_SH="${LARCH_ASSESS_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/assess-plan-round.sh}"

RESULT_ENV="$DESIGN_TMPDIR/.step3.6-assessor.env"
RUN_PARAMS_PATH="$DESIGN_TMPDIR/run-params.json"
_WORKFLOW_RAW="$(json_scalar_or_sed "$RUN_PARAMS_PATH" workflow_path "")"
_DESIGN_CLASSIFICATION="$(json_scalar_or_sed "$RUN_PARAMS_PATH" design_classification "")"
WARN_LINES=()

if [[ -z "$_WORKFLOW_RAW" ]]; then
    if [[ "$_DESIGN_CLASSIFICATION" == HARD ]]; then
        WORKFLOW_PATH=HARD
    else
        WORKFLOW_PATH=SIMPLE
    fi
else
    WORKFLOW_PATH="$_WORKFLOW_RAW"
fi

if [[ -n "$_WORKFLOW_RAW" && -n "$_DESIGN_CLASSIFICATION" && "$_WORKFLOW_RAW" != "$_DESIGN_CLASSIFICATION" ]]; then
    WARN_LINES+=("**⚠ design-plan-quality-assessor: workflow_path=${_WORKFLOW_RAW} disagrees with design_classification=${_DESIGN_CLASSIFICATION}; aligning assessor lane to design_classification.**")
    WORKFLOW_PATH="$_DESIGN_CLASSIFICATION"
fi

ASSESSOR_STATUS=skipped
ASSESSOR_VERDICT=skipped
EFFECTIVE_ASSESSORS=0
ASSESSOR_VERDICT_FILE=""
ASSESSOR_VERDICT_ENV=""
ROUND_NUM=1

_write_result_and_emit() {
    local -a _kvs=()
    _kvs+=("ASSESSOR_STATUS=$ASSESSOR_STATUS")
    _kvs+=("ASSESSOR_VERDICT=$ASSESSOR_VERDICT")
    _kvs+=("EFFECTIVE_ASSESSORS=$EFFECTIVE_ASSESSORS")
    _kvs+=("ASSESSOR_VERDICT_FILE=$ASSESSOR_VERDICT_FILE")
    _kvs+=("ASSESSOR_VERDICT_ENV=$ASSESSOR_VERDICT_ENV")
    _kvs+=("ROUND_NUM=$ROUND_NUM")
    _kvs+=("WORKFLOW_PATH=$WORKFLOW_PATH")
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        _kvs+=("WARN=$_warn")
    done
    if ! phase_driver_write_result_env "$RESULT_ENV" "${_kvs[@]}"; then
        WARN_LINES+=("**⚠ design-plan-quality-assessor: result env write failed; using stdout fallback.**")
        if [[ ! -L "$RESULT_ENV" ]]; then
            rm -f "$RESULT_ENV" || true
        fi
    fi
    emit_kv ASSESSOR_STATUS "$ASSESSOR_STATUS"
    emit_kv ASSESSOR_VERDICT "$ASSESSOR_VERDICT"
    emit_kv EFFECTIVE_ASSESSORS "$EFFECTIVE_ASSESSORS"
    emit_kv ASSESSOR_VERDICT_FILE "$ASSESSOR_VERDICT_FILE"
    emit_kv ASSESSOR_VERDICT_ENV "$ASSESSOR_VERDICT_ENV"
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv WORKFLOW_PATH "$WORKFLOW_PATH"
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        emit_kv WARN "$_warn"
    done
}

_assessor_resolve_issue() {
    local _issue="${ISSUE_NUMBER:-}"
    if [[ -z "$_issue" && -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
        _issue=$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+ISSUE_NUMBER=/ {v=$0; sub(/^export[[:space:]]+ISSUE_NUMBER=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
    fi
    printf '%s\n' "$_issue"
}

_assessor_pause_checkpoint() {
    if [[ -f "$DESIGN_TMPDIR/.pause-requested" ]]; then
        local _issue
        _issue="$(_assessor_resolve_issue)"
        [[ -n "$_issue" ]] || fail 'pause requested but ISSUE_NUMBER could not be resolved'
        ASSESSOR_STATUS=skipped
        ASSESSOR_VERDICT=skipped
        EFFECTIVE_ASSESSORS=0
        _write_result_and_emit
        exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$_issue"
    fi
}

_read_round_cursor() {
    set +e
    local _cursor_out
    _cursor_out=$("$SNAPSHOT_SH" read-cursor --design-tmpdir "$DESIGN_TMPDIR" 2>&1)
    local _cursor_rc=$?
    set -e
    ROUND_NUM=1
    if [[ "$_cursor_rc" -eq 0 ]]; then
        parse_kv_from_output "$_cursor_out"
    else
        WARN_LINES+=("**⚠ design-plan-quality-assessor: snapshot read-cursor failed (exit ${_cursor_rc}); using ROUND_NUM=1.**")
        set +e
        _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-read-cursor.XXXXXX")
        printf '%s\n' "$_cursor_out" >"$_cap" 2>/dev/null || true
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 3.6" \
            --tool "snapshot-plan-round.sh read-cursor" \
            --exit-code "$_cursor_rc" \
            --category Warnings \
            --redact \
            --output-file "$_cap" \
            >/dev/null 2>&1 || true
        rm -f "$_cap" 2>/dev/null || true
        set -e
    fi
}

_assessor_pause_checkpoint

if [[ "$WORKFLOW_PATH" != HARD ]]; then
    _read_round_cursor
    ASSESSOR_STATUS=skipped
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    _write_result_and_emit
    exit 0
fi

_read_round_cursor

_assessor_pause_checkpoint

set +e
_snap_out=$("$SNAPSHOT_SH" write-after --design-tmpdir "$DESIGN_TMPDIR" --round "$ROUND_NUM" 2>&1)
_snap_rc=$?
set -e

if [[ "$_snap_rc" -ne 0 ]]; then
    local_warn="**⚠ 3.6: failed to snapshot post-Gate-B plan for round ${ROUND_NUM}; rolling back pending review-round state and skipping assessor.**"
    WARN_LINES+=("$local_warn")
    set +e
    _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-write-after.XXXXXX")
    printf 'round=%s\n' "${ROUND_NUM}" >"$_cap" 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 3.6" \
        --tool "snapshot-plan-round.sh write-after" \
        --exit-code "$_snap_rc" \
        --category Warnings \
        --redact \
        --output-file "$_cap" \
        >/dev/null 2>&1 || true
    rm -f "$_cap" 2>/dev/null || true
    if [[ "${ROUND_NUM:-0}" -ge 1 ]]; then
        printf '%s\n' "$((ROUND_NUM - 1))" >"$DESIGN_TMPDIR/review-round-count.txt" 2>/dev/null || true
        "$SNAPSHOT_SH" write-cursor --design-tmpdir "$DESIGN_TMPDIR" --value "$ROUND_NUM" >/dev/null 2>&1
        _rollback_rc=$?
        if [[ "$_rollback_rc" -ne 0 ]]; then
            WARN_LINES+=("**⚠ design-plan-quality-assessor: write-cursor rollback failed (exit ${_rollback_rc}); review-round count may be inconsistent.**")
        fi
    fi
    set -e
    ASSESSOR_STATUS=write-after-failed
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    _write_result_and_emit
    exit 0
fi

_assessor_pause_checkpoint

ASSESSOR_STATUS=""
ASSESSOR_VERDICT=""
EFFECTIVE_ASSESSORS=""
ASSESSOR_VERDICT_FILE=""
ASSESSOR_VERDICT_ENV=""

set +e
_assess_out=$("$ASSESS_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --timeout "$TIMEOUT" 2>&1)
_assess_rc=$?
set -e

if [[ "$_assess_rc" -ne 0 ]]; then
    WARN_LINES+=("**⚠ design-plan-quality-assessor: assess-plan-round.sh failed (exit ${_assess_rc}); settling as assess-failed.**")
    set +e
    _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-assess.XXXXXX")
    printf '%s\n' "$_assess_out" >"$_cap" 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 3.6" \
        --tool "assess-plan-round.sh" \
        --exit-code "$_assess_rc" \
        --category Warnings \
        --redact \
        --output-file "$_cap" \
        >/dev/null 2>&1 || true
    rm -f "$_cap" 2>/dev/null || true
    set -e
    ASSESSOR_STATUS=assess-failed
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    ASSESSOR_VERDICT_FILE=""
    ASSESSOR_VERDICT_ENV=""
    _write_result_and_emit
    exit 0
fi

parse_kv_from_output "$_assess_out"

if [[ -z "$ASSESSOR_STATUS" ]]; then
    WARN_LINES+=("**⚠ design-plan-quality-assessor: assess-plan-round.sh exited 0 but ASSESSOR_STATUS missing; settling as assess-failed.**")
    set +e
    _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-assess-empty.XXXXXX")
    printf '%s\n' "$_assess_out" >"$_cap" 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 3.6" \
        --tool "assess-plan-round.sh" \
        --exit-code 0 \
        --category Warnings \
        --redact \
        --output-file "$_cap" \
        >/dev/null 2>&1 || true
    rm -f "$_cap" 2>/dev/null || true
    set -e
    ASSESSOR_STATUS=assess-failed
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    ASSESSOR_VERDICT_FILE=""
    ASSESSOR_VERDICT_ENV=""
    _write_result_and_emit
    exit 0
fi

[[ -n "$ASSESSOR_VERDICT" ]] || ASSESSOR_VERDICT=skipped
[[ -n "$EFFECTIVE_ASSESSORS" ]] || EFFECTIVE_ASSESSORS=0

if [[ "$ASSESSOR_VERDICT" == not-worse && "${EFFECTIVE_ASSESSORS:-0}" == 0 ]]; then
    WARN_LINES+=("**⚠ 3.6: 0/3 effective assessors; proceeding without quality gate (round ${ROUND_NUM}, see ${ASSESSOR_VERDICT_ENV:-?}).**")
fi

_write_result_and_emit
exit 0
