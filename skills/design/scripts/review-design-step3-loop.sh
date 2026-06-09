#!/usr/bin/env bash
# review-design-step3-loop.sh — absorbed /design Step 3 multi-round controller.
# Sourced by run-step3-review.sh after run_step3_round_body is defined. Bash 3.2.

# shellcheck disable=SC2034

step3_loop_now_s() {
    date +%s
}

step3_loop_phase_file() {
    printf '%s/.step3-round-%s.phase\n' "$DESIGN_TMPDIR" "$1"
}

step3_loop_write_phase() {
    local round_num="$1" phase="$2" phase_file tmp
    phase_file="$(step3_loop_phase_file "$round_num")"
    tmp="${phase_file}.tmp.$$"
    printf '%s\n' "$phase" >"$tmp"
    mv "$tmp" "$phase_file"
}

step3_loop_read_phase() {
    local round_num="$1" phase_file
    phase_file="$(step3_loop_phase_file "$round_num")"
    if [[ -f "$phase_file" ]]; then
        tr -d '[:space:]' <"$phase_file" 2>/dev/null || true
    fi
}

step3_loop_emit_envelope() {
    local status="$1" round_num="$2" rounds_completed="$3" final_round="$4"
    emit_kv STEP3_REVIEW_LOOP_STATUS "$status"
    emit_kv ROUNDS_COMPLETED "${rounds_completed:-0}"
    emit_kv FINAL_ROUND_NUM "${final_round:-$round_num}"
    emit_kv ACCEPTED_COUNT "${ACCEPTED_COUNT:-0}"
    emit_kv DEGRADED_PANEL "${DEGRADED_PANEL:-0}"
    [[ -z "${SCOPE_ANCHOR_FILE:-}" ]] || emit_kv SCOPE_ANCHOR_FILE "${SCOPE_ANCHOR_FILE:-}"
    emit_kv PLAN_REVIEW_CONTINUE_REASON "${PLAN_REVIEW_CONTINUE_REASON:-}"
    [[ -z "${POSTPLAN_RC:-}" ]] || emit_kv POSTPLAN_RC "${POSTPLAN_RC:-}"
    [[ -z "${DEDUP_RC:-}" ]] || emit_kv DEDUP_RC "${DEDUP_RC:-}"
    if [[ -f "$DESIGN_TMPDIR/.design-postplan-emit-result.env" && ! -L "$DESIGN_TMPDIR/.design-postplan-emit-result.env" ]]; then
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            case "$_line" in
                POSTPLAN_EMIT_STATUS=*|EMIT_PLAN_STATUS=*|DIFF_LINES=*|VALIDATE_STATUS=*|VALIDATE_DEFECT_COUNT=*|PLAN_SIZE_STATUS=*|HARD_TRIGGER_FIRED=*|TRIGGER_REASONS=*|PLAN_LINES=*|DIFF_ADDED=*|DIFF_DELETED=*|MECHANICAL_CHURN=*|SOFT_ADVISORY=*|PARTITION_REQUESTED=*|DRIFT_TRIGGER_FIRED=*|DRIFT_MULTIPLE=*|DRIFT_PLAN_RATIO=*|DRIFT_DIFF_RATIO=*|BASELINE_PLAN_LINES=*|BASELINE_DIFF_LINES=*)
                    printf '%s\n' "$_line"
                    ;;
            esac
        done <"$DESIGN_TMPDIR/.design-postplan-emit-result.env"
    fi
}

step3_loop_write_completed_step3() {
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : >"$DESIGN_TMPDIR/.completed/step-3"
}

step3_loop_count_accepted_findings() {
    if [[ -s "$DESIGN_TMPDIR/accepted-plan-findings.md" ]]; then
        grep -cE '^### FINDING_[0-9]+:' "$DESIGN_TMPDIR/accepted-plan-findings.md" 2>/dev/null || true
    else
        printf '0\n'
    fi
}

step3_loop_read_bool_param() {
    local key="$1" default_value="$2" value=""
    if command -v jq >/dev/null 2>&1 && [[ -f "$DESIGN_TMPDIR/run-params.json" ]]; then
        value="$(jq -r --arg key "$key" '.[$key] // empty' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || true)"
    fi
    if [[ -z "$value" && -f "$DESIGN_TMPDIR/run-params.json" ]]; then
        value="$(sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*\(true\|false\).*/\1/p' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null | head -1)"
    fi
    case "$value" in true|false) printf '%s\n' "$value" ;; *) printf '%s\n' "$default_value" ;; esac
}

