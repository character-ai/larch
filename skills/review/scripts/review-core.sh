#!/usr/bin/env bash
# review-core.sh — Single-round /review state machine.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
# shellcheck source=scripts/lib-prune-decision.sh
source "$PLUGIN_ROOT/scripts/lib-prune-decision.sh"
larch_quiet_init

usage() {
    larch_err "Usage: review-core.sh --mode diff|description --output-dir DIR --codex-available true|false --cursor-available true|false [--dynamic-archetypes 0-3] [context flags]"
}

MODE=""
REVIEW_TMPDIR=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
DIFF_FILE=""
COMMIT_COUNT="0"
SCOPE_FILES=""
PLAN_FILE=""
FEATURE_FILE=""
DESCRIPTION_TEXT=""
PANEL="hard"
RUN_ID=""
ROUND_NUM="1"
PRUNE_LEDGER=""
REVIEWER_PRUNE_SH="${REVIEWER_PRUNE_SH:-$PLUGIN_ROOT/scripts/reviewer-prune.sh}"
# Non-empty process env only: set-but-empty must fall through to default 0
# (matches review-and-fix.sh / test-review-and-fix.sh empty-export semantics).
if [[ -n "${LARCH_DYNAMIC_ARCHETYPES_MAX:-}" ]]; then
    DYNAMIC_ARCHETYPES="$LARCH_DYNAMIC_ARCHETYPES_MAX"
else
    DYNAMIC_ARCHETYPES="0"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --output-dir) REVIEW_TMPDIR="${2:?--output-dir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --dynamic-archetypes) DYNAMIC_ARCHETYPES="${2:?--dynamic-archetypes requires a value}"; shift 2 ;;
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --prune-ledger) PRUNE_LEDGER="${2:?--prune-ledger requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "review-core.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "review-core.sh: --mode must be diff or description"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "review-core.sh: --output-dir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "review-core.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "review-core.sh: --cursor-available must be true or false"; exit 2; }
[[ "$PANEL" == "simple" || "$PANEL" == "hard" ]] || { larch_err "review-core.sh: --panel must be simple or hard"; exit 2; }
case "$DYNAMIC_ARCHETYPES" in
    [0-3]) ;;
    *) larch_err "review-core.sh: --dynamic-archetypes/LARCH_DYNAMIC_ARCHETYPES_MAX must be an integer from 0 to 3"; exit 2 ;;
esac
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "review-core.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "review-core.sh: --round-num must be a positive integer"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

: "$RUN_ID"

GATHER_CONTEXT_SH="${REVIEW_CORE_GATHER_CONTEXT_SH:-$SCRIPT_DIR/gather-context.sh}"
DISPATCH_PANEL_SH="${REVIEW_CORE_DISPATCH_PANEL_SH:-$SCRIPT_DIR/dispatch-panel.sh}"
COLLECT_FINDINGS_SH="${REVIEW_CORE_COLLECT_FINDINGS_SH:-$SCRIPT_DIR/collect-findings.sh}"
PRUNE_NITS_SH="${REVIEW_CORE_PRUNE_NITS_SH:-$SCRIPT_DIR/prune-nit-findings.sh}"
AGGREGATE_FINDINGS_SH="${REVIEW_CORE_AGGREGATE_FINDINGS_SH:-$SCRIPT_DIR/aggregate-findings.sh}"
TALLY_VOTES_SH="${REVIEW_CORE_TALLY_VOTES_SH:-$SCRIPT_DIR/tally-code-votes.sh}"
EMIT_TALLY_SH="${REVIEW_CORE_EMIT_TALLY_SH:-$SCRIPT_DIR/emit-tally.sh}"
CHECK_DIRTY_TREE_SH="${REVIEW_CORE_CHECK_DIRTY_TREE_SH:-$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh}"
CHECK_THRESHOLD_SH="${REVIEW_CORE_CHECK_THRESHOLD_SH:-$SCRIPT_DIR/check-reviewer-failure-threshold.sh}"
DISPATCH_VOTERS_SH="${REVIEW_CORE_DISPATCH_VOTERS_SH:-$PLUGIN_ROOT/scripts/dispatch-code-voters.sh}"
LARCH_LOG_SH="${REVIEW_CORE_LARCH_LOG_SH:-$PLUGIN_ROOT/python/cli.py run-log}"
APPEND_TOOL_FAILURE_SH="${REVIEW_CORE_APPEND_TOOL_FAILURE_SH:-$PLUGIN_ROOT/python/cli.py run-log append-failure}"

kv_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

copy_to_parent() {
    local file="$1" name="$2"
    [[ -n "$SESSION_ENV_PATH" && -f "$file" ]] || return 0
    cp "$file" "$(dirname "$SESSION_ENV_PATH")/$name" 2>/dev/null || true
}

record_findings_classification_round() {
    local classification_file="$1"
    local map_file="$REVIEW_TMPDIR/findings-classification-round-map.env" tmp_file
    [[ -n "$classification_file" ]] || return 0
    tmp_file="$(mktemp "${TMPDIR:-/tmp}/review-core-findings-map.XXXXXX")" || return 1
    {
        if [[ -f "$map_file" ]]; then
            awk -F= -v round_key="FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_${ROUND_NUM}" '
                $1 != "FINDINGS_CLASSIFICATION_TSV_FILE" && $1 != round_key { print $0 }
            ' "$map_file"
        fi
        printf 'FINDINGS_CLASSIFICATION_TSV_FILE=%s\n' "$classification_file"
        printf 'FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_%s=%s\n' "$ROUND_NUM" "$classification_file"
    } > "$tmp_file"
    mv -f "$tmp_file" "$map_file"
    emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$classification_file"
    emit_kv "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_${ROUND_NUM}" "$classification_file"
}


record_reviewer_prune_round() {
    local classification_file="$1" record_out=""
    [[ -n "$PRUNE_LEDGER" ]] || return 0
    [[ -n "$panel_manifest" && -f "$panel_manifest" ]] || return 0
    [[ -n "$classification_file" && -f "$classification_file" ]] || return 0
    set +e
    record_out=$("$REVIEWER_PRUNE_SH" record \
        --ledger "$PRUNE_LEDGER" \
        --round "$ROUND_NUM" \
        --manifest "$panel_manifest" \
        --classification "$classification_file" 2>&1)
    record_rc=$?
    set -e
    if [[ "$record_rc" -ne 0 ]]; then
        emit_kv WARN "reviewer-prune record failed for round $ROUND_NUM: $(printf '%s' "$record_out" | tail -n 1 | sanitize_diagnostic_line)"
    fi
}

