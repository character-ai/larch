#!/usr/bin/env bash
# review-core.sh — Single-round /review state machine.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

ensure_breadcrumb_fd() {
    if [[ -z "${LARCH_QUIET_BREADCRUMB_FD:-}" ]]; then
        if [[ "${LARCH_QUIET_PID:-}" == "$$" ]]; then
            exec 5>&3
        else
            exec 5>&1
        fi
        export LARCH_QUIET_BREADCRUMB_FD=5
    fi
}
ensure_breadcrumb_fd

usage() {
    larch_err "Usage: review-core.sh --mode diff|description --output-dir DIR --codex-available true|false --cursor-available true|false [--dynamic-archetypes 0-8] [context flags]"
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
    [0-8]) ;;
    *) larch_err "review-core.sh: --dynamic-archetypes/LARCH_DYNAMIC_ARCHETYPES_MAX must be an integer from 0 to 8"; exit 2 ;;
esac
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "review-core.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "review-core.sh: --round-num must be a positive integer"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

: "$RUN_ID"

GATHER_CONTEXT_SH="${REVIEW_CORE_GATHER_CONTEXT_SH:-$SCRIPT_DIR/gather-context.sh}"
DISPATCH_PANEL_SH="${REVIEW_CORE_DISPATCH_PANEL_SH:-$SCRIPT_DIR/dispatch-panel.sh}"
COLLECT_FINDINGS_SH="${REVIEW_CORE_COLLECT_FINDINGS_SH:-$SCRIPT_DIR/collect-findings.sh}"
AGGREGATE_FINDINGS_SH="${REVIEW_CORE_AGGREGATE_FINDINGS_SH:-$SCRIPT_DIR/aggregate-findings.sh}"
TALLY_VOTES_SH="${REVIEW_CORE_TALLY_VOTES_SH:-$SCRIPT_DIR/tally-code-votes.sh}"
EMIT_TALLY_SH="${REVIEW_CORE_EMIT_TALLY_SH:-$SCRIPT_DIR/emit-tally.sh}"
CHECK_DIRTY_TREE_SH="${REVIEW_CORE_CHECK_DIRTY_TREE_SH:-$PLUGIN_ROOT/scripts/check-mid-run-dirty-tree.sh}"
CHECK_THRESHOLD_SH="${REVIEW_CORE_CHECK_THRESHOLD_SH:-$SCRIPT_DIR/check-reviewer-failure-threshold.sh}"
DISPATCH_VOTERS_SH="${REVIEW_CORE_DISPATCH_VOTERS_SH:-$PLUGIN_ROOT/scripts/dispatch-code-voters.sh}"
LARCH_LOG_SH="${REVIEW_CORE_LARCH_LOG_SH:-$PLUGIN_ROOT/scripts/larch-log.sh}"
APPEND_TOOL_FAILURE_SH="${REVIEW_CORE_APPEND_TOOL_FAILURE_SH:-$PLUGIN_ROOT/scripts/append-tool-failure.sh}"

kv_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

copy_to_parent() {
    local file="$1" name="$2"
    [[ -n "$SESSION_ENV_PATH" && -f "$file" ]] || return 0
    cp "$file" "$(dirname "$SESSION_ENV_PATH")/$name" 2>/dev/null || true
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
        --tool "larch-log.sh write-round" \
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
        emit_breadcrumb --category=warn "⚠ review-core: emit-tally failed ($context, round $ROUND_NUM, rc=$rc)"
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
    [[ -x "$PLUGIN_ROOT/scripts/append-execution-issue.sh" ]] || return 0
    "$PLUGIN_ROOT/scripts/append-execution-issue.sh" \
        --log "$(execution_issues_log)" \
        --category "External Reviewer Issues" \
        --entry "$entry" 2>/dev/null || true
}

