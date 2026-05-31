#!/usr/bin/env bash
# review-implement-step5-loop.sh — absorbed Step 5 multi-round controller for /implement.
# Sourced from review-and-fix.sh after _implement_round_body is defined. Bash 3.2.

# shellcheck disable=SC2034

# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$PLUGIN_ROOT/scripts/lib-failed-agent-stderr-tail.sh"

step5_parse_kv_tokens() {
    # Always exits 0 under set -e; absent key yields empty stdout (callers use [[ -n "$v" ]]).
    local line="$1" key="$2" tok v=""
    case "$key" in
        STDERR_TAIL_PATH|CODER_LOG_FILE|REDACTED_LOG_FILE)
            v=$(printf '%s\n' "$line" | awk -F= -v k="$key" '$1 == k { print substr($0, index($0,"=")+1); exit }')
            printf '%s\n' "${v:-}"
            return 0
            ;;
    esac
    for tok in $line; do
        case "$tok" in
            "${key}="*) printf '%s\n' "${tok#*=}"; return 0 ;;
        esac
    done
    printf '\n'
    return 0
}

step5_parse_checks_capture_file() {
    local file="$1"
    local line="" k="" v=""
    STEP5_CHK_STATUS=""
    STEP5_CHK_FAILURE_REASON=""
    STEP5_CHK_REDACTED_LOG_FILE=""
    STEP5_CHK_RELEVANT_CHECKS_OK=""
    STEP5_CHK_RELEVANT_CHECKS_SKIPPED=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        v="$(step5_parse_kv_tokens "$line" STATUS)"
        [[ -n "$v" ]] && STEP5_CHK_STATUS="$v"
        v="$(step5_parse_kv_tokens "$line" FAILURE_REASON)"
        [[ -n "$v" ]] && STEP5_CHK_FAILURE_REASON="$v"
        v="$(step5_parse_kv_tokens "$line" REDACTED_LOG_FILE)"
        [[ -n "$v" ]] && STEP5_CHK_REDACTED_LOG_FILE="$v"
        v="$(step5_parse_kv_tokens "$line" RELEVANT_CHECKS_OK)"
        [[ -n "$v" ]] && STEP5_CHK_RELEVANT_CHECKS_OK="$v"
        v="$(step5_parse_kv_tokens "$line" RELEVANT_CHECKS_SKIPPED)"
        [[ -n "$v" ]] && STEP5_CHK_RELEVANT_CHECKS_SKIPPED="$v"
    done <"$file"
    if [[ -z "${STEP5_CHK_STATUS:-}" && -z "${STEP5_CHK_RELEVANT_CHECKS_OK:-}" && -z "${STEP5_CHK_RELEVANT_CHECKS_SKIPPED:-}" ]]; then
        printf '%s\n' "step5_parse_checks_capture_file: required field missing (none of STATUS, RELEVANT_CHECKS_OK, RELEVANT_CHECKS_SKIPPED) in capture file: $file" >&2
        STEP5_CHK_STATUS=fail
        STEP5_CHK_FAILURE_REASON=malformed-capture
    fi
}

step5_parse_lint_capture_file() {
    local file="$1" line="" v=""
    STEP5_LINT_STATUS=""
    STEP5_LINT_STDERR_TAIL_STEM=""
    STEP5_LINT_CODER_LOG_STEM=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        v="$(step5_parse_kv_tokens "$line" LINT_FIX_STATUS)"
        [[ -n "$v" ]] && STEP5_LINT_STATUS="$v"
        v="$(step5_parse_kv_tokens "$line" STDERR_TAIL_PATH)"
        [[ -n "$v" ]] && STEP5_LINT_STDERR_TAIL_STEM="$v"
        v="$(step5_parse_kv_tokens "$line" CODER_LOG_FILE)"
        [[ -n "$v" ]] && STEP5_LINT_CODER_LOG_STEM="$v"
    done <"$file"
    if [[ -z "${STEP5_LINT_STATUS:-}" ]]; then
        printf '%s\n' "step5_parse_lint_capture_file: required field missing (LINT_FIX_STATUS) in capture file: $file" >&2
    fi
}