snapshot_review_oos_state() {
    local stem="$1" parent_dir=""
    if [[ -f "$REVIEW_TMPDIR/oos-accepted-review.md" ]]; then
        cp -f "$REVIEW_TMPDIR/oos-accepted-review.md" "$REVIEW_TMPDIR/${stem}.oos-accepted-review.before.md"
    else
        rm -f "$REVIEW_TMPDIR/${stem}.oos-accepted-review.before.md"
    fi
    if [[ -f "$REVIEW_TMPDIR/accumulated-oos.md" ]]; then
        cp -f "$REVIEW_TMPDIR/accumulated-oos.md" "$REVIEW_TMPDIR/${stem}.accumulated-oos.before.md"
    else
        rm -f "$REVIEW_TMPDIR/${stem}.accumulated-oos.before.md"
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        parent_dir="$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        parent_dir="$IMPLEMENT_TMPDIR"
    fi
    if [[ -n "$parent_dir" && -f "$parent_dir/oos-accepted-review.md" ]]; then
        cp -f "$parent_dir/oos-accepted-review.md" "$REVIEW_TMPDIR/${stem}.parent-oos-accepted-review.before.md"
    else
        rm -f "$REVIEW_TMPDIR/${stem}.parent-oos-accepted-review.before.md"
    fi
    if [[ -n "$parent_dir" && -f "$parent_dir/accumulated-oos.md" ]]; then
        cp -f "$parent_dir/accumulated-oos.md" "$REVIEW_TMPDIR/${stem}.parent-accumulated-oos.before.md"
    else
        rm -f "$REVIEW_TMPDIR/${stem}.parent-accumulated-oos.before.md"
    fi
}

restore_review_oos_state() {
    local stem="$1" parent_dir=""
    if [[ -f "$REVIEW_TMPDIR/${stem}.oos-accepted-review.before.md" ]]; then
        cp -f "$REVIEW_TMPDIR/${stem}.oos-accepted-review.before.md" "$REVIEW_TMPDIR/oos-accepted-review.md"
    else
        : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    fi
    if [[ -f "$REVIEW_TMPDIR/${stem}.accumulated-oos.before.md" ]]; then
        cp -f "$REVIEW_TMPDIR/${stem}.accumulated-oos.before.md" "$REVIEW_TMPDIR/accumulated-oos.md"
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        parent_dir="$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        parent_dir="$IMPLEMENT_TMPDIR"
    fi
    if [[ -n "$parent_dir" ]]; then
        if [[ -f "$REVIEW_TMPDIR/${stem}.parent-oos-accepted-review.before.md" ]]; then
            cp -f "$REVIEW_TMPDIR/${stem}.parent-oos-accepted-review.before.md" "$parent_dir/oos-accepted-review.md"
        fi
        if [[ -f "$REVIEW_TMPDIR/${stem}.parent-accumulated-oos.before.md" ]]; then
            cp -f "$REVIEW_TMPDIR/${stem}.parent-accumulated-oos.before.md" "$parent_dir/accumulated-oos.md"
        fi
    fi
}

collector_success_count() {
    local collector_file="$1" count=0 line current_status=""
    [[ -n "$collector_file" && -f "$collector_file" ]] || { printf '0\n'; return 0; }
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            if [[ "$current_status" == "OK" || "$current_status" == "cap_hit" ]]; then
                count=$((count + 1))
            fi
            current_status=""
            continue
        fi
        case "$line" in STATUS=*) current_status="${line#STATUS=}" ;; esac
    done < "$collector_file"
    if [[ "$current_status" == "OK" || "$current_status" == "cap_hit" ]]; then
        count=$((count + 1))
    fi
    printf '%s\n' "$count"
}

execution_issues_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s\n' "$LARCH_EXECUTION_ISSUES_LOG"
    elif [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md\n' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md\n' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md\n' "$REVIEW_TMPDIR"
    fi
}

append_round_log_write_failure() {
    local site="$1" round_num="$2" rc="$3" output_file="$4"
    local issues_log
    [[ -x "$APPEND_TOOL_FAILURE_SH" ]] || return 0
    issues_log="$(execution_issues_log)"
    "$APPEND_TOOL_FAILURE_SH" \
        --log "$issues_log" \
        --site "$site" \
        --tool "run-log write-round" \
        --exit-code "$rc" \
        --category "Warnings" \
        --output-file "$output_file" \
        --verdict "review-core round $round_num" \
        --redact >/dev/null 2>&1 || true
}

emit_tally_with_failure_isolation() {
    local site="$1" context="$2" output_file="$3"
    shift 3
    local issues_log rc=0
    set +e
    "$EMIT_TALLY_SH" "$@" > "$output_file" 2>&1
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        larch_err "⚠ review-core: emit-tally failed ($context, round $ROUND_NUM, rc=$rc)"
        if [[ -x "$APPEND_TOOL_FAILURE_SH" ]]; then
            issues_log="$(execution_issues_log)"
            "$APPEND_TOOL_FAILURE_SH" \
                --log "$issues_log" \
                --site "$site" \
                --tool "emit-tally.sh ($context)" \
                --exit-code "$rc" \
                --category "Warnings" \
                --output-file "$output_file" \
                --verdict "review-core round $ROUND_NUM" \
                --redact >/dev/null 2>&1 || true
        fi
    fi
    return "$rc"
}

append_review_execution_issue() {
    local entry="$1"
    command -v python3 >/dev/null 2>&1 || return 0
    python3 "$PLUGIN_ROOT/python/cli.py" run-log append-entry \
        --log "$(execution_issues_log)" \
        --category "External Reviewer Issues" \
        --entry "$entry" 2>/dev/null || true
}

ensure_prune_decision_env() {
    local dest="$REVIEW_TMPDIR/prune-decision.env"
    [[ -f "$dest" ]] && return 0
    write_prune_decision_env "$dest" "$ROUND_NUM" false skipped 0 0 0 "" false || true
}

ensure_prune_nit_env() {
    local dest="$REVIEW_TMPDIR/prune-nit.env" tmp
    [[ -f "$dest" ]] && return 0
    tmp="${dest}.tmp.$$"
    if {
        printf 'PRUNED_COUNT=0\n'
        printf 'INSCOPE_REMAINING=0\n'
        printf 'STATUS=skipped\n'
    } > "$tmp"; then
        mv -f "$tmp" "$dest" || rm -f "$tmp"
    else
        rm -f "$tmp"
    fi
}