flush_round_log() {
    local flush_err rc=0
    [[ -n "$RUN_ID" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" && -d "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    [[ -x "$LARCH_LOG_SH" ]] || return 0
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
        emit_breadcrumb --category=warn "⚠ review-core: round log flush failed (round $ROUND_NUM, rc=$rc)"
        append_round_log_write_failure "5" "$ROUND_NUM" "$rc" "$flush_err"
    else
        rm -f "$flush_err"
    fi
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
[[ -f "$REVIEW_TMPDIR/competition-notice.md" ]] && dispatch_args+=(--competition-notice-file "$REVIEW_TMPDIR/competition-notice.md")
"$DISPATCH_PANEL_SH" "${dispatch_args[@]}" > "$dispatch_out"

external_outputs=$(kv_get "$dispatch_out" EXTERNAL_OUTPUT_FILES)
claude_outputs=$(kv_get "$dispatch_out" CLAUDE_OUTPUT_FILES)
panel_mode=$(kv_get "$dispatch_out" PANEL_MODE)
panel_shape=$(kv_get "$dispatch_out" PANEL_SHAPE)
dispatch_ok=$(kv_get "$dispatch_out" DISPATCH_OK)
static_dispatch_ok=$(kv_get "$dispatch_out" STATIC_DISPATCH_OK)
panel_manifest=$(kv_get "$dispatch_out" PANEL_MANIFEST)
scout_status=$(kv_get "$dispatch_out" SCOUT_STATUS)
dynamic_slots=$(kv_get "$dispatch_out" DYNAMIC_SLOTS)
scout_manifest=$(kv_get "$dispatch_out" SCOUT_MANIFEST)
scout_fail_reason=$(kv_get "$dispatch_out" SCOUT_FAIL_REASON)
static_slot_count=$(kv_get "$dispatch_out" STATIC_SLOT_COUNT)
panel_mode="${panel_mode:-waterfall}"
panel_shape="${panel_shape:-$PANEL}"
dispatch_ok="${dispatch_ok:-true}"
static_dispatch_ok="${static_dispatch_ok:-true}"
scout_status="${scout_status:-na}"
scout_fail_reason="${scout_fail_reason:-}"
dynamic_slots="${dynamic_slots:-0}"
static_slot_count="${static_slot_count:-0}"
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
emit_breadcrumb --category=progress "→ review: consolidating findings"
"$COLLECT_FINDINGS_SH" "${collect_args[@]}" > "$collect_out"
recover_dirty_tree "${external_array[@]+"${external_array[@]}"}" "${claude_array[@]+"${claude_array[@]}"}"

# Reviewer failure threshold: hard-stop the round when >50% of the intended
# panel slots failed. THRESHOLD_OK=false → REVIEW_CORE_STATUS=panel-failed and
# exit 2 so review-and-fix.sh propagates the stall to /implement Step 5.
collector_results_file="$REVIEW_TMPDIR/collector-results.env"
threshold_out="$REVIEW_TMPDIR/review-core-threshold.env"
launched_slots="$static_slot_count"
threshold_args=(--collector-results-file "$collector_results_file" --panel "$panel_shape" --launched-slots "$launched_slots" --round-num "$ROUND_NUM")
if [[ "$static_dispatch_ok" == "false" ]]; then
    printf 'THRESHOLD_OK=false\nTHRESHOLD_REASON=dispatch-failed\n' > "$threshold_out"
else
    "$CHECK_THRESHOLD_SH" "${threshold_args[@]}" > "$threshold_out"
fi
threshold_ok=$(kv_get "$threshold_out" THRESHOLD_OK)
threshold_reason=$(kv_get "$threshold_out" THRESHOLD_REASON)
not_substantive_slots=$(kv_get "$threshold_out" NOT_SUBSTANTIVE_SLOTS)
not_substantive_slots="${not_substantive_slots:-0}"
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
    zero_findings_tally_out="$REVIEW_TMPDIR/review-core-zero-findings-tally.env"
    zero_findings_voter="$REVIEW_TMPDIR/zero-findings-voter.txt"
    zero_emit_out="$REVIEW_TMPDIR/review-core-zero-findings-emit.env"
    : > "$zero_findings_voter"
    zero_tally_args=(
        --ballot-file "$REVIEW_TMPDIR/findings.md"
        --review-tmpdir "$REVIEW_TMPDIR"
        --cursor-available "$CURSOR_AVAILABLE"
        --codex-available "$CODEX_AVAILABLE"
        --voter-files "$zero_findings_voter"
    )
    [[ -n "$panel_manifest" && -f "$panel_manifest" ]] && zero_tally_args+=(--manifest-file "$panel_manifest")
    [[ -f "$collector_results_file" ]] && zero_tally_args+=(--collector-results-file "$collector_results_file")
    [[ "$not_substantive_slots" -gt 0 ]] && zero_tally_args+=(--not-substantive-count "$not_substantive_slots")
    "$TALLY_VOTES_SH" "${zero_tally_args[@]}" > "$zero_findings_tally_out"
    zero_voting_tally_file=$(kv_get "$zero_findings_tally_out" VOTING_TALLY_FILE)
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
        copy_to_parent "$REVIEW_TMPDIR/oos-accepted-review.md" oos-accepted-review.md
    fi
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
"$AGGREGATE_FINDINGS_SH" "${aggregate_args[@]}" > "$aggregate_out" 2> >(tee "$aggregate_stderr" >&2)
aggregate_rc=$?
set -e
if [[ "$aggregate_rc" -ne 0 ]]; then
    emit_breadcrumb --category=warn "⚠ review-core: aggregate-findings exited non-zero (rc=$aggregate_rc; see $aggregate_stderr)"
    append_review_execution_issue "- **review-core / aggregate-findings**: subprocess exited with rc=$aggregate_rc (unexpected; see $aggregate_stderr)."
fi

aggregate_reason=$(kv_get "$aggregate_out" REASON)
if [[ "$aggregate_reason" == "validation-exhausted" ]]; then
    agg_exhaust_tally="$REVIEW_TMPDIR/review-core-aggregator-exhaust-tally.env"
    agg_exhaust_emit_out="$REVIEW_TMPDIR/review-core-aggregator-exhaust-emit.env"
    : > "$REVIEW_TMPDIR/accepted-findings.md"
    : > "$REVIEW_TMPDIR/rejected-findings.md"
    : > "$REVIEW_TMPDIR/oos-accepted-review.md"
    cat > "$agg_exhaust_tally" <<EOF
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
NEUTRAL_COUNT=0
EOF
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
    exit 2
fi

tally_out="$REVIEW_TMPDIR/review-core-tally.env"

# Dispatch the code-review voting panel and collect vote-output files.
# Every round uses Claude + Codex + Cursor; Claude replacements cover unhealthy
# external voters via the waterfall. Failed voters are treated as abstentions.
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
[[ -n "$voting_skipped_warning" ]] && emit_kv VOTING_SKIPPED_WARNING "$voting_skipped_warning"
[[ -n "$yield_tsv_file" ]] && emit_kv YIELD_TSV_FILE "$yield_tsv_file"
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
    exit 0
fi

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
