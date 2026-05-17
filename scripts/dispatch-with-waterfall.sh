#!/usr/bin/env bash
# dispatch-with-waterfall.sh — Three-phase per-slot reviewer dispatcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-with-waterfall.sh --slots-file FILE --codex-present true|false --cursor-present true|false --mode diff|description [context flags]"
}

SLOTS_FILE=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
MODE=""
DIFF_FILE=""
COMMIT_COUNT=""
PLAN_FILE=""
FEATURE_FILE=""
SCOPE_FILES=""
DESCRIPTION_TEXT=""
TIMEOUT="1800"
FALLBACK_COUNTER_FILE=""
COMPETITION_NOTICE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) SLOTS_FILE="${2:?--slots-file requires a value}"; shift 2 ;;
        --codex-present|--codex-available) CODEX_PRESENT="${2:?--codex-present requires a value}"; shift 2 ;;
        --cursor-present|--cursor-available) CURSOR_PRESENT="${2:?--cursor-present requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --fallback-counter-file) FALLBACK_COUNTER_FILE="${2:?--fallback-counter-file requires a value}"; shift 2 ;;
        --competition-notice) COMPETITION_NOTICE="${2:?--competition-notice requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-with-waterfall.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$SLOTS_FILE" && -f "$SLOTS_FILE" ]] || { larch_err "dispatch-with-waterfall.sh: --slots-file must name a file"; exit 2; }
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "dispatch-with-waterfall.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "dispatch-with-waterfall.sh: --cursor-present must be true or false"; exit 2; }
[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "dispatch-with-waterfall.sh: --mode must be diff or description"; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "dispatch-with-waterfall.sh: --timeout must be a positive integer"; exit 2 ;; esac
command -v jq >/dev/null 2>&1 || { larch_err "dispatch-with-waterfall.sh: jq is required"; exit 2; }

slot_names=()
slot_tools=()
slot_outputs=()
slot_agents=()
slot_prompts=()
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    slot_names+=("$(printf '%s' "$row" | jq -r '.slot')")
    slot_tools+=("$(printf '%s' "$row" | jq -r '.tool')")
    slot_outputs+=("$(printf '%s' "$row" | jq -r '.output')")
    slot_agents+=("$(printf '%s' "$row" | jq -r '.agent // empty')")
    slot_prompts+=("$(printf '%s' "$row" | jq -r '.prompt_file // empty')")
done < "$SLOTS_FILE"

slot_count=${#slot_names[@]}
final_outputs=()
final_tools=()
for ((i=0; i<slot_count; i++)); do
    final_outputs+=("")
    final_tools+=("")
done

present_for_tool() {
    case "$1" in
        codex) [[ "$CODEX_PRESENT" == "true" ]] ;;
        cursor) [[ "$CURSOR_PRESENT" == "true" ]] ;;
        *) return 1 ;;
    esac
}

other_tool() {
    case "$1" in
        codex) printf 'cursor' ;;
        cursor) printf 'codex' ;;
        *) return 1 ;;
    esac
}

output_for_phase() {
    local base="$1" phase="$2"
    if [[ "$phase" == "phase1" ]]; then
        printf '%s' "$base"
    else
        case "$base" in
            *.txt) printf '%s-%s.txt' "${base%.txt}" "$phase" ;;
            *) printf '%s-%s' "$base" "$phase" ;;
        esac
    fi
}

common_args=()
[[ -n "$DIFF_FILE" ]] && common_args+=(--diff-file "$DIFF_FILE")
[[ -n "$COMMIT_COUNT" ]] && common_args+=(--commit-count "$COMMIT_COUNT")
[[ -n "$PLAN_FILE" ]] && common_args+=(--plan-file "$PLAN_FILE")
[[ -n "$FEATURE_FILE" ]] && common_args+=(--feature-file "$FEATURE_FILE")
[[ -n "$SCOPE_FILES" ]] && common_args+=(--scope-files "$SCOPE_FILES")
[[ -n "$DESCRIPTION_TEXT" ]] && common_args+=(--description-text "$DESCRIPTION_TEXT")