flush_round_log() {
    local flush_err rc=0
    [[ -n "$RUN_ID" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" && -d "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    [[ -x "$LARCH_LOG_SH" ]] || return 0
    ensure_prune_decision_env
    ensure_prune_nit_env
    flush_err="$REVIEW_TMPDIR/review-core-write-round.log"
    set +e
    "$LARCH_LOG_SH" write-round \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --round "$ROUND_NUM" \
        --source-dir "$REVIEW_TMPDIR" >/dev/null 2>"$flush_err"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        larch_err "⚠ review-core: round log flush failed (round $ROUND_NUM, rc=$rc)"
        append_round_log_write_failure "5" "$ROUND_NUM" "$rc" "$flush_err"
    else
        rm -f "$flush_err"
    fi
}

emit_zero_findings_branch() {
    local zero_findings_tally_out="$REVIEW_TMPDIR/review-core-zero-findings-tally.env"
    local zero_findings_voter="$REVIEW_TMPDIR/zero-findings-voter.txt"
    local zero_emit_out="$REVIEW_TMPDIR/review-core-zero-findings-emit.env"
    local zero_voting_tally_file=""
    local zero_findings_classification_tsv_file=""
    local zero_tally_file=""
    local zero_accepted_file=""
    local zero_tally_args=()
    local zero_emit_args=()

    : > "$zero_findings_voter"
    zero_tally_args=(
        --ballot-file "$REVIEW_TMPDIR/findings.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --cursor-available "$CURSOR_AVAILABLE"
        --codex-available "$CODEX_AVAILABLE"
        --round-num "$ROUND_NUM"
        --voter-files "$zero_findings_voter"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && zero_tally_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "$panel_manifest" && -f "$panel_manifest" ]] && zero_tally_args+=(--manifest-file "$panel_manifest")
    [[ -f "$collector_results_file" ]] && zero_tally_args+=(--collector-results-file "$collector_results_file")
    [[ "$not_substantive_slots" -gt 0 ]] && zero_tally_args+=(--not-substantive-count "$not_substantive_slots")
    snapshot_review_oos_state zero-findings
    "$TALLY_VOTES_SH" "${zero_tally_args[@]}" > "$zero_findings_tally_out"
    zero_voting_tally_file=$(kv_get "$zero_findings_tally_out" VOTING_TALLY_FILE)
    zero_findings_classification_tsv_file=$(kv_get "$zero_findings_tally_out" FINDINGS_CLASSIFICATION_TSV_FILE)
    record_findings_classification_round "$zero_findings_classification_tsv_file"
    record_reviewer_prune_round "$zero_findings_classification_tsv_file"
    zero_tally_file=$(kv_get "$zero_findings_tally_out" TALLY_FILE)
    zero_accepted_file=$(kv_get "$zero_findings_tally_out" ACCEPTED_FINDINGS_FILE)
    zero_tally_file="${zero_tally_file:-$REVIEW_TMPDIR/review-tally.env}"
    zero_accepted_file="${zero_accepted_file:-$REVIEW_TMPDIR/accepted-findings.md}"

    : > "$REVIEW_TMPDIR/accepted-findings.md"
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    zero_emit_args=(
        --tally-file "$zero_tally_file"
        --accepted-findings-file "$zero_accepted_file"
        --oos-file "$REVIEW_TMPDIR/oos.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --round "$ROUND_NUM"
        --mode "$MODE"
        --scout-status "$scout_status"
        --dynamic-slots "$dynamic_slots"
        --static-slot-count "$static_slot_count"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && zero_emit_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] && zero_emit_args+=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
    if emit_tally_with_failure_isolation "5" "zero-findings" "$zero_emit_out" "${zero_emit_args[@]}"; then
        copy_to_parent "$REVIEW_TMPDIR/rejected-findings.md" rejected-findings.md
    fi
    restore_review_oos_state zero-findings
    flush_round_log
    emit_kv REVIEW_CORE_STATUS zero-findings
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE "$panel_mode"
    emit_kv PANEL_SHAPE "$panel_shape"
    [[ -n "$zero_voting_tally_file" ]] && emit_kv VOTING_TALLY_FILE "$zero_voting_tally_file"
}

join_comma() {
    local IFS=,
    printf '%s' "$*"
}

discard_paths_from_file() {
    local paths_file="$1" kind="$2"
    [[ -s "$paths_file" ]] || return 0
    if [[ "$kind" == "tracked" ]]; then
        xargs -0 git checkout -- < "$paths_file" >/dev/null 2>&1 || true
    else
        xargs -0 rm -f -- < "$paths_file" >/dev/null 2>&1 || true
    fi
}

recover_dirty_tree() {
    local summary="$REVIEW_TMPDIR/review-dirty-tree-summary.env"
    local any_dirty="false" recovery_taken="false" launcher_names=()
    local output idx sidecar status tracked_paths new_paths checkpoint_file checkpoint_status

    idx=0
    : > "$summary"
    for output in "$@"; do
        [[ -n "$output" ]] || continue
        idx=$((idx + 1))
        sidecar="${output}.dirty-tree"
        status="unknown"
        if [[ -s "$sidecar" ]]; then
            status=$(kv_get "$sidecar" STATUS)
            [[ -n "$status" ]] || status="unknown"
        fi
        if [[ "$status" == "dirty" || "$status" == "unknown" ]]; then
            any_dirty="true"
            launcher_names+=("$(basename "$output")")
            tracked_paths=""
            new_paths=""
            [[ -s "$sidecar" ]] && tracked_paths=$(kv_get "$sidecar" TRACKED_PATHS_FILE)
            [[ -s "$sidecar" ]] && new_paths=$(kv_get "$sidecar" NEW_UNTRACKED_PATHS_FILE)
            [[ -n "$tracked_paths" ]] && printf 'LAUNCHER_%s_TRACKED_PATHS_FILE=%s\n' "$idx" "$tracked_paths" >> "$summary"
            [[ -n "$new_paths" ]] && printf 'LAUNCHER_%s_NEW_UNTRACKED_PATHS_FILE=%s\n' "$idx" "$new_paths" >> "$summary"

            checkpoint_file="$REVIEW_TMPDIR/dirty-checkpoint-${idx}.env"
            "$CHECK_DIRTY_TREE_SH" --mode checkpoint > "$checkpoint_file" || true
            checkpoint_status=$(kv_get "$checkpoint_file" STATUS)
            if [[ "$checkpoint_status" == "dirty" || "$checkpoint_status" == "unknown" ]]; then
                recovery_taken="true"
                discard_paths_from_file "$tracked_paths" tracked
                discard_paths_from_file "$new_paths" untracked
            fi
        fi
    done

    {
        printf 'ANY_DIRTY=%s\n' "$any_dirty"
        printf 'LAUNCHERS_DIRTY=%s\n' "$(join_comma "${launcher_names[@]+"${launcher_names[@]}"}")"
        printf 'RECOVERY_TAKEN=%s\n' "$recovery_taken"
    } | cat - "$summary" > "${summary}.tmp"
    mv -f "${summary}.tmp" "$summary"
    copy_to_parent "$summary" review-dirty-tree-summary.env
}

log_dropped_slots() {
    local dropped_file="$1" issues_log drop_dir idx=0 slot tool reason snippet entry_file
    [[ -n "$dropped_file" && -r "$dropped_file" ]] || return 0
    if [[ -n "$REVIEW_TMPDIR" ]]; then
        cp "$dropped_file" "$REVIEW_TMPDIR/round-${ROUND_NUM}-dropped-slots.tsv" 2>/dev/null || true
    fi
    [[ -x "$APPEND_TOOL_FAILURE_SH" ]] || return 0
    issues_log="$(execution_issues_log)"
    drop_dir="$REVIEW_TMPDIR/dropped-slot-diags"
    mkdir -p "$drop_dir" 2>/dev/null || return 0
    while IFS=$'\t' read -r slot tool reason snippet || [[ -n "$slot" ]]; do
        [[ -n "$slot" ]] || continue
        idx=$((idx + 1))
        entry_file="$drop_dir/drop-${idx}.txt"
        {
            printf 'slot=%s\n' "$slot"
            printf 'tool=%s\n' "$tool"
            printf 'reason=%s\n' "$reason"
            [[ -n "$snippet" ]] && printf 'snippet=%s\n' "$snippet"
        } > "$entry_file"
        "$APPEND_TOOL_FAILURE_SH" \
            --log "$issues_log" \
            --site "5" \
            --tool "reviewer slot $slot/$tool" \
            --exit-code 1 \
            --category "External Reviewer Issues" \
            --output-file "$entry_file" \
            --verdict "dropped before fallback" \
            --redact >/dev/null 2>&1 || true
    done < "$dropped_file"
}

collect_dropped_static_outputs() {
    local dropped_file="$1" manifest_file="$2" out_file="$3"
    local slot tool _reason _snippet row row_slot row_tool row_output
    : > "$out_file"
    [[ -n "$dropped_file" && -r "$dropped_file" && -n "$manifest_file" && -f "$manifest_file" ]] || return 0
    while IFS=$'\t' read -r slot tool _reason _snippet || [[ -n "$slot" ]]; do
        [[ -n "$slot" ]] || continue
        case "$slot" in dyn-*) continue ;; esac
        while IFS= read -r row || [[ -n "$row" ]]; do
            [[ -n "$row" ]] || continue
            row_slot=$(printf '%s' "$row" | jq -r '.slot // ""')
            row_tool=$(printf '%s' "$row" | jq -r '.tool // ""')
            if [[ "$row_slot" == "$slot" && "$row_tool" == "$tool" ]]; then
                row_output=$(printf '%s' "$row" | jq -r '.output // ""')
                [[ -n "$row_output" ]] && printf '%s\n' "$row_output" >> "$out_file"
                break
            fi
        done < "$manifest_file"
    done < "$dropped_file"
}