step5_surface_lint_stderr_tail() {
    local stem=""
    if [[ -n "${STEP5_LINT_STDERR_TAIL_STEM:-}" ]]; then
        stem="$STEP5_LINT_STDERR_TAIL_STEM"
    elif [[ -n "${STEP5_LINT_CODER_LOG_STEM:-}" ]]; then
        stem="$STEP5_LINT_CODER_LOG_STEM"
    fi
    [[ -n "$stem" ]] || return 0
    emit_failed_agent_stderr_tail_larch_err "$stem" || true
}

step5_emit_final_envelope() {
    local step5_status="$1" stall_tracking="$2" stall_reason="$3" rounds_completed="$4" final_round="$5" \
        final_irf="$6" coder_st="$7" files_hint="$8" eff_cap="$9"
    emit_kv STEP5_REVIEW_STATUS "$step5_status"
    emit_kv STALL_TRACKING "$stall_tracking"
    emit_kv STALL_REASON "${stall_reason:-}"
    emit_kv ROUNDS_COMPLETED "$rounds_completed"
    emit_kv FINAL_ROUND_NUM "$final_round"
    emit_kv FINAL_REVIEW_AND_FIX_STATUS "$final_irf"
    emit_kv CODER_STATUS "${coder_st:-}"
    emit_kv FILES_CHANGED_HINT "${files_hint:-}"
    emit_kv EFFECTIVE_ROUND_CAP "$eff_cap"
}

# Best-effort retry shim for the immediately previous round artifact. `sync`
# is not a guaranteed cache-invalidation barrier; it only gives a just-written
# env file one bounded retry before the loop fail-closes.
step5_probe_prior_round_env() {
    local implement_tmpdir="$1" prior_round="$2"
    local expected_env_path="$implement_tmpdir/round-$((10#$prior_round))/review-and-fix.env"
    [[ -f "$expected_env_path" ]] && return 0
    sync >/dev/null 2>&1 || true
    [[ -f "$expected_env_path" ]] && return 0
    return 1
}

