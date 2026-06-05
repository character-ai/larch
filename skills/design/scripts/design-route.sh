#!/usr/bin/env bash
# design-route.sh — /design Step 0b pre-gate phase driver (resume, title, reentry, ROUTE).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "design-route.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-route.sh --design-tmpdir PATH --issue N --issue-title STR --issue-body-file PATH --has-clarify-label true|false --claude-pid N --session-id STR [--repo OWNER/REPO]'
}

MARK_START='^[[:space:]]*<!--[[:space:]]+larch:plan:start[[:space:]]+-->[[:space:]]*$'
MARK_END='^[[:space:]]*<!--[[:space:]]+larch:plan:end[[:space:]]+-->[[:space:]]*$'
PAUSE_MARK_START='^[[:space:]]*<!--[[:space:]]+larch:design-pause:start[[:space:]]+-->[[:space:]]*$'

pause_marker_present() {
    local body_file="$1"
    grep -q -E "$PAUSE_MARK_START" "$body_file" 2>/dev/null
}

validate_plain_scalar() {
    local label="$1" value="$2"
    case "$value" in
        '' | *$'\n'* | *$'\r'*) fail "invalid $label" ;;
    esac
}

validate_session_id_arg() {
    local value="$1"
    case "$value" in
        *$'\n'* | *$'\r'*) fail 'invalid --session-id' ;;
    esac
}

