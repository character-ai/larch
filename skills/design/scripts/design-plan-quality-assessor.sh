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
        if [[ "$_value" == *$'\n'* || "$_value" == *$'\r'* ]]; then
            continue
        fi
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

_ROUND_CURSOR_READ_FAILED=false

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
TRAILER_MARKER='LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN'
WARN_LINES=()

READ_CLASSIFICATION_SH="$PLUGIN_ROOT/scripts/read-design-classification.sh"
if [[ -x "$READ_CLASSIFICATION_SH" ]]; then
    _class_cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-classification-stderr.XXXXXX")
    DESIGN_CLASSIFICATION=$("$READ_CLASSIFICATION_SH" "$RUN_PARAMS_PATH" 2>"$_class_cap" || printf '%s\n' HARD)
    if [[ -s "$_class_cap" ]]; then
        while IFS= read -r _class_warn || [[ -n "$_class_warn" ]]; do
            [[ -n "$_class_warn" ]] && WARN_LINES+=("$_class_warn")
        done <"$_class_cap"
    fi
    rm -f "$_class_cap" 2>/dev/null || true
else
    DESIGN_CLASSIFICATION=HARD
    WARN_LINES+=("**⚠ design-plan-quality-assessor: read-design-classification.sh not executable; defaulting to HARD.**")
fi
case "$DESIGN_CLASSIFICATION" in
    SIMPLE|HARD) ;;
    *) DESIGN_CLASSIFICATION=HARD ;;
esac
WORKFLOW_PATH="$DESIGN_CLASSIFICATION"
_WORKFLOW_RAW="$(json_scalar_or_sed "$RUN_PARAMS_PATH" workflow_path "")"
if [[ -n "$_WORKFLOW_RAW" && "$_WORKFLOW_RAW" != "$DESIGN_CLASSIFICATION" ]]; then
    WARN_LINES+=("**⚠ design-plan-quality-assessor: workflow_path=${_WORKFLOW_RAW} disagrees with design_classification=${DESIGN_CLASSIFICATION}; aligning assessor lane to design_classification.**")
fi

ASSESSOR_STATUS=skipped
ASSESSOR_VERDICT=skipped
EFFECTIVE_ASSESSORS=0
ASSESSOR_VERDICT_FILE=""
ASSESSOR_VERDICT_ENV=""
ROUND_NUM=1

_write_result_env() {
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
        WARN_LINES+=("**⚠ design-plan-quality-assessor: result env write failed; continuing with display-only output.**")
        if [[ ! -L "$RESULT_ENV" ]]; then
            rm -f "$RESULT_ENV" || true
        fi
        return 1
    fi
    return 0
}

_emit_warn_lines() {
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        emit "$_warn"
    done
}

_neutralize_assessor_display_line() {
    local line="$1"
    line=$(printf '%s' "$line" | sanitize_diagnostic_line)
    if [[ "$line" == "$TRAILER_MARKER" || "$line" =~ ^LARCH_ASSESSOR_[A-Z0-9_]*= ]]; then
        printf '[untrusted assessor display] %s\n' "$line"
    else
        printf '%s\n' "$line"
    fi
}

_read_fixed_env_value() {
    local file="$1" key="$2"
    [[ -f "$file" && ! -L "$file" ]] || return 0
    awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true
}