normalize_reviewer_output_base() {
    local base="$1" stem ext=""
    base="${base##*/}"
    case "$base" in
        *.txt) stem="${base%.txt}"; ext=".txt" ;;
        *) stem="$base" ;;
    esac
    while :; do
        case "$stem" in
            *-phase2) stem="${stem%-phase2}" ;;
            *-phase3) stem="${stem%-phase3}" ;;
            *-retry) stem="${stem%-retry}" ;;
            *) break ;;
        esac
    done
    printf '%s%s' "$stem" "$ext"
}

static_slug_for_reviewer_file() {
    local base="$1"
    base=$(normalize_reviewer_output_base "$base")
    case "$base" in
        cursor-specialist-*-output.txt)
            base="${base#cursor-specialist-}"
            printf '%s\n' "${base%-output.txt}"
            ;;
        codex-specialist-*-output.txt)
            base="${base#codex-specialist-}"
            printf '%s\n' "${base%-output.txt}"
            ;;
        *) return 1 ;;
    esac
}

claude_static_output_is_success() {
    local file="$1"
    [[ -s "$file" ]] || return 1
    if grep -Eq '(^|[^A-Z_])NOT_SUBSTANTIVE([^A-Z_]|$)' "$file" 2>/dev/null; then
        return 1
    fi
    return 0
}

static_archetype_coverage_ok() {
    local collector_file="$1" success_file rejected_file current_reviewer_file="" current_status="" current_base normalized_base slug missing="" static_output
    shift || true
    [[ -n "$collector_file" && -f "$collector_file" ]] || {
        printf 'missing collector results'
        return 1
    }
    success_file="$REVIEW_TMPDIR/static-success-slugs.txt"
    rejected_file="$REVIEW_TMPDIR/static-collector-rejected-bases.txt"
    : > "$success_file"
    : > "$rejected_file"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            if [[ -n "$current_status" ]]; then
                current_base=$(basename "${current_reviewer_file:-}")
                normalized_base=$(normalize_reviewer_output_base "$current_base")
                if slug=$(static_slug_for_reviewer_file "$current_base" 2>/dev/null); then
                    [[ "$current_status" == "OK" || "$current_status" == "cap_hit" ]] && printf '%s\n' "$slug" >> "$success_file"
                    [[ "$current_status" != "OK" && "$current_status" != "cap_hit" ]] && printf '%s\n' "$normalized_base" >> "$rejected_file"
                fi
            fi
            current_reviewer_file=""
            current_status=""
            continue
        fi
        case "$line" in
            REVIEWER_FILE=*) current_reviewer_file="${line#REVIEWER_FILE=}" ;;
            STATUS=*) current_status="${line#STATUS=}" ;;
        esac
    done < "$collector_file"
    if [[ -n "$current_status" ]]; then
        current_base=$(basename "${current_reviewer_file:-}")
        normalized_base=$(normalize_reviewer_output_base "$current_base")
        if slug=$(static_slug_for_reviewer_file "$current_base" 2>/dev/null); then
            [[ "$current_status" == "OK" || "$current_status" == "cap_hit" ]] && printf '%s\n' "$slug" >> "$success_file"
            [[ "$current_status" != "OK" && "$current_status" != "cap_hit" ]] && printf '%s\n' "$normalized_base" >> "$rejected_file"
        fi
    fi
    for static_output in "$@"; do
        current_base=$(basename "$static_output")
        if slug=$(static_slug_for_reviewer_file "$current_base" 2>/dev/null); then
            if ! grep -Fxq "$(normalize_reviewer_output_base "$current_base")" "$rejected_file" 2>/dev/null \
                && claude_static_output_is_success "$static_output"; then
                printf '%s\n' "$slug" >> "$success_file"
            fi
        fi
    done
    expected_file="$REVIEW_TMPDIR/static-expected-slugs.txt"
    : > "$expected_file"
    if [[ -n "${panel_manifest:-}" && -f "$panel_manifest" ]]; then
        while IFS= read -r _expected_row || [[ -n "$_expected_row" ]]; do
            [[ -n "$_expected_row" ]] || continue
            _expected_output=$(printf '%s' "$_expected_row" | jq -r 'select(has("agent")) | .output // empty' 2>/dev/null || true)
            [[ -n "$_expected_output" ]] || continue
            if slug=$(static_slug_for_reviewer_file "$(basename "$_expected_output")" 2>/dev/null); then
                printf '%s\n' "$slug" >> "$expected_file"
            fi
        done < "$panel_manifest"
    else
        printf '%s\n' correctness edge-cases testing > "$expected_file"
    fi
    if [[ ! -s "$expected_file" ]]; then
        return 0
    fi
    while IFS= read -r slug || [[ -n "$slug" ]]; do
        [[ -n "$slug" ]] || continue
        if ! grep -Fxq "$slug" "$success_file" 2>/dev/null; then
            missing="${missing}${missing:+,}$slug"
        fi
    done < <(sort -u "$expected_file")
    if [[ -n "$missing" ]]; then
        printf 'no successful static reviewer for archetype(s): %s' "$missing"
        return 1
    fi
    return 0
}

gather_out="$REVIEW_TMPDIR/review-core-gather.env"
gather_args=(--mode "$MODE" --output-dir "$REVIEW_TMPDIR")
[[ -n "$DESCRIPTION_TEXT" ]] && gather_args+=(--description-text "$DESCRIPTION_TEXT")
[[ -n "$SCOPE_FILES" ]] && gather_args+=(--scope-files "$SCOPE_FILES")
"$GATHER_CONTEXT_SH" "${gather_args[@]}" > "$gather_out"

DIFF_FILE="${DIFF_FILE:-$(kv_get "$gather_out" DIFF_FILE)}"
SCOPE_FILES="${SCOPE_FILES:-$(kv_get "$gather_out" FILE_LIST_FILE)}"
COMMIT_COUNT="${COMMIT_COUNT:-$(kv_get "$gather_out" COMMIT_COUNT)}"
MODE="$(kv_get "$gather_out" MODE)"
MODE="${MODE:-diff}"
scope_count=$(kv_get "$gather_out" SCOPE_FILES_COUNT)
if [[ "$MODE" == "description" && "${scope_count:-0}" == "0" ]]; then
    : > "$REVIEW_TMPDIR/findings.md"
    : > "$REVIEW_TMPDIR/accepted-findings.md"
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    recover_dirty_tree
    flush_round_log
    emit_kv REVIEW_CORE_STATUS zero-findings
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv SCOUT_STATUS na
    emit_kv DYNAMIC_SLOTS 0
    emit_kv SCOUT_MANIFEST ""
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE normal
    emit_kv PANEL_SHAPE "$PANEL"
    exit 0