validate_repo() {
    local value="$1"
    case "$value" in
        '' | --* | *$'\n'* | *$'\r'* | /* | *../* | *\\*) fail 'invalid --repo' ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || fail 'invalid --repo'
}

plan_block_present() {
    local body_file="$1"
    local start_count=0 end_count=0 start_line end_line
    start_count=$(grep -c -E "$MARK_START" "$body_file" 2>/dev/null) || start_count=0
    end_count=$(grep -c -E "$MARK_END" "$body_file" 2>/dev/null) || end_count=0
    if [[ "$start_count" -eq 0 && "$end_count" -eq 0 ]]; then
        return 1
    fi
    if [[ "$start_count" -gt 1 || "$end_count" -gt 1 ]]; then
        return 1
    fi
    if [[ "$start_count" -eq 1 && "$end_count" -eq 0 ]]; then
        return 1
    fi
    if [[ "$start_count" -eq 0 && "$end_count" -eq 1 ]]; then
        return 1
    fi
    start_line=$(grep -n -E "$MARK_START" "$body_file" | head -1 | cut -d: -f1)
    end_line=$(grep -n -E "$MARK_END" "$body_file" | head -1 | cut -d: -f1)
    [[ "$end_line" -ge "$start_line" ]] || return 1
    return 0
}

DESIGN_TMPDIR_ARG=""
ISSUE=""
ISSUE_TITLE=""
ISSUE_BODY_FILE=""
HAS_CLARIFY_LABEL=""
CLAUDE_PID=""
SESSION_ID_ARG=""
SESSION_ID_ARG_SEEN=false
REPO=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --issue)
            [[ $# -ge 2 ]] || fail '--issue requires a value'
            ISSUE="$2"
            shift 2
            ;;
        --issue-title)
            [[ $# -ge 2 ]] || fail '--issue-title requires a value'
            ISSUE_TITLE="$2"
            shift 2
            ;;
        --issue-body-file)
            [[ $# -ge 2 ]] || fail '--issue-body-file requires a value'
            ISSUE_BODY_FILE="$2"
            shift 2
            ;;
        --has-clarify-label)
            [[ $# -ge 2 ]] || fail '--has-clarify-label requires a value'
            HAS_CLARIFY_LABEL="$2"
            shift 2
            ;;
        --claude-pid)
            [[ $# -ge 2 ]] || fail '--claude-pid requires a value'
            CLAUDE_PID="$2"
            shift 2
            ;;
        --session-id)
            [[ $# -ge 2 ]] || fail '--session-id requires a value'
            SESSION_ID_ARG="$2"
            SESSION_ID_ARG_SEEN=true
            shift 2
            ;;
        --repo)
            [[ $# -ge 2 ]] || fail '--repo requires a value'
            REPO="$2"
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
[[ -n "$ISSUE" ]] || { usage; fail '--issue is required'; }
[[ -n "$ISSUE_TITLE" ]] || { usage; fail '--issue-title is required'; }
[[ -n "$ISSUE_BODY_FILE" ]] || { usage; fail '--issue-body-file is required'; }
[[ -n "$HAS_CLARIFY_LABEL" ]] || { usage; fail '--has-clarify-label is required'; }
[[ -n "$CLAUDE_PID" ]] || { usage; fail '--claude-pid is required'; }
[[ "$SESSION_ID_ARG_SEEN" == true ]] || { usage; fail '--session-id is required'; }

case "$ISSUE" in
    '' | *[!0-9]*) fail '--issue must be a positive integer' ;;
esac
[[ "$ISSUE" != "0" ]] || fail '--issue must be a positive integer'
case "$HAS_CLARIFY_LABEL" in
    true | false) ;;
    *) fail '--has-clarify-label must be true or false' ;;
esac
case "$CLAUDE_PID" in
    '' | *[!0-9]*) fail '--claude-pid must be a positive integer' ;;
esac

validate_plain_scalar issue-title "$ISSUE_TITLE"
validate_session_id_arg "$SESSION_ID_ARG"
[[ -n "$REPO" ]] && validate_repo "$REPO"

if [[ -L "$ISSUE_BODY_FILE" ]] || [[ ! -f "$ISSUE_BODY_FILE" ]] || [[ ! -r "$ISSUE_BODY_FILE" ]]; then
    fail 'issue-body-file must be a readable regular file'
fi

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR
SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

RESULT_ENV="$DESIGN_TMPDIR/.design-route-result.env"
ROUTE=""
BRAINSTORM_PREFIX=false
TITLE_FILTER_REASON=""
TITLE_FILTER_MARKER=""
MARKER_AGE=""
MARKER_TTL=""
MARKER_REMAINING=0
DESIGN_REENTRY_MARKER_PATH=""
SUMMARY_MODE_STRING=N/A
RESUME_STEP=""
SESSION_ID=""
RUN_ID=""
TIER=""
BRAINSTORM_DONE=""
WARN_LINES=()
ERROR_LINES=()

ROUTE_KVS=()

route_build_kvs() {
    ROUTE_KVS=("ROUTE=$ROUTE" "BRAINSTORM_PREFIX=$BRAINSTORM_PREFIX")
    [[ -n "$TITLE_FILTER_REASON" ]] && ROUTE_KVS+=("TITLE_FILTER_REASON=$TITLE_FILTER_REASON")
    [[ -n "$TITLE_FILTER_MARKER" ]] && ROUTE_KVS+=("TITLE_FILTER_MARKER=$TITLE_FILTER_MARKER")
    [[ -n "$MARKER_AGE" ]] && ROUTE_KVS+=("MARKER_AGE=$MARKER_AGE")
    [[ -n "$MARKER_TTL" ]] && ROUTE_KVS+=("MARKER_TTL=$MARKER_TTL")
    [[ -n "$DESIGN_REENTRY_MARKER_PATH" ]] && ROUTE_KVS+=("DESIGN_REENTRY_MARKER_PATH=$DESIGN_REENTRY_MARKER_PATH")
    [[ -n "$RESUME_STEP" ]] && ROUTE_KVS+=("RESUME_STEP=$RESUME_STEP")
    [[ -n "$SESSION_ID" ]] && ROUTE_KVS+=("SESSION_ID=$SESSION_ID")
    [[ -n "$RUN_ID" ]] && ROUTE_KVS+=("RUN_ID=$RUN_ID")
    [[ -n "$TIER" ]] && ROUTE_KVS+=("TIER=$TIER")
    [[ -n "$BRAINSTORM_DONE" ]] && ROUTE_KVS+=("BRAINSTORM_DONE=$BRAINSTORM_DONE")
    local w e
    for w in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        ROUTE_KVS+=("WARN=$w")
    done
    for e in "${ERROR_LINES[@]+"${ERROR_LINES[@]}"}"; do
        ROUTE_KVS+=("ERROR=$e")
    done
}

route_write_result_env() {
    route_build_kvs
    if ! phase_driver_write_result_env "$RESULT_ENV" "${ROUTE_KVS[@]}"; then
        exit 1
    fi
}

route_emit_stdout_and_exit() {
    local kv
    for kv in "${ROUTE_KVS[@]}"; do
        emit_kv "${kv%%=*}" "${kv#*=}"
    done
    exit 0
}

emit_route_result() {
    route_write_result_env
    route_emit_stdout_and_exit
}

render_cancel_summary() {
    local outcome="$1" mode="$2"
    set +e
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        DESIGN_TMPDIR="$DESIGN_TMPDIR" ISSUE_NUMBER="$ISSUE" SESSION_ID="$SESSION_ID_ARG" \
            "$PLUGIN_ROOT/skills/design/scripts/render-final-summary.sh" \
            --outcome "$outcome" \
            --mode "$mode" \
            ${REPO:+--repo "$REPO"} \
            --post-publish-only >/dev/null 2>&4
    else
        DESIGN_TMPDIR="$DESIGN_TMPDIR" ISSUE_NUMBER="$ISSUE" SESSION_ID="$SESSION_ID_ARG" \
            "$PLUGIN_ROOT/skills/design/scripts/render-final-summary.sh" \
            --outcome "$outcome" \
            --mode "$mode" \
            ${REPO:+--repo "$REPO"} \
            --post-publish-only >/dev/null
    fi
    # Render failure is intentionally tolerated; child diagnostics stay on stderr/FD4.
    set -e
    return 0
}

route_emit_cancel_side_effects() {
    case "$ROUTE" in
        cancel-title-filter)
            if [[ "$TITLE_FILTER_REASON" == lifecycle ]]; then
                larch_err "**⚠ /design: issue title starts with managed lifecycle marker ${TITLE_FILTER_MARKER:-<token>} — refusing to design. Rename the title (drop the bracket prefix) and re-invoke /design.**"
            else
                # shellcheck disable=SC2016 # Markdown code spans are literal in this diagnostic.
                larch_err '**⚠ /design: issue title matches archival report-prefix `[... Report]` — refusing to design. Such titles are reserved for `/research` / `/report-tokens` artifacts. Rename the title and re-invoke /design.**'
            fi
            render_cancel_summary cancelled-title-filter N/A
            ;;
        cancel-reentry-guard)
            larch_errf '**⚠ /design: refusing spurious re-entry — guard=session-cache issue=#%s ppid=%s marker_age=%ss ttl=%ss. Wait %ss or delete %s to override.**\n' \
                "$ISSUE" "$CLAUDE_PID" "$MARKER_AGE" "$MARKER_TTL" "$MARKER_REMAINING" "$DESIGN_REENTRY_MARKER_PATH"
            render_cancel_summary cancelled-reentry-guard "$SUMMARY_MODE_STRING"
            ;;
    esac
}

emit_cancel_route_result() {
    route_write_result_env
    route_emit_cancel_side_effects
    route_emit_stdout_and_exit
}

step_registry_present() {
    [[ -f "$PLUGIN_ROOT/skills/design/scripts/step-name-registry.tsv" ]]
}

step_is_registered() {
    local step="$1" registry="$PLUGIN_ROOT/skills/design/scripts/step-name-registry.tsv"
    step_registry_present || return 2
    awk -F '\t' -v step="$step" 'NR > 1 && $1 == step { found=1; exit } END { exit found ? 0 : 1 }' "$registry"
}

# 1. Resume detection
if pause_marker_present "$ISSUE_BODY_FILE"; then
    set +e
    _pause_out=$("$PLUGIN_ROOT/scripts/design-pause-load.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"})
    _pause_rc=$?
    set -e
    _load_ok=false
    _step=""
    while IFS= read -r _pline || [[ -n "$_pline" ]]; do
        _pkey="${_pline%%=*}"
        _pval="${_pline#*=}"
        case "$_pkey" in
            LOAD_OK) _load_ok="$_pval" ;;
            STEP) _step="$_pval" ;;
            SESSION_ID) SESSION_ID="$_pval" ;;
            RUN_ID) RUN_ID="$_pval" ;;
            TIER) TIER="$_pval" ;;
            BRAINSTORM_DONE) BRAINSTORM_DONE="$_pval" ;;
            WARN) WARN_LINES+=("$_pval") ;;
            ERROR) ERROR_LINES+=("$_pval") ;;
        esac
    done <<<"${_pause_out:-}"
    if [[ "${_pause_rc:-0}" -ne 0 ]]; then
        ERROR_LINES+=("design-pause-load-failed")
        _load_ok=false
    fi
    if [[ "$_load_ok" == true && -n "$_step" ]]; then
        _step_reg_rc=0
        step_is_registered "$_step" || _step_reg_rc=$?
        if [[ "$_step_reg_rc" -eq 0 ]]; then
            _manual_resume=false
            if [[ -f "$DESIGN_TMPDIR/run-params.json" ]] && command -v jq >/dev/null 2>&1; then
                [[ "$(jq -r '.manual_gate_b // false' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo false)" == true ]] && _manual_resume=true
            fi
            _wdce_resume_args=(
                "$PLUGIN_ROOT/scripts/write-design-current-env.sh"
                --output "$DESIGN_TMPDIR/source-env.sh"
                --design-tmpdir "$DESIGN_TMPDIR"
                --session-id "$SESSION_ID"
                --issue-number "$ISSUE"
                --claude-pid "$CLAUDE_PID"
            )
            [[ -n "$REPO" ]] && _wdce_resume_args+=(--repo "$REPO")
            [[ "$_manual_resume" == true ]] && _wdce_resume_args+=(--manual-requested true)
            _wdce_resume_rc=0
            set +e
            if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
                "${_wdce_resume_args[@]}" >/dev/null 2>&4
            else
                "${_wdce_resume_args[@]}" >/dev/null
            fi
            _wdce_resume_rc=$?
            set -e
            if [[ "${_wdce_resume_rc:-0}" -ne 0 ]]; then
                larch_err "**⚠ /design: resume env refresh failed via write-design-current-env.sh (exit ${_wdce_resume_rc}); aborting before resumed STEP=${_step}. Inspect source-env.sh / write-design-current-env.sh diagnostics and re-invoke /design.**"
                exit 1
            fi
            ROUTE="resume@${_step}"
            RESUME_STEP="$_step"
            emit_route_result
        fi
        if [[ "$_step_reg_rc" -eq 2 ]]; then
            fail "step-name-registry.tsv missing"
        fi
        ERROR_LINES+=("pause-load-invalid-step")
        ROUTE=cancel-pause-load
        emit_route_result
    fi
    if [[ "$_load_ok" == true ]]; then
        ERROR_LINES+=("pause-load-missing-step")
        ROUTE=cancel-pause-load
        emit_route_result
    fi
fi

# 2. Title-eligibility
# shellcheck source=scripts/lib-title-eligibility.sh
source "$PLUGIN_ROOT/scripts/lib-title-eligibility.sh"
_lifecycle_marker=""
if _lifecycle_marker=$(title_has_lifecycle_reject_prefix "$ISSUE_TITLE" 2>/dev/null); then
    ROUTE=cancel-title-filter
    TITLE_FILTER_REASON=lifecycle
    TITLE_FILTER_MARKER="$_lifecycle_marker"
    emit_cancel_route_result
fi
if title_has_archival_report_prefix "$ISSUE_TITLE"; then
    ROUTE=cancel-title-filter
    TITLE_FILTER_REASON=archival
    emit_cancel_route_result
fi
if title_starts_with_brainstorm "$ISSUE_TITLE"; then
    BRAINSTORM_PREFIX=true
fi

# 3. Re-entry guard
# shellcheck source=scripts/lib-design-reentry-guard.sh
source "$PLUGIN_ROOT/scripts/lib-design-reentry-guard.sh"
_reentry_rc=0
_reentry_out=""
set +e
_reentry_out="$(design_reentry_marker_hit "$ISSUE" "$CLAUDE_PID" 2>&1)"
_reentry_rc=$?
set -e
if [[ "$_reentry_rc" -eq 2 ]]; then
    while IFS= read -r _rline || [[ -n "$_rline" ]]; do
        [[ -n "$_rline" ]] && WARN_LINES+=("reentry-guard: $_rline")
    done <<<"${_reentry_out:-}"
fi
_marker_hit=false
for _rkv in $_reentry_out; do
    case "$_rkv" in
        MARKER_HIT=*) _marker_hit="${_rkv#MARKER_HIT=}" ;;
        MARKER_AGE=*) MARKER_AGE="${_rkv#MARKER_AGE=}" ;;
        MARKER_TTL=*) MARKER_TTL="${_rkv#MARKER_TTL=}" ;;
    esac
done
if [[ "$_marker_hit" == true ]]; then
    ROUTE=cancel-reentry-guard
    DESIGN_REENTRY_MARKER_PATH="$(design_reentry_marker_path "$ISSUE" "$CLAUDE_PID" 2>/dev/null || true)"
    [[ "$MARKER_AGE" =~ ^[0-9]+$ ]] || MARKER_AGE=0
    [[ "$MARKER_TTL" =~ ^[0-9]+$ ]] || MARKER_TTL=300
    MARKER_REMAINING=$((MARKER_TTL - MARKER_AGE))
    [[ "$MARKER_REMAINING" -lt 0 ]] && MARKER_REMAINING=0
    SUMMARY_MODE_STRING=N/A
    if [[ -f "$DESIGN_TMPDIR/run-params.json" ]] && command -v jq >/dev/null 2>&1; then
        SUMMARY_MODE_STRING="$(jq -r '.design_classification // "N/A"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo N/A)"
    fi
    [[ -n "$SUMMARY_MODE_STRING" ]] || SUMMARY_MODE_STRING=N/A
    emit_cancel_route_result
fi

# 4. Verdict
if [[ "$HAS_CLARIFY_LABEL" == true ]]; then
    ROUTE=clarify
elif plan_block_present "$ISSUE_BODY_FILE"; then
    ROUTE=already-planned
else
    ROUTE=proceed
fi
emit_route_result