run_implement_loop() {
    local base_cap="${ROUND_CAP:-5}"
    case "$base_cap" in ''|*[!0-9]*) larch_err "review-and-fix.sh: --round-cap must be a positive integer for loop mode"; exit 2 ;; esac
    (( 10#$base_cap > 0 )) || { larch_err "review-and-fix.sh: --round-cap must be positive"; exit 2; }

    case "$STARTING_ROUND" in ''|*[!0-9]*) larch_err "review-and-fix.sh: --starting-round must be a positive integer"; exit 2 ;; esac
    (( 10#$STARTING_ROUND > 0 )) || { larch_err "review-and-fix.sh: --starting-round must be positive"; exit 2; }

    local entry_prior_deg="" entry_effective_cap="" prior_round_num=0 expected_env_path=""
    entry_prior_deg="$(count_prior_degraded_rounds "$IMPLEMENT_TMPDIR" "$STARTING_ROUND")"
    case "$entry_prior_deg" in
        ''|*[!0-9]*)
            larch_err "review-and-fix.sh: count_prior_degraded_rounds returned non-numeric entry_prior_deg=${entry_prior_deg:-}"
            step5_emit_final_envelope stall true env-write-failed 0 "$STARTING_ROUND" unknown "" "" "$base_cap"
            exit 2
            ;;
    esac
    entry_effective_cap=$((10#$base_cap + 10#$entry_prior_deg))

    if (( 10#$STARTING_ROUND > 1 )); then
        prior_round_num=$((10#$STARTING_ROUND - 1))
        expected_env_path="$IMPLEMENT_TMPDIR/round-${prior_round_num}/review-and-fix.env"
        if (( 10#$STARTING_ROUND > entry_effective_cap )) && [[ -f "$expected_env_path" ]]; then
            flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" 0 0 0 0 0 2>/dev/null || true
            step5_emit_final_envelope mav-resume-past-cap false "" 0 "$prior_round_num" complete "" "" "$entry_effective_cap"
            exit 0
        fi
        if ! step5_probe_prior_round_env "$IMPLEMENT_TMPDIR" "$prior_round_num"; then
            larch_err "IMPLEMENT_TMPDIR=$IMPLEMENT_TMPDIR STARTING_ROUND=$STARTING_ROUND expected_env_path=$expected_env_path base_cap=$base_cap entry_prior_deg=$entry_prior_deg entry_effective_cap=$entry_effective_cap"
            step5_emit_final_envelope stall false starting-round-invalid 0 "$STARTING_ROUND" unknown "" "" "$entry_effective_cap"
            exit 2
        fi
    fi

    local round_num=$((10#$STARTING_ROUND))
    local effective_round_cap="" prior_deg="" degraded_env="" skip_ratio="" threshold="0.5"
    local structural_loc substantial checks_sh lint_sh cap_out lint_out
    local post_round_status="" post_exit=0 post_coder="" post_skipped=0 post_fix=0 post_round_dir="" post_accepted=""
    local lint_attempts lint_max="${LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS:-3}"
    local rounds_completed=0 last_irf="" last_coder="" last_hint="" stall_track=false stall_reason=""

    checks_sh="${REVIEW_AND_FIX_RUN_RELEVANT_CHECKS_SH:-$PLUGIN_ROOT/scripts/run-relevant-checks-captured.sh}"
    lint_sh="${REVIEW_AND_FIX_LINT_FIX_LOOP_SH:-$PLUGIN_ROOT/scripts/lint-fix-loop.sh}"

    if [[ -n "${LARCH_SKIP_RATIO_THRESHOLD:-}" ]]; then
        if awk -v t="$LARCH_SKIP_RATIO_THRESHOLD" 'BEGIN{ exit !(t+0>0 && t+0<1) }'; then
            threshold="$LARCH_SKIP_RATIO_THRESHOLD"
        else
            larch_err "⚠ review-and-fix: invalid LARCH_SKIP_RATIO_THRESHOLD=${LARCH_SKIP_RATIO_THRESHOLD}; using 0.5"
        fi
    fi

    while true; do
        prior_deg="$(count_prior_degraded_rounds "$IMPLEMENT_TMPDIR" "$round_num")"
        effective_round_cap=$((10#$base_cap + 10#$prior_deg))

        if (( round_num > effective_round_cap )); then
            step5_emit_final_envelope mav-resume-past-cap false "" "$rounds_completed" $((round_num - 1)) "${last_irf:-complete}" "${last_coder:-}" "${last_hint:-}" "$effective_round_cap"
            flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "${rounds_completed:-0}" 0 0 0 0 2>/dev/null || true
            exit 0
        fi

        larch_err "→ Step 5 round ${round_num}/${effective_round_cap}"

        ROUND_NUM="$round_num"
        MODE='diff'
        IRF_SUPPRESS_EMIT_KV=1
        set +e
        _implement_round_body
        post_exit=$?
        set -e
        IRF_SUPPRESS_EMIT_KV=""
        MODE=loop

        post_round_status="${IRF_LAST_ROUND_STATUS:-unknown}"
        post_coder="${IRF_LAST_CODER_STATUS:-}"
        post_skipped="${IRF_LAST_SKIPPED:-0}"
        post_fix="${IRF_LAST_FIX_COUNT:-0}"
        post_round_dir="${IRF_LAST_ROUND_DIR:-}"
        post_accepted="${IRF_LAST_ACCEPTED_FILE:-}"
        last_irf="$post_round_status"
        last_coder="$post_coder"
        last_hint="${IRF_LAST_FILES_HINT:-}"
        rounds_completed=$round_num

        case "$post_round_status" in
            main-agent-vote-required)
                step5_emit_final_envelope main-agent-vote-required false "" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                exit 0
                ;;
            coder-main-agent-required)
                # #3207: codex -> cursor both exhausted this round; hand the
                # accepted-findings application off to the main agent (Step 5
                # orchestrator) rather than stalling — the Claude tier of the
                # coder waterfall.
                step5_emit_final_envelope coder-main-agent-required false "" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                exit 0
                ;;
            panel-failed)
                step5_emit_final_envelope stall true panel-failed "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                exit 2
                ;;
            aggregator-validation-exhausted)
                step5_emit_final_envelope stall true aggregator-validation-exhausted "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                exit 2
                ;;
            coder-failed)
                stall_reason=coder-failed
                if [[ "$post_coder" == "submodule-violation" ]]; then
                    stall_reason=submodule-violation
                fi
                step5_emit_final_envelope stall true "$stall_reason" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                exit 2
                ;;
            converged-small-changes|no-changes|no-findings|in-scope-filtered-out|complete)
                step5_emit_final_envelope complete false "" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                exit 0
                ;;
            fix-applied) ;;
            *)
                step5_emit_final_envelope stall true "round-failed-${post_round_status:-unknown}" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                exit 2
                ;;
        esac

        cap_out="$IMPLEMENT_TMPDIR/.step5-checks-capture.$$.$RANDOM.log"
        rm -f "$cap_out"
        set +e
        "$checks_sh" --tmpdir "$IMPLEMENT_TMPDIR" --site step5-review-fixes >"$cap_out" 2>&1
        set -e
        step5_parse_checks_capture_file "$cap_out"
        rm -f "$cap_out"

        if [[ "$STEP5_CHK_RELEVANT_CHECKS_SKIPPED" == "true" ]]; then
            STEP5_CHK_STATUS=pass
        fi
        if [[ "$STEP5_CHK_RELEVANT_CHECKS_OK" == "true" ]]; then
            STEP5_CHK_STATUS=pass
        fi

        if [[ "$STEP5_CHK_STATUS" == "fail" ]]; then
            if [[ -z "${STEP5_CHK_REDACTED_LOG_FILE:-}" ]]; then
                step5_emit_final_envelope stall true "relevant-checks-${STEP5_CHK_FAILURE_REASON:-unknown}" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                exit 2
            fi
            lint_attempts=0
            while true; do
                lint_out="$IMPLEMENT_TMPDIR/.step5-lint-capture.$$.$RANDOM.log"
                rm -f "$lint_out"
                set +e
                "$lint_sh" --tmpdir "$IMPLEMENT_TMPDIR" --site step5 --checks-log "$STEP5_CHK_REDACTED_LOG_FILE" >"$lint_out" 2>&1
                set -e
                step5_parse_lint_capture_file "$lint_out"
                rm -f "$lint_out"
                case "${STEP5_LINT_STATUS:-}" in
                    applied)
                        lint_attempts=$((lint_attempts + 1))
                        if (( lint_attempts >= 10#$lint_max )); then
                            step5_surface_lint_stderr_tail
                            step5_emit_final_envelope stall true lint-fix-attempt-cap "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                            flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                            exit 2
                        fi
                        cap_out="$IMPLEMENT_TMPDIR/.step5-checks-capture.$$.$RANDOM.log"
                        rm -f "$cap_out"
                        set +e
                        "$checks_sh" --tmpdir "$IMPLEMENT_TMPDIR" --site step5-review-fixes >"$cap_out" 2>&1
                        set -e
                        step5_parse_checks_capture_file "$cap_out"
                        rm -f "$cap_out"
                        if [[ "$STEP5_CHK_RELEVANT_CHECKS_SKIPPED" == "true" || "$STEP5_CHK_RELEVANT_CHECKS_OK" == "true" ]]; then
                            break
                        fi
                        if [[ "$STEP5_CHK_STATUS" != "fail" ]]; then
                            break
                        fi
                        ;;
                    main-agent-required)
                        step5_surface_lint_stderr_tail
                        step5_emit_final_envelope stall true lint-fix-main-agent-required "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                        flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                        exit 2
                        ;;
                    failed)
                        step5_surface_lint_stderr_tail
                        step5_emit_final_envelope stall true lint-fix-failed "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                        flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                        exit 2
                        ;;
                    no-changes)
                        cap_out="$IMPLEMENT_TMPDIR/.step5-checks-capture.$$.$RANDOM.log"
                        rm -f "$cap_out"
                        set +e
                        "$checks_sh" --tmpdir "$IMPLEMENT_TMPDIR" --site step5-review-fixes >"$cap_out" 2>&1
                        set -e
                        step5_parse_checks_capture_file "$cap_out"
                        rm -f "$cap_out"
                        if [[ "$STEP5_CHK_RELEVANT_CHECKS_SKIPPED" == "true" || "$STEP5_CHK_RELEVANT_CHECKS_OK" == "true" ]]; then
                            break
                        fi
                        step5_surface_lint_stderr_tail
                        step5_emit_final_envelope stall true lint-fix-failed "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                        flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                        exit 2
                        ;;
                    *)
                        step5_surface_lint_stderr_tail
                        step5_emit_final_envelope stall true lint-fix-failed "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
                        flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
                        exit 2
                        ;;
                esac
            done
        fi

        degraded_env="$(kv_get "${post_round_dir}/review-and-fix.env" DEGRADED_ROUND)"
        if [[ "$degraded_env" == "true" ]]; then
            effective_round_cap=$((effective_round_cap + 1))
        fi

        structural_loc=0
        if [[ -s "${post_round_dir}/pre-coder-head.txt" && -s "${post_round_dir}/post-coder-head.txt" ]]; then
            set +e
            structural_loc=$(git diff --numstat "$(cat "${post_round_dir}/pre-coder-head.txt")" "$(cat "${post_round_dir}/post-coder-head.txt")" 2>/dev/null | awk '{a+=$1; b+=$2} END {print a+b+0}')
            set -e
            [[ "$structural_loc" =~ ^[0-9]+$ ]] || structural_loc=0
        fi

        local high_n=0
        high_n="$(count_high_severity_accepted "${post_accepted:-}")"
        [[ "$high_n" =~ ^[0-9]+$ ]] || high_n=0

        substantial=false
        if (( high_n >= 2 )) || (( structural_loc >= 100 )) || (( post_fix >= 8 )); then
            substantial=true
        fi

        skip_ratio=0
        if (( post_fix > 0 )); then
            skip_ratio=$(awk -v s="$post_skipped" -v f="$post_fix" 'BEGIN { if (f == 0) print 0; else print s / f }')
        fi

        local skip_hit=false
        if awk -v r="$skip_ratio" -v t="$threshold" 'BEGIN { exit !(r + 0 >= t + 0) }'; then
            skip_hit=true
        fi

        if [[ "$skip_hit" == true ]]; then
            if (( round_num < effective_round_cap )); then
                larch_err "⏳ Step 5: bulk-skip-ratio gate triggered (ratio=${skip_ratio}; threshold=${threshold}); continuing"
                round_num=$((round_num + 1))
                continue
            fi
            step5_emit_final_envelope stall true bulk-skip-ratio-cap "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
            flush_review_batches "$IMPLEMENT_TMPDIR" "$RUN_ID" "$rounds_completed" 0 0 0 0 2>/dev/null || true
            exit 2
        fi

        if [[ "$substantial" == true ]]; then
            if (( round_num < effective_round_cap )); then
                round_num=$((round_num + 1))
                continue
            fi
            step5_emit_final_envelope cap-hit false "" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
            exit 0
        fi

        step5_emit_final_envelope complete false "" "$rounds_completed" "$round_num" "$post_round_status" "$post_coder" "$last_hint" "$effective_round_cap"
        exit 0
    done
}

run_implement_mav_apply() {
    case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "review-and-fix.sh: mav-apply requires --round-num"; exit 2 ;; esac
    (( 10#$ROUND_NUM > 0 )) || { larch_err "review-and-fix.sh: mav-apply requires positive --round-num"; exit 2; }
    [[ -n "$FINDINGS_FILE" && -f "$FINDINGS_FILE" ]] || { larch_err "review-and-fix.sh: mav-apply requires --findings-file"; exit 2; }
    [[ -n "$IMPLEMENT_TMPDIR" && -d "$IMPLEMENT_TMPDIR" ]] || { larch_err "review-and-fix.sh: mav-apply requires --implement-tmpdir"; exit 2; }

    local round_num_dec=$((10#$ROUND_NUM)) round_dir="$IMPLEMENT_TMPDIR/round-$((10#$ROUND_NUM))"
    mkdir -p "$round_dir"
    git rev-parse HEAD > "$round_dir/pre-coder-head.txt" 2>/dev/null || rm -f "$round_dir/pre-coder-head.txt"
    local coder_env="$round_dir/coder.env" coder_rc=0
    set +e
    apply_findings_with_coder "$FINDINGS_FILE" "$round_dir" "$coder_env" "$round_num_dec"
    coder_rc=$?
    set -e
    if [[ "$coder_rc" -eq 0 ]]; then
        local st
        st=$(kv_get "$coder_env" CODER_STATUS)
        if [[ "$st" == "applied" ]]; then
            git rev-parse HEAD > "$round_dir/post-coder-head.txt" 2>/dev/null || rm -f "$round_dir/post-coder-head.txt"
        fi
    fi
    emit_kv REVIEW_AND_FIX_STATUS mav-apply-done
    emit_kv CODER_STATUS "$(kv_get "$coder_env" CODER_STATUS)"
    exit 0
}