fi

dispatch_out="$REVIEW_TMPDIR/review-core-dispatch.env"
dispatch_args=(
    --mode "$MODE"
    --review-tmpdir "$REVIEW_TMPDIR"
    --panel "$PANEL"
    --codex-available "$CODEX_AVAILABLE"
    --cursor-available "$CURSOR_AVAILABLE"
    --commit-count "${COMMIT_COUNT:-0}"
    --timing-task-prefix "review-round${ROUND_NUM}"
    --dynamic-archetypes "$DYNAMIC_ARCHETYPES"
    --round-num "$ROUND_NUM"
)
[[ -n "$DIFF_FILE" ]] && dispatch_args+=(--diff-file "$DIFF_FILE")
[[ -n "$SCOPE_FILES" ]] && dispatch_args+=(--scope-files "$SCOPE_FILES")
[[ -n "$PLAN_FILE" ]] && dispatch_args+=(--plan-file "$PLAN_FILE")
[[ -n "$FEATURE_FILE" ]] && dispatch_args+=(--feature-file "$FEATURE_FILE")
[[ -n "$DESCRIPTION_TEXT" ]] && dispatch_args+=(--description-text "$DESCRIPTION_TEXT")
[[ -n "$SESSION_ENV_PATH" ]] && dispatch_args+=(--session-env-path "$SESSION_ENV_PATH")
[[ -n "$PRUNE_LEDGER" ]] && dispatch_args+=(--prune-ledger "$PRUNE_LEDGER")
[[ -f "$REVIEW_TMPDIR/competition-notice.md" ]] && dispatch_args+=(--competition-notice-file "$REVIEW_TMPDIR/competition-notice.md")
set +e
"$DISPATCH_PANEL_SH" "${dispatch_args[@]}" > "$dispatch_out"
dispatch_rc=$?
set -e
if [[ "$dispatch_rc" -ne 0 ]]; then
    ensure_prune_decision_env
    ensure_prune_nit_env
    flush_round_log
    emit_kv REVIEW_CORE_STATUS panel-failed
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE normal
    emit_kv PANEL_SHAPE "$PANEL"
    emit_kv THRESHOLD_REASON "dispatch-panel exited rc=$dispatch_rc"
    exit 2
fi

external_outputs=$(kv_get "$dispatch_out" EXTERNAL_OUTPUT_FILES)
claude_outputs=$(kv_get "$dispatch_out" CLAUDE_OUTPUT_FILES)
panel_mode=$(kv_get "$dispatch_out" PANEL_MODE)
panel_shape=$(kv_get "$dispatch_out" PANEL_SHAPE)
panel_manifest=$(kv_get "$dispatch_out" PANEL_MANIFEST)
dropped_slots_file=$(kv_get "$dispatch_out" DROPPED_SLOTS_FILE)
scout_status=$(kv_get "$dispatch_out" SCOUT_STATUS)
dynamic_slots=$(kv_get "$dispatch_out" DYNAMIC_SLOTS)
scout_manifest=$(kv_get "$dispatch_out" SCOUT_MANIFEST)
scout_fail_reason=$(kv_get "$dispatch_out" SCOUT_FAIL_REASON)
static_slot_count=$(kv_get "$dispatch_out" STATIC_SLOT_COUNT)
panel_pruned_empty=$(kv_get "$dispatch_out" PANEL_PRUNED_EMPTY)
prune_status=$(kv_get "$dispatch_out" PRUNE_STATUS)
pruned_combos=$(kv_get "$dispatch_out" PRUNED_COMBOS)
panel_mode="${panel_mode:-waterfall}"
panel_shape="${panel_shape:-$PANEL}"
scout_status="${scout_status:-na}"
scout_fail_reason="${scout_fail_reason:-}"
dynamic_slots="${dynamic_slots:-0}"
static_slot_count="${static_slot_count:-0}"
panel_pruned_empty="${panel_pruned_empty:-false}"
pruned_combos="${pruned_combos:-}"
{
    printf 'SCOUT_STATUS=%s\n' "$scout_status"
    [[ -n "$scout_fail_reason" ]] && printf 'SCOUT_FAIL_REASON=%s\n' "$scout_fail_reason"
    printf 'DYNAMIC_SLOTS=%s\n' "$dynamic_slots"
    printf 'SCOUT_MANIFEST=%s\n' "$scout_manifest"
} > "$REVIEW_TMPDIR/scout-round${ROUND_NUM}-status.env"
emit_kv SCOUT_STATUS "$scout_status"
[[ -n "$scout_fail_reason" ]] && emit_kv SCOUT_FAIL_REASON "$scout_fail_reason"
emit_kv DYNAMIC_SLOTS "$dynamic_slots"
[[ -n "$scout_manifest" ]] && emit_kv SCOUT_MANIFEST "$scout_manifest"
[[ -n "$pruned_combos" ]] && emit_kv PRUNED_COMBOS "$pruned_combos"
emit_kv PANEL_PRUNED_EMPTY "$panel_pruned_empty"

if [[ "$panel_pruned_empty" == "true" && "${prune_status:-}" == "pruned-empty" ]]; then
    snapshot_review_oos_state prune-skipped
    : > "$REVIEW_TMPDIR/findings.md"
    : > "$REVIEW_TMPDIR/accepted-findings.md"
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    : > "$REVIEW_TMPDIR/oos.md"
    : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    {
        printf '# Code Review Voting Tally\n\n'
        printf 'Round skipped: all reviewer combos pruned.\n'
    } > "$REVIEW_TMPDIR/voting-tally.md"
    restore_review_oos_state prune-skipped
    ensure_prune_decision_env
    ensure_prune_nit_env
    flush_round_log
    larch_err "→ review: round $ROUND_NUM skipped — all reviewer combos pruned"
    emit_kv REVIEW_CORE_STATUS prune-skipped
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE "$panel_mode"
    emit_kv PANEL_SHAPE "$panel_shape"
    exit 0
fi

collect_out="$REVIEW_TMPDIR/review-core-collect.env"
collect_args=(--mode "$MODE" --timeout 1860 --findings-file "$REVIEW_TMPDIR/findings.md" --oos-file "$REVIEW_TMPDIR/oos.md")
[[ -n "$SESSION_ENV_PATH" ]] && collect_args+=(--session-env-path "$SESSION_ENV_PATH")
if [[ -n "$external_outputs" ]]; then
    collect_args+=(--external-output-files)
    # shellcheck disable=SC2206
    external_array=($external_outputs)
    collect_args+=("${external_array[@]}")
else
    external_array=()
fi
if [[ -n "$claude_outputs" ]]; then
    collect_args+=(--claude-output-files)
    # shellcheck disable=SC2206
    claude_array=($claude_outputs)
    collect_args+=("${claude_array[@]}")
else
    claude_array=()