step3_loop_record_timing() {
    local round_num="$1" start_s="$2" end_s="$3" timing_sh
    case "$round_num$start_s$end_s" in *[!0-9]*) return 0 ;; esac
    timing_sh="${RUN_STEP3_RECORD_TIMING_SH:-$PLUGIN_ROOT/skills/design/scripts/record-plan-review-round-timing.sh}"
    [[ -x "$timing_sh" ]] || return 0
    LARCH_TIMING_SKILL=design "$timing_sh" --design-tmpdir "$DESIGN_TMPDIR" --round "$round_num" --start-s "$start_s" --end-s "$end_s" || true
}

step3_loop_honor_pause() {
    local pause_sh issue_arg=()
    # shellcheck source=/dev/null
    [[ -f "$DESIGN_TMPDIR/source-env.sh" ]] && source "$DESIGN_TMPDIR/source-env.sh"
    [[ -f "$DESIGN_TMPDIR/.pause-requested" ]] || return 0
    pause_sh="${RUN_STEP3_DESIGN_PAUSE_SAVE_SH:-$PLUGIN_ROOT/scripts/design-pause-save.sh}"
    if [[ -n "${ISSUE_NUMBER:-}" ]]; then
        issue_arg=(--issue "$ISSUE_NUMBER")
    fi
    exec "$pause_sh" --design-tmpdir "$DESIGN_TMPDIR" "${issue_arg[@]}"
}

step3_loop_restore_snapshot() {
    local snapshot="$1"
    [[ -f "$snapshot" ]] || return 1
    cp "$snapshot" "$DESIGN_TMPDIR/plan.txt"
}

step3_loop_run_apply() {
    local round_num="$1" snapshot revise_sh revise_out revise_rc revise_status="" dedup_sh postplan_sh snap_sh
    local dedup_rc postplan_rc snapshot_rc cursor_rc next_round
    ACCEPTED_COUNT="$(step3_loop_count_accepted_findings)"
    case "$ACCEPTED_COUNT" in ''|*[!0-9]*) ACCEPTED_COUNT=0 ;; esac
    if (( 10#$ACCEPTED_COUNT == 0 )); then
        step3_loop_write_phase "$round_num" awaiting-continuation
        return 0
    fi

    snapshot="$DESIGN_TMPDIR/plan-pre-apply-round-${round_num}.txt"
    if [[ ! -f "$snapshot" ]]; then
        cp "$DESIGN_TMPDIR/plan.txt" "$snapshot"
    fi

    revise_sh="${RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH:-$PLUGIN_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh}"
    set +e
    revise_out=$(LARCH_QUIET_DISABLE=1 "$revise_sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --plan-file "$DESIGN_TMPDIR/plan.txt" \
        --findings-file "$DESIGN_TMPDIR/accepted-plan-findings.md" \
        --feature-file "$DESIGN_TMPDIR/feature-description.txt" \
        --round-num "$round_num" \
        --codex-present "${CODEX_PRESENT:-false}" \
        --cursor-present "${CURSOR_PRESENT:-false}" \
        --patch-format file-replacement)
    revise_rc=$?
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        case "$_line" in
            REVISE_STATUS=*) revise_status="${_line#*=}" ;;
        esac
    done <<<"${revise_out:-}"
    if [[ "$revise_rc" -ne 0 || ! "$revise_status" =~ ^(ok|ok-fallback)$ ]]; then
        step3_loop_write_phase "$round_num" awaiting-apply
        return 21
    fi

    step3_loop_write_phase "$round_num" awaiting-post-apply
    dedup_sh="${RUN_STEP3_DEDUP_PLAN_SH:-$PLUGIN_ROOT/skills/design/scripts/gate-b-dedup-plan.sh}"
    set +e
    "$dedup_sh" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers
    dedup_rc=$?
    if [[ "$dedup_rc" -eq 0 ]]; then
        "$dedup_sh" --design-tmpdir "$DESIGN_TMPDIR" --dedup
        dedup_rc=$?
    fi
    if [[ "$dedup_rc" -ne 0 ]]; then
        DEDUP_RC="$dedup_rc"
        step3_loop_restore_snapshot "$snapshot" || true
        step3_loop_write_phase "$round_num" awaiting-apply
        return 22
    fi
    : >"$DESIGN_TMPDIR/.gate-b-postapply-ready-${round_num}"
    return 0
}

step3_loop_run_post_apply() {
    local round_num="$1" postplan_sh postplan_rc snap_sh next_round
    postplan_sh="${RUN_STEP3_POSTPLAN_EMIT_SH:-$PLUGIN_ROOT/skills/design/scripts/design-postplan-emit.sh}"
    set +e
    "$postplan_sh" --design-tmpdir "$DESIGN_TMPDIR" --with-plan-size
    postplan_rc=$?
    case "$postplan_rc" in
        0)
            snap_sh="${RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh}"
            if [[ -x "$snap_sh" ]]; then
                set +e
                "$snap_sh" write-after --design-tmpdir "$DESIGN_TMPDIR" --round "$round_num"
                snapshot_rc=$?
                next_round=$((10#$round_num + 1))
                if [[ "$snapshot_rc" -eq 0 ]]; then
                    "$snap_sh" write-cursor --design-tmpdir "$DESIGN_TMPDIR" --value "$next_round"
                    cursor_rc=$?
                else
                    cursor_rc=1
                fi
                if [[ "$snapshot_rc" -ne 0 || "$cursor_rc" -ne 0 ]]; then
                    POSTPLAN_RC=1
                    return 31
                fi
            fi
            step3_loop_write_phase "$round_num" awaiting-continuation
            return 0
            ;;
        11)
            exec "${RUN_STEP3_DESIGN_PAUSE_SAVE_SH:-$PLUGIN_ROOT/scripts/design-pause-save.sh}" --design-tmpdir "$DESIGN_TMPDIR" --issue "${ISSUE_NUMBER:-0}"
            ;;
        10|12|13|14)
            POSTPLAN_RC="$postplan_rc"
            return 32
            ;;
        *)
            POSTPLAN_RC="$postplan_rc"
            return 33
            ;;
    esac
}

