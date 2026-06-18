# shellcheck shell=bash
# Shared Step 3 panel-init-failed prelaunch helpers (sourced only; no shebang).

if [[ "${LARCH_LIB_STEP3_PRELAUNCH_FAILURE_LOADED:-}" == "1" ]]; then
    # shellcheck disable=SC2317
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_STEP3_PRELAUNCH_FAILURE_LOADED=1

_step3_review_write_terminal_sentinels() {
  mkdir -p "$DESIGN_TMPDIR/.completed" 2>/dev/null || return 0
  rm -f "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
  : >"$DESIGN_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
  : >"$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
}

_step3_review_write_result_env() {
    local _status="${1:-panel-init-failed}"
    local _reason="${2:-prelaunch-failure}"
    local _rounds="${3:-0}"
    local _result_env="$DESIGN_TMPDIR/.step3-review-result.env"
    local _tmp=""
    rm -f "$_result_env" 2>/dev/null || true
    _tmp="$(mktemp "$DESIGN_TMPDIR/.step3-review-result.env.XXXXXX" 2>/dev/null || true)"
    if [[ -n "$_tmp" ]]; then
        if {
            printf 'STEP3_REVIEW_LOOP_STATUS=%s\n' "$_status"
            printf 'LOOP_STATUS=%s\n' "$_status"
            printf 'REASON=%s\n' "$_reason"
            printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "$_status"
            printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
            printf '%s\n' 'STEP3_REVIEW_ROUND_NUM='
            printf '%s\n' 'ROUND_NUM='
            printf 'ROUNDS_COMPLETED=%s\n' "$_rounds"
            printf 'REVIEW_ROUND_COUNT=%s\n' "$_rounds"
        } >"$_tmp"; then
            mv "$_tmp" "$_result_env" 2>/dev/null || {
                rm -f "$_tmp" "$_result_env" 2>/dev/null || true
            }
            if [[ -f "$_result_env" && ! -L "$_result_env" && -r "$_result_env" ]]; then
                _step3_review_write_terminal_sentinels
            fi
        else
            rm -f "$_tmp" "$_result_env" 2>/dev/null || true
        fi
    fi
}

_step3_review_emit_prelaunch_stdout() {
    local _status="${1:-panel-init-failed}"
    local _reason="${2:-prelaunch-failure}"
    local _rounds="${3:-0}"
    printf 'STEP3_REVIEW_LOOP_STATUS=%s\n' "$_status"
    printf 'LOOP_STATUS=%s\n' "$_status"
    printf 'REASON=%s\n' "$_reason"
    printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "$_status"
    printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
    printf 'ROUNDS_COMPLETED=%s\n' "$_rounds"
    printf 'REVIEW_ROUND_COUNT=%s\n' "$_rounds"
}

_step3_review_write_prelaunch_failure() {
    local _status="${1:-panel-init-failed}"
    local _reason="${2:-prelaunch-failure}"
    local _rounds="${3:-0}"
    _step3_review_write_result_env "$_status" "$_reason" "$_rounds"
    _step3_review_emit_prelaunch_stdout "$_status" "$_reason" "$_rounds"
}

_step3_review_stage_panel_init_failed() {
    local _reason="${1:-panel-init-failed}"
    local _detail_log="$DESIGN_TMPDIR/step3-panel-init-failed.log"
    local _stage_helper="${CLAUDE_PLUGIN_ROOT:-}/skills/design/scripts/design-stage-terminal-state.sh"
    printf 'Step 3 panel initialization failed before any reviewers launched: %s\n' "$_reason" >"$_detail_log" 2>/dev/null || true
    [[ -x "$_stage_helper" ]] || return 0
    "$_stage_helper" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --outcome failed-judge-panel \
        --step judge-panel \
        --phase judge-panel \
        --site step3-review \
        --trigger panel-init-failed \
        --bail-reason panel-init-failed \
        --exit-code 1 \
        --source-script design-step3-review \
        --summary-outcome failed-judge-panel \
        --failure-detail-log "$_detail_log" >/dev/null 2>"$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log" || true
}

_step3_review_zero_round_coverage_missing() {
    local _rounds_dec="${1:-0}"
    local _r1="$DESIGN_TMPDIR/plan-review/round-1"
    if [[ "$_rounds_dec" -eq 0 ]]; then
        return 0
    fi
    [[ -d "$_r1" ]] || return 0
    [[ -z "$(find "$_r1" -mindepth 1 -maxdepth 1 -type f -print -quit 2>/dev/null)" ]] && return 0
    return 1
}

_step3_entry_panel_init_failed_exit() {
    local _reason="${1:-panel-init-failed}"
    _step3_review_write_prelaunch_failure panel-init-failed "$_reason"
    _step3_review_stage_panel_init_failed "$_reason"
    printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
    exit 1
}