fi
larch_err "→ review: consolidating findings"
"$COLLECT_FINDINGS_SH" "${collect_args[@]}" > "$collect_out"
dropped_static_outputs_file="$REVIEW_TMPDIR/dropped-static-outputs.txt"
collect_dropped_static_outputs "$dropped_slots_file" "$panel_manifest" "$dropped_static_outputs_file"
dropped_static_outputs=()
if [[ -s "$dropped_static_outputs_file" ]]; then
    while IFS= read -r dropped_output || [[ -n "$dropped_output" ]]; do
        [[ -n "$dropped_output" ]] && dropped_static_outputs+=("$dropped_output")
    done < "$dropped_static_outputs_file"
fi
recover_dirty_tree "${external_array[@]+"${external_array[@]}"}" "${claude_array[@]+"${claude_array[@]}"}" "${dropped_static_outputs[@]+"${dropped_static_outputs[@]}"}"

# Reviewer failure threshold: hard-stop the round when >50% of the intended
# panel slots failed. THRESHOLD_OK=false → REVIEW_CORE_STATUS=panel-failed and
# exit 2 so review-and-fix.sh propagates the stall to /implement Step 5.
collector_results_file="$REVIEW_TMPDIR/collector-results.env"
threshold_out="$REVIEW_TMPDIR/review-core-threshold.env"
launched_slots="$static_slot_count"
threshold_args=(
    --collector-results-file "$collector_results_file"
    --panel "$panel_shape"
    --intended-slots "$static_slot_count"
    --launched-slots "$launched_slots"
    --round-num "$ROUND_NUM"
)
if [[ -n "$dropped_slots_file" && -r "$dropped_slots_file" ]]; then
    log_dropped_slots "$dropped_slots_file"
    threshold_args+=(--dropped-slots-file "$dropped_slots_file")