pids=()
phase_indices=()
phase_outputs=()
phase_tools=()

reset_phase() {
    pids=()
    phase_indices=()
    phase_outputs=()
    phase_tools=()
}

launch_slot() {
    local idx="$1" phase="$2" tool="$3" output="$4"
    local agent="${slot_agents[$idx]}"
    local prompt_file="${slot_prompts[$idx]}"
    local timing="${tool}-${phase}-${slot_names[$idx]}"
    mkdir -p "$(dirname "$output")"
    if [[ "$tool" == "claude" ]]; then
        (
            set +e
            if [[ -n "$prompt_file" ]]; then
                "$SCRIPT_DIR/launch-claude-review.sh" --output "$output" --prompt-file "$prompt_file" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}"
            else
                "$SCRIPT_DIR/launch-claude-review.sh" --output "$output" --agent-file "$agent" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}"
            fi
            rc=$?
            [[ -f "${output}.done" ]] || printf '%s\n' "$rc" > "${output}.done"
            exit "$rc"
        ) >/dev/null 2>&1 &
    else
        (
            set +e
            competition_args=()
            [[ -n "$COMPETITION_NOTICE" ]] && competition_args+=(--competition-notice "$COMPETITION_NOTICE")
            if [[ -n "$prompt_file" ]]; then
                "$SCRIPT_DIR/launch-review.sh" --tool "$tool" --output "$output" --prompt-file "$prompt_file" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}" "${competition_args[@]+"${competition_args[@]}"}"
            else
                "$SCRIPT_DIR/launch-review.sh" --tool "$tool" --output "$output" --agent-file "$agent" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}" "${competition_args[@]+"${competition_args[@]}"}"
            fi
            rc=$?
            [[ -f "${output}.done" ]] || printf '%s\n' "$rc" > "${output}.done"
            exit "$rc"
        ) >/dev/null 2>&1 &
    fi
    pids+=("$!")
    phase_indices+=("$idx")
    phase_outputs+=("$output")
    phase_tools+=("$tool")
}

