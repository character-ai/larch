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
    step3_loop_persist_envelope "$status" "$round_num" "${rounds_completed:-0}" "${final_round:-$round_num}"
}

step3_loop_read_review_round_count() {
    local count_file="$DESIGN_TMPDIR/review-round-count.txt" raw=""
    if [[ -s "$count_file" ]]; then
        raw="$(tr -d '[:space:]' <"$count_file" 2>/dev/null || true)"
        case "$raw" in
            ''|*[!0-9]*) printf '0\n' ;;
            *) printf '%s\n' "$raw" ;;
        esac
    else
        printf '0\n'
    fi
}

step3_loop_persist_envelope() {
    local status="$1" round_num="$2" rounds_completed="$3" final_round="$4"
    local result_env="$DESIGN_TMPDIR/.step3-review-result.env" loop_status="" kvs=() merge_key _line _key _value _present
    local persist_round_num="" persist_review_count=""
    case "$status" in
        cap-hit) loop_status=cap-reached ;;
        complete) loop_status=complete ;;
        main-agent-vote-required) loop_status=main-agent-vote-required ;;
        postplan-failed) loop_status=postplan-failed ;;
        panel-failed|tally-error|degraded-empty-collector) loop_status="$status" ;;
        main-agent-apply-required|per-round-approval-required|postplan-operator-required) loop_status=complete ;;
        *) loop_status="${LOOP_STATUS:-complete}" ;;
    esac
    case "$status" in
        cap-hit)
            persist_round_num=""
            persist_review_count="${rounds_completed:-0}"
            ;;
        tally-error|degraded-empty-collector|panel-failed|postplan-failed)
            persist_round_num=""
            persist_review_count="$(step3_loop_read_review_round_count)"
            ;;
        *)
            persist_round_num="${round_num:-}"
            persist_review_count="${round_num:-0}"
            ;;
    esac
    kvs=(
        "STEP3_REVIEW_LOOP_STATUS=$status"
        "LOOP_STATUS=$loop_status"
        "FINAL_ROUND_NUM=${final_round:-$round_num}"
        "ROUNDS_COMPLETED=${rounds_completed:-0}"
        "ACCEPTED_COUNT=${ACCEPTED_COUNT:-0}"
        "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-0}"
        "DEGRADED_PANEL=${DEGRADED_PANEL:-0}"
        "STEP3_REVIEW_ROUND_NUM=${persist_round_num}"
        "REVIEW_ROUND_COUNT=${persist_review_count}"
        "ROUND_NUM=${ROUND_NUM:-$round_num}"
        "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}"
        "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}"
        "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}"
        "PANEL_PRUNED_EMPTY=${PANEL_PRUNED_EMPTY:-false}"
    )
    [[ -z "${POSTPLAN_RC:-}" ]] || kvs+=("POSTPLAN_RC=${POSTPLAN_RC:-}")
    [[ -z "${DEDUP_RC:-}" ]] || kvs+=("DEDUP_RC=${DEDUP_RC:-}")
    [[ -z "${PLAN_REVIEW_CONTINUE_REASON:-}" ]] || kvs+=("PLAN_REVIEW_CONTINUE_REASON=${PLAN_REVIEW_CONTINUE_REASON:-}")
    [[ -z "${SCOPE_ANCHOR_FILE:-}" ]] || kvs+=("SCOPE_ANCHOR_FILE=${SCOPE_ANCHOR_FILE:-}")
    if [[ -f "$result_env" && ! -L "$result_env" ]]; then
        for merge_key in TALLY_PLAN_REVIEW_STATUS IMPORTANT_ACCEPTED_COUNT AGGREGATOR_STATUS VOTING_TALLY_FILE PANEL_PRUNED_EMPTY ROUND_NUM PLAN_REVIEW_CONTINUE_REASON; do
            _present=false
            for _line in "${kvs[@]}"; do
                _key="${_line%%=*}"
                if [[ "$_key" == "$merge_key" && -n "${_line#*=}" ]]; then
                    _present=true
                    break
                fi
            done
            [[ "$_present" == true ]] && continue
            while IFS= read -r _line || [[ -n "$_line" ]]; do
                _key="${_line%%=*}"
                _value="${_line#*=}"
                if [[ "$_key" == "$merge_key" && -n "$_value" ]]; then
                    kvs+=("${_key}=${_value}")
                    break
                fi
            done <"$result_env"
        done
    fi
    phase_driver_write_result_env "$result_env" "${kvs[@]}" || true
}