fi
if (( ${#external_array[@]} > 0 || ${#claude_array[@]} > 0 )); then
    threshold_args+=(--reviewer-output-files)
    threshold_args+=("${external_array[@]+"${external_array[@]}"}" "${claude_array[@]+"${claude_array[@]}"}")
fi
"$CHECK_THRESHOLD_SH" "${threshold_args[@]}" > "$threshold_out"
threshold_ok=$(kv_get "$threshold_out" THRESHOLD_OK)
threshold_reason=$(kv_get "$threshold_out" THRESHOLD_REASON)
not_substantive_slots=$(kv_get "$threshold_out" NOT_SUBSTANTIVE_SLOTS)
not_substantive_slots="${not_substantive_slots:-0}"
if [[ "$threshold_ok" != "false" ]]; then
    launched_success_count=$(collector_success_count "$collector_results_file")
    if (( launched_success_count == 0 )); then
        threshold_ok=false
        threshold_reason="no successful launched reviewer output"
        {
            cat "$threshold_out"
            printf 'COVERAGE_GATE_OK=false\n'
            printf 'COVERAGE_GATE_REASON=%s\n' "$threshold_reason"
        } > "${threshold_out}.tmp"
        mv -f "${threshold_out}.tmp" "$threshold_out"
    fi
fi
if [[ "$threshold_ok" != "false" ]]; then
    coverage_reason=$(static_archetype_coverage_ok "$collector_results_file" "${external_array[@]+"${external_array[@]}"}" "${claude_array[@]+"${claude_array[@]}"}" || true)
    if [[ -n "$coverage_reason" ]]; then
        threshold_ok=false
        threshold_reason="$coverage_reason"
        {
            cat "$threshold_out"
            printf 'COVERAGE_GATE_OK=false\n'
            printf 'COVERAGE_GATE_REASON=%s\n' "$coverage_reason"
        } > "${threshold_out}.tmp"
        mv -f "${threshold_out}.tmp" "$threshold_out"
    fi
fi
if [[ "$threshold_ok" == "false" ]]; then
    panel_failed_tally="$REVIEW_TMPDIR/review-core-panel-failed-tally.env"
    panel_failed_emit_out="$REVIEW_TMPDIR/review-core-panel-failed-emit.env"
    : > "$REVIEW_TMPDIR/accepted-findings.md"
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    cat > "$panel_failed_tally" <<EOF
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
NEUTRAL_COUNT=0
EOF
    panel_failed_emit_args=(
        --tally-file "$panel_failed_tally"
        --accepted-findings-file "$REVIEW_TMPDIR/accepted-findings.md"
        --oos-file "$REVIEW_TMPDIR/oos.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --round "$ROUND_NUM"
        --mode "$MODE"
        --scout-status "$scout_status"
        --dynamic-slots "$dynamic_slots"
        --static-slot-count "$static_slot_count"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && panel_failed_emit_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] && panel_failed_emit_args+=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
    if emit_tally_with_failure_isolation "5" "panel-failed" "$panel_failed_emit_out" "${panel_failed_emit_args[@]}"; then
        copy_to_parent "$REVIEW_TMPDIR/rejected-findings.md" rejected-findings.md
        copy_to_parent "$REVIEW_TMPDIR/oos-accepted-review.md" oos-accepted-review.md
    fi
    flush_round_log
    emit_kv REVIEW_CORE_STATUS panel-failed
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE "$panel_mode"
    emit_kv PANEL_SHAPE "$panel_shape"
    emit_kv THRESHOLD_REASON "$threshold_reason"
    exit 2
fi

findings_count=$(kv_get "$collect_out" FINDINGS_COUNT)
findings_count="${findings_count:-0}"
if [[ "$findings_count" == "0" ]]; then
    emit_zero_findings_branch
    exit 0
fi

aggregate_out="$REVIEW_TMPDIR/review-core-aggregate.env"
aggregate_args=(
    --findings-file "$REVIEW_TMPDIR/findings.md"
    --review-tmpdir "$REVIEW_TMPDIR"
    --codex-present "$CODEX_AVAILABLE"
    --cursor-present "$CURSOR_AVAILABLE"
    --mode "$MODE"
)
[[ -n "$SESSION_ENV_PATH" ]] && aggregate_args+=(--session-env-path "$SESSION_ENV_PATH")
[[ -n "$DIFF_FILE" ]] && aggregate_args+=(--diff-file "$DIFF_FILE")
[[ -n "$PLAN_FILE" ]] && aggregate_args+=(--plan-file "$PLAN_FILE")
aggregate_stderr="$REVIEW_TMPDIR/review-core-aggregate.stderr"
set +e
"$AGGREGATE_FINDINGS_SH" "${aggregate_args[@]}" > "$aggregate_out" 2>"$aggregate_stderr"
aggregate_rc=$?
set -e
if [[ -s "$aggregate_stderr" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"
    done < "$aggregate_stderr"
fi
if [[ "$aggregate_rc" -ne 0 ]]; then
    larch_err "⚠ review-core: aggregate-findings exited non-zero (rc=$aggregate_rc; see $aggregate_stderr)"
    append_review_execution_issue "- **review-core / aggregate-findings**: subprocess exited with rc=$aggregate_rc (unexpected; see $aggregate_stderr)."
fi

aggregate_reason=$(kv_get "$aggregate_out" REASON)
if [[ "$aggregate_reason" == "validation-exhausted" ]]; then
    agg_exhaust_tally="$REVIEW_TMPDIR/review-core-aggregator-exhaust-tally.env"
    agg_exhaust_emit_out="$REVIEW_TMPDIR/review-core-aggregator-exhaust-emit.env"
    agg_exhaust_classification_tsv_file=""
    tally_args=(
        --ballot-file "$REVIEW_TMPDIR/findings.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --cursor-available "$CURSOR_AVAILABLE"
        --codex-available "$CODEX_AVAILABLE"
        --round-num "$ROUND_NUM"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && tally_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "$SCOPE_FILES" && -s "$SCOPE_FILES" ]] && tally_args+=(--scope-files "$SCOPE_FILES")
    [[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && tally_args+=(--plan-file "$PLAN_FILE")
    [[ -n "$panel_manifest" && -f "$panel_manifest" ]] && tally_args+=(--manifest-file "$panel_manifest")
    [[ -f "$collector_results_file" ]] && tally_args+=(--collector-results-file "$collector_results_file")
    [[ "$not_substantive_slots" -gt 0 ]] && tally_args+=(--not-substantive-count "$not_substantive_slots")
    "$TALLY_VOTES_SH" "${tally_args[@]}" > "$agg_exhaust_tally"
    agg_exhaust_classification_tsv_file=$(kv_get "$agg_exhaust_tally" FINDINGS_CLASSIFICATION_TSV_FILE)
    record_findings_classification_round "$agg_exhaust_classification_tsv_file"
    agg_exhaust_emit_args=(
        --tally-file "$agg_exhaust_tally"
        --accepted-findings-file "$REVIEW_TMPDIR/accepted-findings.md"
        --oos-file "$REVIEW_TMPDIR/oos.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --round "$ROUND_NUM"
        --mode "$MODE"
        --scout-status "$scout_status"
        --dynamic-slots "$dynamic_slots"
        --static-slot-count "$static_slot_count"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && agg_exhaust_emit_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] && agg_exhaust_emit_args+=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
    if emit_tally_with_failure_isolation "5" "aggregator-validation-exhausted" "$agg_exhaust_emit_out" "${agg_exhaust_emit_args[@]}"; then
        copy_to_parent "$REVIEW_TMPDIR/rejected-findings.md" rejected-findings.md
        copy_to_parent "$REVIEW_TMPDIR/oos-accepted-review.md" oos-accepted-review.md
    fi
    flush_round_log
    emit_kv REVIEW_CORE_STATUS aggregator-validation-exhausted
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE "$panel_mode"
    emit_kv PANEL_SHAPE "$panel_shape"
    emit_kv THRESHOLD_REASON aggregation-validation-exhausted
    [[ -n "$agg_exhaust_classification_tsv_file" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$agg_exhaust_classification_tsv_file"
    exit 2
fi

aggregate_merged_count_raw=$(kv_get "$aggregate_out" MERGED_COUNT)
if [[ "$aggregate_reason" == "ok" && "$aggregate_merged_count_raw" == "0" ]]; then
    emit_zero_findings_branch
    exit 0
fi

prune_out="$REVIEW_TMPDIR/review-core-prune-nit.env"
set +e
"$PRUNE_NITS_SH" \
    --findings-file "$REVIEW_TMPDIR/findings.md" \
    --input-mode code > "$prune_out"
_prune_rc=$?
set -e
if [[ "$_prune_rc" -ne 0 ]]; then
    append_review_execution_issue "- **review-core / prune-nit-findings**: subprocess exited with rc=$_prune_rc (unexpected; failing open)."
fi
if ! cp -f "$prune_out" "$REVIEW_TMPDIR/prune-nit.env"; then
    append_review_execution_issue "- **review-core / prune-nit-findings**: failed to persist prune-nit.env."
fi
_prune_count=$(kv_get "$prune_out" PRUNED_COUNT)
_prune_count="${_prune_count:-0}"
if [[ "${_prune_count}" != "0" ]]; then
    larch_err "→ review: nit post-aggregate filter marked ${_prune_count} finding(s) as [OUT_OF_SCOPE]"
fi

tally_out="$REVIEW_TMPDIR/review-core-tally.env"

# Dispatch the code-review voting panel and collect vote-output files.
# Shrink-not-backfill: Claude (always; the floor) plus each available external.
# An unavailable external is skipped, not replaced by a duplicate judge; a
# failed/empty voter is treated as an abstention by reducing the eligible count.
voter_files=()
voter_1_tool=""
voter_2_tool=""
voter_3_tool=""
voter_1_status=""
voter_2_status=""
voter_3_status=""
voters_out="$REVIEW_TMPDIR/review-core-voters.env"
voter_args=(
    --ballot-file "$REVIEW_TMPDIR/findings.md"
    --review-tmpdir "$REVIEW_TMPDIR"
    --codex-available "$CODEX_AVAILABLE"
    --cursor-available "$CURSOR_AVAILABLE"
    --round-num "$ROUND_NUM"
)
[[ -n "$SESSION_ENV_PATH" ]] && voter_args+=(--session-env-path "$SESSION_ENV_PATH")
[[ -n "$DIFF_FILE" ]] && voter_args+=(--diff-file "$DIFF_FILE")
[[ -n "$PLAN_FILE" ]] && voter_args+=(--plan-file "$PLAN_FILE")
"$DISPATCH_VOTERS_SH" "${voter_args[@]}" > "$voters_out"
voter_1_path=$(kv_get "$voters_out" VOTER_1_PATH)
voter_2_path=$(kv_get "$voters_out" VOTER_2_PATH)
voter_3_path=$(kv_get "$voters_out" VOTER_3_PATH)
voter_1_status=$(kv_get "$voters_out" VOTER_1_STATUS)
voter_2_status=$(kv_get "$voters_out" VOTER_2_STATUS)
voter_3_status=$(kv_get "$voters_out" VOTER_3_STATUS)
voter_1_tool=$(kv_get "$voters_out" VOTER_1_TOOL)
voter_2_tool=$(kv_get "$voters_out" VOTER_2_TOOL)
voter_3_tool=$(kv_get "$voters_out" VOTER_3_TOOL)
# Only include voter files whose dispatch succeeded; failed voters are
# treated as abstentions by reducing the eligible voter count.
[[ "$voter_1_status" != "failed" && -s "$voter_1_path" ]] && voter_files+=("$voter_1_path")
[[ "$voter_2_status" != "failed" && -s "$voter_2_path" ]] && voter_files+=("$voter_2_path")
[[ "$voter_3_status" != "failed" && -s "$voter_3_path" ]] && voter_files+=("$voter_3_path")

tally_args=(
    --ballot-file "$REVIEW_TMPDIR/findings.md"
    --review-tmpdir "$REVIEW_TMPDIR"
    --cursor-available "$CURSOR_AVAILABLE"
    --codex-available "$CODEX_AVAILABLE"
    --round-num "$ROUND_NUM"
)
[[ -n "$SESSION_ENV_PATH" ]] && tally_args+=(--session-env-path "$SESSION_ENV_PATH")
[[ -n "$SCOPE_FILES" && -s "$SCOPE_FILES" ]] && tally_args+=(--scope-files "$SCOPE_FILES")
[[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && tally_args+=(--plan-file "$PLAN_FILE")
[[ -n "$panel_manifest" && -f "$panel_manifest" ]] && tally_args+=(--manifest-file "$panel_manifest")
[[ -f "$collector_results_file" ]] && tally_args+=(--collector-results-file "$collector_results_file")
[[ "$not_substantive_slots" -gt 0 ]] && tally_args+=(--not-substantive-count "$not_substantive_slots")
if [[ "${#voter_files[@]}" -gt 0 ]]; then
    tally_args+=(--voter-files "${voter_files[@]}")
fi
"$TALLY_VOTES_SH" "${tally_args[@]}" > "$tally_out"

out_of_scope_drift_count=$(kv_get "$tally_out" OUT_OF_SCOPE_DRIFT_COUNT)
out_of_scope_drift_count="${out_of_scope_drift_count:-0}"

tally_status=$(kv_get "$tally_out" TALLY_STATUS)
accepted_count=$(kv_get "$tally_out" ACCEPTED_COUNT)
rejected_count=$(kv_get "$tally_out" REJECTED_COUNT)
exonerated_count=$(kv_get "$tally_out" EXONERATED_COUNT)
neutral_count=$(kv_get "$tally_out" NEUTRAL_COUNT)
exonerated_count="${exonerated_count:-0}"
neutral_count="${neutral_count:-0}"
tally_file=$(kv_get "$tally_out" TALLY_FILE)
accepted_file=$(kv_get "$tally_out" ACCEPTED_FINDINGS_FILE)
voting_skipped_warning=$(kv_get "$tally_out" VOTING_SKIPPED_WARNING)
yield_tsv_file=$(kv_get "$tally_out" YIELD_TSV_FILE)
findings_classification_tsv_file=$(kv_get "$tally_out" FINDINGS_CLASSIFICATION_TSV_FILE)
[[ -n "$voting_skipped_warning" ]] && emit_kv VOTING_SKIPPED_WARNING "$voting_skipped_warning"
[[ -n "$yield_tsv_file" ]] && emit_kv YIELD_TSV_FILE "$yield_tsv_file"
record_findings_classification_round "$findings_classification_tsv_file"
accepted_count="${accepted_count:-0}"
rejected_count="${rejected_count:-0}"
tally_file="${tally_file:-$REVIEW_TMPDIR/review-tally.env}"
accepted_file="${accepted_file:-$REVIEW_TMPDIR/accepted-findings.md}"

# Surface per-voter status so /implement can include it in the code-review-tally
# larch-log batch.
[[ -n "$voter_1_tool"   ]] && emit_kv VOTER_1_TOOL   "$voter_1_tool"
[[ -n "$voter_2_tool"   ]] && emit_kv VOTER_2_TOOL   "$voter_2_tool"
[[ -n "$voter_3_tool"   ]] && emit_kv VOTER_3_TOOL   "$voter_3_tool"
[[ -n "$voter_1_status" ]] && emit_kv VOTER_1_STATUS "$voter_1_status"
[[ -n "$voter_2_status" ]] && emit_kv VOTER_2_STATUS "$voter_2_status"
[[ -n "$voter_3_status" ]] && emit_kv VOTER_3_STATUS "$voter_3_status"
voting_tally_file=$(kv_get "$tally_out" VOTING_TALLY_FILE)
[[ -n "$voting_tally_file" ]] && emit_kv VOTING_TALLY_FILE "$voting_tally_file"

if [[ "$tally_status" == "main-agent-vote-required" ]]; then
    main_agent_emit_out="$REVIEW_TMPDIR/review-core-main-agent-emit.env"
    main_agent_emit_args=(
        --tally-file "$tally_file"
        --accepted-findings-file "$accepted_file"
        --oos-file "$REVIEW_TMPDIR/oos.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --round "$ROUND_NUM"
        --mode "$MODE"
        --scout-status "$scout_status"
        --dynamic-slots "$dynamic_slots"
        --static-slot-count "$static_slot_count"
    )
    [[ -n "$SESSION_ENV_PATH" ]] && main_agent_emit_args+=(--session-env-path "$SESSION_ENV_PATH")
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] && main_agent_emit_args+=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    if emit_tally_with_failure_isolation "5" "main-agent-vote-required" "$main_agent_emit_out" "${main_agent_emit_args[@]}"; then
        copy_to_parent "$REVIEW_TMPDIR/rejected-findings.md" rejected-findings.md
        copy_to_parent "$REVIEW_TMPDIR/oos-accepted-review.md" oos-accepted-review.md
    fi
    record_reviewer_prune_round "$findings_classification_tsv_file"
    flush_round_log
    emit_kv REVIEW_CORE_STATUS main-agent-vote-required
    emit_kv ROUND_NUM "$ROUND_NUM"
    emit_kv ACCEPTED_COUNT 0
    emit_kv REJECTED_COUNT 0
    emit_kv EXONERATED_COUNT 0
    emit_kv NEUTRAL_COUNT 0
    emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
    emit_kv ACCEPTED_FINDINGS_FILE "$REVIEW_TMPDIR/accepted-findings.md"
    emit_kv REJECTED_FINDINGS_FILE "$REVIEW_TMPDIR/rejected-findings.md"
    emit_kv PANEL_MODE "$panel_mode"
    emit_kv PANEL_SHAPE "$panel_shape"
    emit_kv OUT_OF_SCOPE_DRIFT_COUNT "$out_of_scope_drift_count"
    [[ -n "$findings_classification_tsv_file" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$findings_classification_tsv_file"
    exit 0
fi

record_reviewer_prune_round "$findings_classification_tsv_file"

emit_out="$REVIEW_TMPDIR/review-core-emit.env"
emit_args=(
    --tally-file "$tally_file"
    --accepted-findings-file "$accepted_file"
    --oos-file "$REVIEW_TMPDIR/oos.md"
    --review-tmpdir "$REVIEW_TMPDIR"
    --round "$ROUND_NUM"
    --mode "$MODE"
)
[[ -n "$SESSION_ENV_PATH" ]] && emit_args+=(--session-env-path "$SESSION_ENV_PATH")
[[ -n "${IMPLEMENT_TMPDIR:-}" ]] && emit_args+=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
emit_args+=(--scout-status "$scout_status")
emit_args+=(--dynamic-slots "$dynamic_slots")
emit_args+=(--static-slot-count "$static_slot_count")
"$EMIT_TALLY_SH" "${emit_args[@]}" > "$emit_out"

rejected_file="$REVIEW_TMPDIR/rejected-findings.md"
copy_to_parent "$rejected_file" rejected-findings.md
copy_to_parent "$REVIEW_TMPDIR/oos-accepted-review.md" oos-accepted-review.md
flush_round_log

status="ok"
if [[ "$MODE" == "diff" && "$accepted_count" -gt 0 ]]; then
    if [[ "$ROUND_NUM" -ge 5 ]]; then
        status="cap-reached"
    else
        status="fix-required"
    fi
fi

emit_kv REVIEW_CORE_STATUS "$status"
emit_kv ROUND_NUM "$ROUND_NUM"
emit_kv ACCEPTED_COUNT "$accepted_count"
emit_kv REJECTED_COUNT "$rejected_count"
emit_kv EXONERATED_COUNT "$exonerated_count"
emit_kv NEUTRAL_COUNT "$neutral_count"
emit_kv FINDINGS_FILE "$REVIEW_TMPDIR/findings.md"
emit_kv ACCEPTED_FINDINGS_FILE "$accepted_file"
emit_kv REJECTED_FINDINGS_FILE "$rejected_file"
emit_kv OUT_OF_SCOPE_DRIFT_COUNT "$out_of_scope_drift_count"
emit_kv PANEL_MODE "$panel_mode"
emit_kv PANEL_SHAPE "$panel_shape"
[[ -n "$findings_classification_tsv_file" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$findings_classification_tsv_file"
exit 0