step3_loop_run_continuation() {
    local round_num="$1" cont_sh cont_out cont_rc
    cont_sh="${RUN_STEP3_CONTINUATION_SH:-$PLUGIN_ROOT/skills/design/scripts/plan-review-continuation.sh}"
    PLAN_REVIEW_CONTINUE=false
    PLAN_REVIEW_CONTINUE_REASON=""
    set +e
    cont_out=$(LARCH_QUIET_DISABLE=1 "$cont_sh" --design-tmpdir "$DESIGN_TMPDIR" --approve-requested "$APPROVE_REQUESTED")
    cont_rc=$?
    if [[ "$cont_rc" -ne 0 ]]; then
        PLAN_REVIEW_CONTINUE=false
        PLAN_REVIEW_CONTINUE_REASON=continuation-failed
        return 1
    fi
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        case "$_line" in
            PLAN_REVIEW_CONTINUE=*) PLAN_REVIEW_CONTINUE="${_line#*=}" ;;
            PLAN_REVIEW_CONTINUE_REASON=*) PLAN_REVIEW_CONTINUE_REASON="${_line#*=}" ;;
            ACCEPTED_COUNT=*) ACCEPTED_COUNT="${_line#*=}" ;;
            DEGRADED_PANEL=*) DEGRADED_PANEL="${_line#*=}" ;;
        esac
    done <<<"${cont_out:-}"
    return 0
}