collect_phase() {
    local failed_var="$1"
    local idx output tool block key value status rf
    local -a failed=()
    [[ ${#phase_outputs[@]} -gt 0 ]] || {
        eval "$failed_var=()"
        return 0
    }

    for pid in "${pids[@]+"${pids[@]}"}"; do
        wait "$pid" || true
    done

    # Split summary into per-slot blocks by position (same order as argv to
    # collect-agent-results.sh). This avoids the retry-path mismatch where
    # collect-agent-results emits REVIEWER_FILE=<orig>-retry.txt but we
    # search for REVIEWER_FILE=<orig>.
    summary_blocks=()
    current_block=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            if [[ -n "$current_block" ]]; then
                summary_blocks+=("$current_block")
                current_block=""
            fi
        else
            if [[ -n "$current_block" ]]; then
                current_block="${current_block}"$'\n'"${line}"
            else
                current_block="$line"
            fi
        fi
    done <<< "$("$SCRIPT_DIR/collect-agent-results.sh" --timeout "$TIMEOUT" --summary-only "${phase_outputs[@]}")"
    [[ -n "$current_block" ]] && summary_blocks+=("$current_block")

    for i in "${!phase_outputs[@]}"; do
        idx="${phase_indices[$i]}"
        output="${phase_outputs[$i]}"
        tool="${phase_tools[$i]}"
        status=""
        rf=""
        block="${summary_blocks[$i]:-}"
        while IFS= read -r line || [[ -n "$line" ]]; do
            key="${line%%=*}"
            value="${line#*=}"
            [[ "$key" == "STATUS" ]] && status="$value"
            [[ "$key" == "REVIEWER_FILE" ]] && rf="$value"
        done <<< "$block"
        if [[ "$status" == "OK" || "$status" == "cap_hit" ]]; then
            # shellcheck disable=SC2004
            final_outputs[$idx]="${rf:-$output}"
            # shellcheck disable=SC2004
            final_tools[$idx]="$tool"
        else
            failed+=("$idx")
        fi
    done
    if [[ ${#failed[@]} -gt 0 ]]; then
        eval "$failed_var=(\"\${failed[@]}\")"
    else
        eval "$failed_var=()"
    fi
}

phase1_outputs=()
phase2_outputs=()
phase3_outputs=()

phase1_queue=()
reset_phase
for ((i=0; i<slot_count; i++)); do
    tool="${slot_tools[$i]}"
    if present_for_tool "$tool"; then
        out=$(output_for_phase "${slot_outputs[$i]}" phase1)
        phase1_outputs+=("$out")
        launch_slot "$i" phase1 "$tool" "$out"
    else
        phase1_queue+=("$i")
    fi
done
collect_phase phase1_failed
phase2_queue=("${phase1_queue[@]+"${phase1_queue[@]}"}" "${phase1_failed[@]+"${phase1_failed[@]}"}")

reset_phase
phase3_seed=()
for idx in "${phase2_queue[@]+"${phase2_queue[@]}"}"; do
    primary="${slot_tools[$idx]}"
    alt=$(other_tool "$primary" || true)
    if [[ -n "$alt" ]] && present_for_tool "$alt"; then
        out=$(output_for_phase "${slot_outputs[$idx]}" phase2)
        phase2_outputs+=("$out")
        launch_slot "$idx" phase2 "$alt" "$out"
    else
        phase3_seed+=("$idx")
    fi
done
collect_phase phase2_failed
phase3_queue=("${phase3_seed[@]+"${phase3_seed[@]}"}" "${phase2_failed[@]+"${phase2_failed[@]}"}")

fallback_count=0
reset_phase
for idx in "${phase3_queue[@]+"${phase3_queue[@]}"}"; do
    out=$(output_for_phase "${slot_outputs[$idx]}" phase3)
    phase3_outputs+=("$out")
    fallback_count=$((fallback_count + 1))
    launch_slot "$idx" phase3 claude "$out"
done
phase3_failed=()
collect_phase phase3_failed

if [[ -n "$FALLBACK_COUNTER_FILE" ]]; then
    prior=0
    [[ -f "$FALLBACK_COUNTER_FILE" ]] && prior=$(cat "$FALLBACK_COUNTER_FILE" 2>/dev/null || echo 0)
    case "$prior" in ''|*[!0-9]*) prior=0 ;; esac
    tmp=$(mktemp "${FALLBACK_COUNTER_FILE}.tmp.XXXXXX")
    printf '%s\n' "$((prior + fallback_count))" > "$tmp"
    mv "$tmp" "$FALLBACK_COUNTER_FILE"
fi

dispatch_ok=true
for idx in "${phase3_failed[@]+"${phase3_failed[@]}"}"; do
    # shellcheck disable=SC2004
    final_outputs[$idx]="$(output_for_phase "${slot_outputs[$idx]}" phase3)"
    # shellcheck disable=SC2004
    final_tools[$idx]="claude"
    dispatch_ok=false
done

warn=""
threshold="${LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD:-3}"
case "$threshold" in ''|*[!0-9]*) threshold=3 ;; esac
if (( fallback_count > threshold )); then
    warn="cost-fallback-exceeded-threshold"
fi

emit_kv PHASE1_SLOTS "${phase1_outputs[*]-}"
emit_kv PHASE2_SLOTS "${phase2_outputs[*]-}"
emit_kv PHASE3_SLOTS "${phase3_outputs[*]-}"
emit_kv ALL_OUTPUT_FILES "${final_outputs[*]-}"
emit_kv ALL_OUTPUT_TOOLS "${final_tools[*]-}"
emit_kv FALLBACK_COUNT "$fallback_count"
[[ -n "$warn" ]] && emit_kv WARN "$warn"
emit_kv DISPATCH_OK "$dispatch_ok"