step3_loop_write_completed_step3() {
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : >"$DESIGN_TMPDIR/.completed/step-3"
    : >"$DESIGN_TMPDIR/.completed/step-3.5"
}

step3_loop_is_hard() {
    local tier=""
    tier="$(python3 "$PLUGIN_ROOT/python/cli.py" session read-classification "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo SIMPLE)"
    [[ "$tier" == HARD ]]
}

step3_loop_canonical_dir() {
    (cd "$1" 2>/dev/null && pwd -P) || return 1
}

step3_loop_path_under_tmpdir() {
    local path="$1" parent dir base real_parent real_path tmp_real
    [[ "$path" == /* ]] || return 1
    parent=$(dirname "$path")
    base=$(basename "$path")
    [[ -d "$parent" ]] || return 1
    real_parent=$(step3_loop_canonical_dir "$parent") || return 1
    tmp_real=$(step3_loop_canonical_dir "$DESIGN_TMPDIR") || return 1
    real_path="$real_parent/$base"
    case "$real_path" in
        "$tmp_real"/*) ;;
        *) return 1 ;;
    esac
    return 0
}

step3_loop_validate_tmpdir_file() {
    local path="$1"
    [[ -n "$path" ]] || return 1
    step3_loop_path_under_tmpdir "$path" || return 1
    [[ -f "$path" && ! -L "$path" && -r "$path" ]] || return 1
    return 0
}

step3_loop_source_env_get() {
    local key="$1" file="$2"
    awk -v k="$key" '
      BEGIN { q=sprintf("%c", 39) }
      $1 == "export" {
        v=$0
        sub(/^[[:space:]]*export[[:space:]]+/, "", v)
        if (index(v, k "=") != 1) next
        sub("^[^=]*=", "", v)
        if ((substr(v, 1, 1) == q && substr(v, length(v), 1) == q) ||
            (substr(v, 1, 1) == "\"" && substr(v, length(v), 1) == "\"")) {
          v=substr(v, 2, length(v)-2)
        }
        print v
        exit
      }
    ' "$file"
}

step3_loop_refresh_issue_from_source_env() {
    local source_env="$DESIGN_TMPDIR/source-env.sh" _issue=""
    [[ -f "$source_env" && ! -L "$source_env" && -r "$source_env" ]] || return 0
    if [[ -z "${ISSUE_NUMBER:-}" ]]; then
        _issue="$(step3_loop_source_env_get ISSUE_NUMBER "$source_env" 2>/dev/null || true)"
        if [[ -n "$_issue" && "$_issue" =~ ^[1-9][0-9]*$ ]]; then
            ISSUE_NUMBER="$_issue"
        fi
    fi
}

step3_loop_resolve_findings_file() {
    local round_num="$1" approval_env findings_file=""
    findings_file="$DESIGN_TMPDIR/accepted-plan-findings.md"
    approval_env="$DESIGN_TMPDIR/.gate-b-per-round-approval-round-${round_num}.env"
    if [[ -f "$approval_env" && ! -L "$approval_env" ]]; then
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            case "$_line" in
                FINDINGS_FILE=*) findings_file="${_line#FINDINGS_FILE=}" ;;
            esac
        done <"$approval_env"
    fi
    if [[ "$findings_file" != "$DESIGN_TMPDIR/accepted-plan-findings.md" ]] \
        && ! step3_loop_validate_tmpdir_file "$findings_file"; then
        findings_file="$DESIGN_TMPDIR/accepted-plan-findings.md"
    fi
    printf '%s\n' "$findings_file"
}

step3_loop_consume_approval_env() {
    local round_num="$1"
    rm -f "$DESIGN_TMPDIR/.gate-b-per-round-approval-round-${round_num}.env"
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
    local pause_sh
    step3_loop_refresh_issue_from_source_env
    [[ -f "$DESIGN_TMPDIR/.pause-requested" ]] || return 0
    pause_sh="${RUN_STEP3_DESIGN_PAUSE_SAVE_SH:-$PLUGIN_ROOT/scripts/design-pause-save.sh}"
    if [[ -n "${ISSUE_NUMBER:-}" ]]; then
        exec "$pause_sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER"
    else
        exec "$pause_sh" --design-tmpdir "$DESIGN_TMPDIR"
    fi
}

step3_loop_restore_snapshot() {
    local snapshot="$1"
    [[ -f "$snapshot" ]] || return 1
    cp "$snapshot" "$DESIGN_TMPDIR/plan.txt"
}

step3_loop_run_dedup() {
    local round_num="$1" snapshot dedup_sh dedup_rc
    snapshot="$DESIGN_TMPDIR/plan-pre-apply-round-${round_num}.txt"
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
    step3_loop_consume_approval_env "$round_num"
    return 0
}

step3_loop_run_hard_snapshots() {
    local round_num="$1" snap_sh next_round snapshot_rc cursor_rc
    if ! step3_loop_is_hard; then
        return 0
    fi
    snap_sh="${RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh}"
    if [[ ! -x "$snap_sh" ]]; then
        POSTPLAN_RC=1
        return 1
    fi
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
        return 1
    fi
    return 0
}

step3_loop_run_apply() {
    local round_num="$1" snapshot revise_sh revise_out revise_rc revise_status="" findings_file current_phase=""
    ACCEPTED_COUNT="$(step3_loop_count_accepted_findings)"
    case "$ACCEPTED_COUNT" in ''|*[!0-9]*) ACCEPTED_COUNT=0 ;; esac
    if (( 10#$ACCEPTED_COUNT == 0 )); then
        step3_loop_consume_approval_env "$round_num"
        step3_loop_write_phase "$round_num" awaiting-continuation
        return 0
    fi

    findings_file="$(step3_loop_resolve_findings_file "$round_num")"
    if [[ "$findings_file" != "$DESIGN_TMPDIR/accepted-plan-findings.md" ]] \
        && step3_loop_validate_tmpdir_file "$findings_file" && [[ -s "$findings_file" ]]; then
        cp "$findings_file" "$DESIGN_TMPDIR/accepted-plan-findings.md"
    fi
    if [[ ! -s "$findings_file" ]] || ! step3_loop_validate_tmpdir_file "$findings_file"; then
        : >"$DESIGN_TMPDIR/accepted-plan-findings.md"
        step3_loop_consume_approval_env "$round_num"
        step3_loop_write_phase "$round_num" awaiting-continuation
        return 0
    fi

    snapshot="$DESIGN_TMPDIR/plan-pre-apply-round-${round_num}.txt"
    if [[ ! -f "$snapshot" ]]; then
        cp "$DESIGN_TMPDIR/plan.txt" "$snapshot"
    fi
    current_phase="$(step3_loop_read_phase "$round_num")"
    if [[ -f "$snapshot" ]] && ! cmp -s "$snapshot" "$DESIGN_TMPDIR/plan.txt" 2>/dev/null; then
        if [[ "$current_phase" == awaiting-post-apply ]] \
            || [[ -f "$DESIGN_TMPDIR/.gate-b-postapply-ready-${round_num}" ]]; then
            step3_loop_run_dedup "$round_num"
            return $?
        fi
        if [[ "$current_phase" == awaiting-revise ]]; then
            cp "$snapshot" "$DESIGN_TMPDIR/plan.txt"
        fi
    fi

    step3_loop_write_phase "$round_num" awaiting-revise
    revise_sh="${RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH:-$PLUGIN_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh}"
    set +e
    revise_out=$(LARCH_QUIET_DISABLE=1 "$revise_sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --plan-file "$DESIGN_TMPDIR/plan.txt" \
        --findings-file "$findings_file" \
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

    step3_loop_run_dedup "$round_num"
    return $?
}

step3_loop_run_post_apply() {
    local round_num="$1" postplan_sh postplan_rc snap_sh next_round pause_sh
    postplan_sh="${RUN_STEP3_POSTPLAN_EMIT_SH:-$PLUGIN_ROOT/skills/design/scripts/design-postplan-emit.sh}"
    set +e
    "$postplan_sh" --design-tmpdir "$DESIGN_TMPDIR" --with-plan-size
    postplan_rc=$?
    case "$postplan_rc" in
        0)
            set +e
            step3_loop_run_hard_snapshots "$round_num"
            post_rc=$?
            set -e
            if [[ "$post_rc" -ne 0 ]]; then
                return 31
            fi
            step3_loop_write_phase "$round_num" awaiting-continuation
            return 0
            ;;
        11)
            step3_loop_refresh_issue_from_source_env
            pause_sh="${RUN_STEP3_DESIGN_PAUSE_SAVE_SH:-$PLUGIN_ROOT/scripts/design-pause-save.sh}"
            if [[ -n "${ISSUE_NUMBER:-}" ]]; then
                exec "$pause_sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER"
            else
                exec "$pause_sh" --design-tmpdir "$DESIGN_TMPDIR"
            fi
            ;;
        10|12|13)
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
    local round_num="$1" cont_sh cont_out cont_rc saw_continue=0
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
            PLAN_REVIEW_CONTINUE=*) PLAN_REVIEW_CONTINUE="${_line#*=}"; saw_continue=1 ;;
            PLAN_REVIEW_CONTINUE_REASON=*) PLAN_REVIEW_CONTINUE_REASON="${_line#*=}" ;;
            ACCEPTED_COUNT=*) ACCEPTED_COUNT="${_line#*=}" ;;
            DEGRADED_PANEL=*) DEGRADED_PANEL="${_line#*=}" ;;
        esac
    done <<<"${cont_out:-}"
    if [[ "$saw_continue" -eq 0 ]]; then
        PLAN_REVIEW_CONTINUE=false
        PLAN_REVIEW_CONTINUE_REASON=continuation-malformed
        return 1
    fi
    return 0
}

run_design_step3_loop() {
    local round_num phase round_start_s post_rc body_rc cap_rounds_completed
    APPROVE_REQUESTED="$(step3_loop_read_bool_param approve_requested false)"
    round_num=$((10#$STARTING_ROUND))

    while true; do
        step3_loop_honor_pause
        phase="$(step3_loop_read_phase "$round_num")"
        round_start_s="$(step3_loop_now_s)"
        if [[ -z "$phase" ]]; then
            local round_body_capture=""
            round_body_capture="$(mktemp "$DESIGN_TMPDIR/.step3-round-body.XXXXXX")"
            set +e
            run_step3_round_body >"$round_body_capture" 2>&1
            body_rc=$?
            set -e
            cat "$round_body_capture"
            rm -f "$round_body_capture"
            if [[ "$body_rc" -ne 0 && "${LOOP_STATUS:-}" != panel-failed ]]; then
                LOOP_STATUS=panel-failed
            fi
            round_num=$((10#${STEP3_REVIEW_ROUND_NUM:-$round_num}))
            case "${LOOP_STATUS:-}" in
                cap-reached)
                    step3_loop_write_completed_step3
                    cap_rounds_completed=$((10#$round_num - 1))
                    (( cap_rounds_completed < 0 )) && cap_rounds_completed=0
                    step3_loop_emit_envelope cap-hit "$round_num" "$cap_rounds_completed" "$round_num"
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
                        step3_loop_write_phase "$round_num" awaiting-apply
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
            awaiting-revise)
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
            awaiting-apply)
                if [[ "$APPROVE_REQUESTED" == true && ! -f "$DESIGN_TMPDIR/.gate-b-per-round-approval-round-${round_num}.env" ]]; then
                    step3_loop_emit_envelope per-round-approval-required "$round_num" "$round_num" "$round_num"
                    exit 0
                fi
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
            awaiting-post-apply|awaiting-postplan-operator)
                if [[ "$phase" == awaiting-postplan-operator ]]; then
                    if [[ -f "$DESIGN_TMPDIR/.postplan-operator-continue-${round_num}" ]]; then
                        rm -f "$DESIGN_TMPDIR/.postplan-operator-continue-${round_num}"
                        set +e
                        step3_loop_run_hard_snapshots "$round_num"
                        post_rc=$?
                        set -e
                        if [[ "$post_rc" -ne 0 ]]; then
                            step3_loop_emit_envelope postplan-failed "$round_num" "$round_num" "$round_num"
                            exit 0
                        fi
                        step3_loop_write_phase "$round_num" awaiting-continuation
                        phase=awaiting-continuation
                        continue
                    fi
                    step3_loop_emit_envelope postplan-operator-required "$round_num" "$round_num" "$round_num"
                    exit 0
                fi
                if [[ ! -f "$DESIGN_TMPDIR/.gate-b-postapply-ready-${round_num}" ]]; then
                    set +e
                    step3_loop_run_dedup "$round_num"
                    post_rc=$?
                    set -e
                    if [[ "$post_rc" -ne 0 ]]; then
                        step3_loop_emit_envelope main-agent-apply-required "$round_num" "$round_num" "$round_num"
                        exit 0
                    fi
                fi
                set +e
                step3_loop_run_post_apply "$round_num"
                post_rc=$?
                set -e
                case "$post_rc" in
                    0) phase=awaiting-continuation ;;
                    32)
                        step3_loop_write_phase "$round_num" awaiting-postplan-operator
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
                if [[ "$post_rc" -ne 0 ]]; then
                    step3_loop_emit_envelope postplan-failed "$round_num" "$round_num" "$round_num"
                    exit 0
                fi
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