_confine_assessor_file_path() {
    local label="$1" path="$2" parent base canon_parent canon_path
    _CONFINED_ASSESSOR_PATH=""
    [[ -n "$path" ]] || return 0
    if [[ ! -f "$path" || -L "$path" ]]; then
        WARN_LINES+=("**⚠ design-plan-quality-assessor: ignoring unsafe ${label} path outside DESIGN_TMPDIR.**")
        return 1
    fi
    parent="${path%/*}"
    base="${path##*/}"
    [[ -n "$parent" && "$parent" != "$path" ]] || parent="."
    canon_parent="$(cd "$parent" 2>/dev/null && pwd -P)" || {
        WARN_LINES+=("**⚠ design-plan-quality-assessor: ignoring unsafe ${label} path outside DESIGN_TMPDIR.**")
        return 1
    }
    canon_path="$canon_parent/$base"
    case "$canon_path" in
        "$DESIGN_TMPDIR"/*) _CONFINED_ASSESSOR_PATH="$canon_path" ;;
        *)
            WARN_LINES+=("**⚠ design-plan-quality-assessor: ignoring unsafe ${label} path outside DESIGN_TMPDIR.**")
            return 1
            ;;
    esac
}

_confine_assessor_output_paths() {
    _CONFINED_ASSESSOR_PATH=""
    if [[ -n "${ASSESSOR_VERDICT_FILE:-}" ]]; then
        _confine_assessor_file_path ASSESSOR_VERDICT_FILE "$ASSESSOR_VERDICT_FILE" || true
        ASSESSOR_VERDICT_FILE="$_CONFINED_ASSESSOR_PATH"
    fi
    if [[ -n "${ASSESSOR_VERDICT_ENV:-}" ]]; then
        _confine_assessor_file_path ASSESSOR_VERDICT_ENV "$ASSESSOR_VERDICT_ENV" || true
        ASSESSOR_VERDICT_ENV="$_CONFINED_ASSESSOR_PATH"
    fi
}

_emit_worse_display() {
    emit "## Plan-Quality Assessor — WORSE majority (round ${ROUND_NUM})"
    local _headline="" _summary="" _line _count=0
    if [[ -n "${ASSESSOR_VERDICT_FILE:-}" && -f "$ASSESSOR_VERDICT_FILE" && ! -L "$ASSESSOR_VERDICT_FILE" ]]; then
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            [[ -n "$_line" ]] || continue
            _headline="$(_neutralize_assessor_display_line "$_line")"
            break
        done <"$ASSESSOR_VERDICT_FILE"
    fi
    [[ -n "$_headline" ]] || _headline="WORSE: assessor majority found the revised plan worse than the prior round."
    emit "$_headline"
    _summary="$(_read_fixed_env_value "${ASSESSOR_VERDICT_ENV:-}" QUALIFICATIONS_SUMMARY)"
    if [[ -n "$_summary" ]]; then
        emit "Untrusted assessor notes:"
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            _count=$((_count + 1))
            [[ "$_count" -le 20 ]] || break
            _line="$(_neutralize_assessor_display_line "$_line")"
            [[ ${#_line} -le 400 ]] || _line="${_line:0:400}…"
            emit "$_line"
        done <<<"$_summary"
    fi
}

_emit_trailer_frame() {
    emit "$TRAILER_MARKER"
    emit "LARCH_ASSESSOR_ROUND_NUM=${ROUND_NUM}"
    if [[ -n "${ASSESSOR_VERDICT_ENV:-}" ]]; then
        local _token
        _token="$(_read_fixed_env_value "$ASSESSOR_VERDICT_ENV" ASSESSOR_RESULT_TOKEN)"
        if [[ "$_token" =~ ^[A-Za-z0-9_.:-]+$ ]]; then
            emit "LARCH_ASSESSOR_RESULT_TOKEN=$_token"
        fi
    fi
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
        ASSESSOR_STATUS=paused
        ASSESSOR_VERDICT=skipped
        EFFECTIVE_ASSESSORS=0
        _write_result_env || true
        emit "**⏸ /design Step 3.6: pause requested; saving design state.**"
        exit 11
    fi
}


_read_round_cursor() {
    set +e
    local _cursor_stdout _cap
    _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-read-cursor-stderr.XXXXXX")
    _cursor_stdout=$("$SNAPSHOT_SH" read-cursor --design-tmpdir "$DESIGN_TMPDIR" 2>"$_cap")
    local _cursor_rc=$?
    set -e
    ROUND_NUM=1
    _ROUND_CURSOR_READ_FAILED=false
    if [[ "$_cursor_rc" -eq 0 ]]; then
        parse_kv_from_output "$_cursor_stdout"
    else
        _ROUND_CURSOR_READ_FAILED=true
        WARN_LINES+=("**⚠ design-plan-quality-assessor: snapshot read-cursor failed (exit ${_cursor_rc}); settling as cursor-read-failed.**")
        set +e
        {
            printf '%s\n' "$_cursor_stdout"
            cat "$_cap" 2>/dev/null || true
        } >"${_cap}.merged" 2>/dev/null || true
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 3.6" \
            --tool "snapshot-plan-round.sh read-cursor" \
            --exit-code "$_cursor_rc" \
            --category Warnings \
            --redact \
            --output-file "${_cap}.merged" \
            >/dev/null 2>&1 || true
        rm -f "${_cap}.merged" 2>/dev/null || true
        set -e
    fi
    rm -f "$_cap" 2>/dev/null || true
}

_assessor_pause_checkpoint

if [[ "$WORKFLOW_PATH" != HARD ]]; then
    _read_round_cursor
    ASSESSOR_STATUS=skipped
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    _assessor_pause_checkpoint
    _write_result_env || true
    exit 0
fi

emit "> **🔶 /design 3.6: assessor**"
_emit_warn_lines
_read_round_cursor

_assessor_pause_checkpoint

if [[ "$_ROUND_CURSOR_READ_FAILED" == true ]]; then
    ASSESSOR_STATUS=cursor-read-failed
    ASSESSOR_VERDICT=skipped
    EFFECTIVE_ASSESSORS=0
    _assessor_pause_checkpoint
    _write_result_env || true
    _emit_warn_lines
    exit 0
fi

set +e
_snap_cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-write-after-stderr.XXXXXX")
_snap_out=$("$SNAPSHOT_SH" write-after --design-tmpdir "$DESIGN_TMPDIR" --round "$ROUND_NUM" 2>"$_snap_cap")
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
    _assessor_pause_checkpoint
    _write_result_env || true
    _emit_warn_lines
    rm -f "$_snap_cap" 2>/dev/null || true
    exit 0
fi

rm -f "$_snap_cap" 2>/dev/null || true

_assessor_pause_checkpoint

ASSESSOR_STATUS=""
ASSESSOR_VERDICT=""
EFFECTIVE_ASSESSORS=""
ASSESSOR_VERDICT_FILE=""
ASSESSOR_VERDICT_ENV=""

set +e
_assess_cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-assess-stderr.XXXXXX")
_assess_out=$("$ASSESS_SH" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --timeout "$TIMEOUT" \
    --design-classification "$WORKFLOW_PATH" 2>"$_assess_cap")
_assess_rc=$?
set -e

if [[ "$_assess_rc" -ne 0 ]]; then
    WARN_LINES+=("**⚠ design-plan-quality-assessor: assess-plan-round.sh failed (exit ${_assess_rc}); settling as assess-failed.**")
    set +e
    _cap=$(mktemp "${TMPDIR:-/tmp}/design-step3.6-assess.XXXXXX")
    {
        printf '%s\n' "$_assess_out"
        cat "$_assess_cap" 2>/dev/null || true
    } >"$_cap" 2>/dev/null || true
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
    _assessor_pause_checkpoint
    _write_result_env || true
    _emit_warn_lines
    rm -f "$_assess_cap" 2>/dev/null || true
    exit 0
fi

parse_kv_from_output "$_assess_out"
rm -f "$_assess_cap" 2>/dev/null || true
_confine_assessor_output_paths

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
    _assessor_pause_checkpoint
    _write_result_env || true
    _emit_warn_lines
    exit 0
fi

[[ -n "$ASSESSOR_VERDICT" ]] || ASSESSOR_VERDICT=skipped
[[ -n "$EFFECTIVE_ASSESSORS" ]] || EFFECTIVE_ASSESSORS=0

if [[ "$ASSESSOR_VERDICT" == not-worse && "${EFFECTIVE_ASSESSORS:-0}" == 0 ]]; then
    WARN_LINES+=("**⚠ 3.6: 0/3 effective assessors; proceeding without quality gate (round ${ROUND_NUM}, see ${ASSESSOR_VERDICT_ENV:-?}).**")
fi

_assessor_pause_checkpoint
_write_result_env || true
if [[ "$ASSESSOR_STATUS" == ok && "$ASSESSOR_VERDICT" == worse-majority && "${EFFECTIVE_ASSESSORS:-0}" =~ ^[0-9]+$ && "${EFFECTIVE_ASSESSORS:-0}" -ge 1 ]]; then
    _emit_warn_lines
    _emit_worse_display
    _emit_trailer_frame
    exit 10
fi
_emit_warn_lines
exit 0