run_design_step3_loop() {
    local round_num phase round_start_s post_rc body_rc terminal_rounds
    APPROVE_REQUESTED="$(step3_loop_read_bool_param approve_requested false)"
    round_num=$((10#$STARTING_ROUND))
    terminal_rounds=0

    while true; do
        step3_loop_honor_pause
        phase="$(step3_loop_read_phase "$round_num")"
        round_start_s="$(step3_loop_now_s)"
        if [[ -z "$phase" ]]; then
            set +e
            run_step3_round_body >/tmp/larch-step3-round-body.$$ 2>&1
            body_rc=$?
            set -e
            cat /tmp/larch-step3-round-body.$$
            rm -f /tmp/larch-step3-round-body.$$
            if [[ "$body_rc" -ne 0 && "${LOOP_STATUS:-}" != panel-failed ]]; then
                LOOP_STATUS=panel-failed
            fi
            round_num=$((10#${STEP3_REVIEW_ROUND_NUM:-$round_num}))
            case "${LOOP_STATUS:-}" in
                cap-reached)
                    step3_loop_write_completed_step3
                    step3_loop_emit_envelope cap-hit "$round_num" "$terminal_rounds" "$round_num"
                    exit 0
                    ;;
                tally-error|degraded-empty-collector|panel-failed)
                    step3_loop_write_completed_step3
                    step3_loop_record_timing "$round_num" "$round_start_s" "$(step3_loop_now_s)"
                    step3_loop_emit_envelope "${LOOP_STATUS:-panel-failed}" "$round_num" "$round_num" "$round_num"
                    exit 0
                    ;;
                main-agent-vote-required)
                    step3_loop_write_phase "$round_num" awaiting-apply
                    step3_loop_emit_envelope main-agent-vote-required "$round_num" "$round_num" "$round_num"
                    exit 0
                    ;;
                complete|zero-findings-degraded-panel)
                    ACCEPTED_COUNT="$(step3_loop_count_accepted_findings)"
                    case "$ACCEPTED_COUNT" in ''|*[!0-9]*) ACCEPTED_COUNT=0 ;; esac
                    if (( 10#$ACCEPTED_COUNT == 0 )); then
                        step3_loop_write_phase "$round_num" awaiting-continuation
                    elif [[ "$APPROVE_REQUESTED" == true ]]; then
                        step3_loop_write_phase "$round_num" awaiting-apply
                        step3_loop_emit_envelope per-round-approval-required "$round_num" "$round_num" "$round_num"
                        exit 0
                    else
                        phase=awaiting-apply
                    fi
                    ;;
                *)
                    step3_loop_write_completed_step3
                    step3_loop_emit_envelope panel-failed "$round_num" "$round_num" "$round_num"
                    exit 0
                    ;;
            esac
        fi

        phase="${phase:-$(step3_loop_read_phase "$round_num")}"
        case "$phase" in
            awaiting-apply)
                set +e
                step3_loop_run_apply "$round_num"
                post_rc=$?
                set -e
                case "$post_rc" in
                    0) phase=awaiting-post-apply ;;
                    21|22)
                        step3_loop_emit_envelope main-agent-apply-required "$round_num" "$round_num" "$round_num"
                        exit 0
                        ;;
                    *)
                        step3_loop_emit_envelope main-agent-apply-required "$round_num" "$round_num" "$round_num"
                        exit 0
                        ;;
                esac
                continue
                ;;
            awaiting-post-apply)
                set +e
                step3_loop_run_post_apply "$round_num"
                post_rc=$?
                set -e
                case "$post_rc" in
                    0) phase=awaiting-continuation ;;
                    32)
                        step3_loop_emit_envelope postplan-operator-required "$round_num" "$round_num" "$round_num"
                        exit 0
                        ;;
                    *)
                        step3_loop_emit_envelope postplan-failed "$round_num" "$round_num" "$round_num"
                        exit 0
                        ;;
                esac
                continue
                ;;
            awaiting-continuation)
                set +e
                step3_loop_run_continuation "$round_num"
                post_rc=$?
                set -e
                [[ "$post_rc" -eq 0 ]] || true
                step3_loop_record_timing "$round_num" "$round_start_s" "$(step3_loop_now_s)"
                if [[ "${PLAN_REVIEW_CONTINUE:-false}" == true ]]; then
                    "$PLUGIN_ROOT/skills/design/scripts/design-step3-state.sh" --design-tmpdir "$DESIGN_TMPDIR" --auto-continuation-entry >/dev/null 2>&1 || true
                    rm -f "$DESIGN_TMPDIR/.step3-entry-plan-printed"
                    round_num=$((10#$round_num + 1))
                    continue
                fi
                step3_loop_write_completed_step3
                step3_loop_emit_envelope complete "$round_num" "$round_num" "$round_num"
                exit 0
                ;;
            *)
                larch_err "review-design-step3-loop.sh: invalid phase for round $round_num: ${phase:-missing}"
                step3_loop_emit_envelope postplan-failed "$round_num" "$round_num" "$round_num"
                exit 2
                ;;
        esac
    done
}
