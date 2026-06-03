#!/usr/bin/env bash
# dispatch-with-waterfall.sh — Three-phase per-slot reviewer dispatcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-with-waterfall.sh --slots-file FILE --codex-present true|false --cursor-present true|false --mode diff|description [--paths-file FILE] [context flags]. Default paths-file is SLOTS_FILE.output-files; its parent directory must already exist. Stdout KVs include ALL_OUTPUT_FILES_PATH, ALL_OUTPUT_FILES, ALL_OUTPUT_TOOLS, DISPATCH_OK, WARN, …"
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
COMPETITION_NOTICE=false
COMPETITION_NOTICE_FILE=""
WATERFALL_PATHS_FILE=""
REQUIRE_RESULT_PATTERN=""
REQUIRE_FIRST_LINE_PATTERN=""
NO_FALLBACK=false

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
        --competition-notice) COMPETITION_NOTICE=true; shift ;;
        --competition-notice-file) COMPETITION_NOTICE_FILE="${2:?--competition-notice-file requires a value}"; shift 2 ;;
        --paths-file) WATERFALL_PATHS_FILE="${2:?--paths-file requires a value}"; shift 2 ;;
        --require-result-pattern) REQUIRE_RESULT_PATTERN="${2:?--require-result-pattern requires a value}"; shift 2 ;;
        --require-first-line-pattern) REQUIRE_FIRST_LINE_PATTERN="${2:?--require-first-line-pattern requires a value}"; shift 2 ;;
        --no-fallback) NO_FALLBACK=true; shift ;;
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

# Prevalidate --require-result-pattern as ERE once before any slot launches.
# grep -E on empty stdin returns 1 (no match) for valid patterns and 2 for
# invalid ERE syntax; only the latter is a caller bug we should refuse upfront.
if [[ -n "$REQUIRE_RESULT_PATTERN" ]]; then
    set +e
    printf '' | grep -E -- "$REQUIRE_RESULT_PATTERN" >/dev/null 2>&1
    _rrp_rc=$?
    set -e
    if (( _rrp_rc > 1 )); then
        larch_err "dispatch-with-waterfall.sh: --require-result-pattern is not a valid ERE: $REQUIRE_RESULT_PATTERN"
        exit 2
    fi
fi
if [[ -n "$REQUIRE_FIRST_LINE_PATTERN" ]]; then
    set +e
    printf '' | grep -E -- "$REQUIRE_FIRST_LINE_PATTERN" >/dev/null 2>&1
    _rflp_rc=$?
    set -e
    if (( _rflp_rc > 1 )); then
        larch_err "dispatch-with-waterfall.sh: --require-first-line-pattern is not a valid ERE: $REQUIRE_FIRST_LINE_PATTERN"
        exit 2
    fi
fi

slot_names=()
slot_tools=()
slot_outputs=()
slot_agents=()
slot_prompts=()

while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    printf '%s' "$row" \
        | jq -er '
            if (type != "object") then error("slot row must be a JSON object")
            elif ((.slot | type) != "string" or (.slot | length) == 0) then error("slot must be a non-empty string")
            elif (.tool != "codex" and .tool != "cursor") then error("tool must be codex or cursor")
            elif ((.output | type) != "string" or (.output | length) == 0) then error("output must be a non-empty string")
            elif ((has("agent") and (.agent != null) and ((.agent | type) != "string")) or
                  (has("prompt_file") and (.prompt_file != null) and ((.prompt_file | type) != "string"))) then
                error("agent and prompt_file must be strings when present")
            else
                true
            end
        ' >/dev/null 2>&1 || {
        larch_err "dispatch-with-waterfall.sh: invalid slot row: $row"
        exit 2
    }
    slot_name=$(printf '%s' "$row" | jq -r '.slot')
    slot_tool=$(printf '%s' "$row" | jq -r '.tool')
    slot_output=$(printf '%s' "$row" | jq -r '.output')
    case "$slot_output" in
        *$'\n'*|*$'\r'*)
            larch_err "dispatch-with-waterfall.sh: slot '${slot_name}' output path contains a newline or carriage return (line-oriented paths-file contract)"
            exit 2
            ;;
    esac
    slot_agent=$(printf '%s' "$row" | jq -r '.agent // empty')
    slot_prompt=$(printf '%s' "$row" | jq -r '.prompt_file // empty')
    if [[ -n "$slot_agent" && -n "$slot_prompt" ]]; then
        larch_err "dispatch-with-waterfall.sh: slot '$slot_name' must not set both agent and prompt_file"
        exit 2
    fi
    if [[ -z "$slot_agent" && -z "$slot_prompt" ]]; then
        larch_err "dispatch-with-waterfall.sh: slot '$slot_name' must set either agent or prompt_file"
        exit 2
    fi
    slot_names+=("$slot_name")
    slot_tools+=("$slot_tool")
    slot_outputs+=("$slot_output")
    slot_agents+=("$slot_agent")
    slot_prompts+=("$slot_prompt")
done < "$SLOTS_FILE"

slot_count=${#slot_names[@]}
if (( slot_count == 0 )); then
    larch_err "dispatch-with-waterfall.sh: slots file contains no slot rows"
    exit 2
fi

final_outputs=()
final_tools=()
# Parallel per-slot drop bookkeeping (indexed like final_outputs). When a slot
# is dropped (only possible under --no-fallback), slot_drop_reason[idx] records
# *why* (format-gate-miss / result-gate-miss / empty / collector-failure /
# result-unreadable / tool-absent) and slot_drop_detail[idx] holds a single-line
# ~200-char snippet of the offending output so the drop is observable downstream
# (#3392). Cleared when a slot settles OK so stale phase-1 reasons never leak.
slot_drop_reason=()
slot_drop_detail=()
for ((i=0; i<slot_count; i++)); do
    final_outputs+=("")
    final_tools+=("")
    slot_drop_reason+=("")
    slot_drop_detail+=("")
done

# Flatten a captured snippet to a single line: read the leading bytes of a file,
# collapse newlines/CR/tabs to spaces, and cap at 200 chars (the line-oriented
# DROPPED_SLOTS_FILE / KV contract forbids embedded newlines or tabs).
snippet_from_file() {
    local f="$1"
    [[ -r "$f" ]] || { printf ''; return 0; }
    # `cut -c` reads each line to its end (no early close), so `tr`/`head` do not
    # take SIGPIPE here; the trailing `|| true` is defensive so a snippet capture
    # can never abort the caller under `set -euo pipefail`.
    head -c 2000 "$f" 2>/dev/null | LC_ALL=C tr '\n\r\t' '   ' | cut -c1-200 || true
}

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
        ) >/dev/null 2>"${output}.launch-stderr" &
    else
        (
            set +e
            competition_args=()
            [[ "$COMPETITION_NOTICE" == "true" ]] && competition_args+=(--competition-notice)
            [[ -n "$COMPETITION_NOTICE_FILE" ]] && competition_args+=(--competition-notice-file "$COMPETITION_NOTICE_FILE")
            if [[ -n "$prompt_file" ]]; then
                "$SCRIPT_DIR/launch-review.sh" --tool "$tool" --output "$output" --prompt-file "$prompt_file" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}" "${competition_args[@]+"${competition_args[@]}"}"
            else
                "$SCRIPT_DIR/launch-review.sh" --tool "$tool" --output "$output" --agent-file "$agent" --mode "$MODE" --timeout "$TIMEOUT" --timing-task-kind "$timing" "${common_args[@]+"${common_args[@]}"}" "${competition_args[@]+"${competition_args[@]}"}"
            fi
            rc=$?
            [[ -f "${output}.done" ]] || printf '%s\n' "$rc" > "${output}.done"
            exit "$rc"
        ) >/dev/null 2>"${output}.launch-stderr" &
    fi
    pids+=("$!")
    phase_indices+=("$idx")
    phase_outputs+=("$output")
    phase_tools+=("$tool")
}

collect_phase() {
    local failed_var="$1"
    local idx output tool block key value status rf check_file _first_nonblank _drop_stderr
    local _salvage_lineno _salvage_tmp _salvage_ok
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
            # STATUS=cap_hit is a launcher-side budget skip and remains terminal
            # under the pattern gate (token-budget skip contract preserved).
            if [[ "$status" == "OK" && -n "$REQUIRE_RESULT_PATTERN" ]]; then
                check_file="${rf:-$output}"
                if [[ ! -r "$check_file" ]]; then
                    larch_err "dispatch-with-waterfall.sh: result file not readable for --require-result-pattern check: $check_file"
                    slot_drop_reason[idx]="result-unreadable"
                    slot_drop_detail[idx]="result file not readable: $check_file"
                    failed+=("$idx")
                    continue
                fi
                if ! grep -Eq -- "$REQUIRE_RESULT_PATTERN" "$check_file"; then
                    slot_drop_reason[idx]="result-gate-miss"
                    slot_drop_detail[idx]="$(snippet_from_file "$check_file")"
                    failed+=("$idx")
                    continue
                fi
            fi
            if [[ "$status" == "OK" && -n "$REQUIRE_FIRST_LINE_PATTERN" ]]; then
                check_file="${rf:-$output}"
                if [[ ! -r "$check_file" ]]; then
                    larch_err "dispatch-with-waterfall.sh: result file not readable for --require-first-line-pattern check: $check_file"
                    slot_drop_reason[idx]="result-unreadable"
                    slot_drop_detail[idx]="result file not readable: $check_file"
                    failed+=("$idx")
                    continue
                fi
                _first_nonblank=$(awk '/[^[:space:]]/ { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print; exit }' "$check_file")
                if ! printf '%s\n' "$_first_nonblank" | grep -Eq -- "$REQUIRE_FIRST_LINE_PATTERN"; then
                    # Distinguish a genuinely empty result (reviewer produced
                    # nothing) from a format-gate-miss (reviewer produced a
                    # healthy response that merely leads with a preamble).
                    if [[ -z "$_first_nonblank" ]]; then
                        slot_drop_reason[idx]="empty"
                        slot_drop_detail[idx]=""
                        failed+=("$idx")
                        continue
                    fi
                    # #3423 preamble-salvage: the first non-blank line is a
                    # narration preamble, but a valid TSV/sentinel payload may
                    # follow on a LATER line. Find the first line matching the
                    # gate; when it is below line 1, strip every preceding line,
                    # rewrite check_file in place, and settle the slot instead of
                    # dropping it. Narration-only output (no later match), a
                    # match already on line 1, or a rewrite failure all keep the
                    # existing format-gate-miss drop. Salvage is confined to this
                    # branch — the empty / result-gate-miss / result-unreadable /
                    # collector-failure paths are untouched. The grep|head|cut
                    # substitution carries `|| true` so a no-match (grep rc 1) or
                    # head-induced SIGPIPE cannot abort the run under
                    # `set -euo pipefail`; the line number is validated as a
                    # positive integer before `tail -n +N`.
                    _salvage_ok=false
                    _salvage_lineno=$(grep -nE -- "$REQUIRE_FIRST_LINE_PATTERN" "$check_file" 2>/dev/null | head -n1 | cut -d: -f1 || true)
                    if [[ "$_salvage_lineno" =~ ^[0-9]+$ ]] && (( _salvage_lineno > 1 )); then
                        _salvage_tmp=$(mktemp "${check_file}.salvage.XXXXXX")
                        if tail -n +"$_salvage_lineno" "$check_file" > "$_salvage_tmp" 2>/dev/null && mv -f "$_salvage_tmp" "$check_file"; then
                            _salvage_ok=true
                        else
                            rm -f "$_salvage_tmp"
                        fi
                    fi
                    if [[ "$_salvage_ok" != "true" ]]; then
                        slot_drop_reason[idx]="format-gate-miss"
                        slot_drop_detail[idx]="$(snippet_from_file "$check_file")"
                        failed+=("$idx")
                        continue
                    fi
                    # Salvage succeeded — fall through to the settle block below.
                fi
            fi
            # shellcheck disable=SC2004
            final_outputs[$idx]="${rf:-$output}"
            # shellcheck disable=SC2004
            final_tools[$idx]="$tool"
            # Slot settled OK — clear any drop reason recorded on a prior phase.
            slot_drop_reason[idx]=""
            slot_drop_detail[idx]=""
        else
            # Non-OK / non-cap_hit collector status: launch or collection failed.
            _drop_stderr=""
            [[ -r "${output}.launch-stderr" ]] && _drop_stderr="$(snippet_from_file "${output}.launch-stderr")"
            slot_drop_reason[idx]="collector-failure"
            if [[ -n "$_drop_stderr" ]]; then
                slot_drop_detail[idx]="STATUS=${status:-unknown} ${_drop_stderr}"
            else
                slot_drop_detail[idx]="STATUS=${status:-unknown}"
            fi
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
phase1_failed=()

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

fallback_count=0
phase3_failed=()
dispatch_ok=true
static_dispatch_ok=true
dynamic_dispatch_ok=true

if [[ "$NO_FALLBACK" == "true" ]]; then
    combined_fallback=0
    # phase1_queue slots never launched (their primary tool was absent); record
    # the drop reason so it is distinguishable from a format/collector failure.
    for idx in "${phase1_queue[@]+"${phase1_queue[@]}"}"; do
        slot_drop_reason[idx]="tool-absent"
        slot_drop_detail[idx]="primary tool ${slot_tools[$idx]} not present"
    done
    for idx in "${phase1_queue[@]+"${phase1_queue[@]}"}" "${phase1_failed[@]+"${phase1_failed[@]}"}"; do
        case "${slot_names[$idx]}" in
            dyn-*) dynamic_dispatch_ok=false ;;
            *) static_dispatch_ok=false ;;
        esac
    done
else
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

    reset_phase
    for idx in "${phase3_queue[@]+"${phase3_queue[@]}"}"; do
        out=$(output_for_phase "${slot_outputs[$idx]}" phase3)
        phase3_outputs+=("$out")
        fallback_count=$((fallback_count + 1))
        launch_slot "$idx" phase3 claude "$out"
    done
    collect_phase phase3_failed

    combined_fallback=$fallback_count
fi

if [[ -n "$FALLBACK_COUNTER_FILE" ]]; then
    prior=0
    [[ -f "$FALLBACK_COUNTER_FILE" ]] && prior=$(cat "$FALLBACK_COUNTER_FILE" 2>/dev/null || echo 0)
    case "$prior" in ''|*[!0-9]*) prior=0 ;; esac
    tmp=$(mktemp "${FALLBACK_COUNTER_FILE}.tmp.XXXXXX")
    printf '%s\n' "$((prior + combined_fallback))" > "$tmp"
    mv "$tmp" "$FALLBACK_COUNTER_FILE"
fi

for idx in "${phase3_failed[@]+"${phase3_failed[@]}"}"; do
    # shellcheck disable=SC2004
    final_outputs[$idx]="$(output_for_phase "${slot_outputs[$idx]}" phase3)"
    # shellcheck disable=SC2004
    final_tools[$idx]="claude"
    dispatch_ok=false
    case "${slot_names[$idx]}" in
        dyn-*) dynamic_dispatch_ok=false ;;
        *) static_dispatch_ok=false ;;
    esac
done

if [[ ${#phase3_failed[@]} -gt 0 ]]; then
    _wf_tail_replay_paths=()
    for idx in "${phase3_failed[@]}"; do
        _wf_tail_replay_paths+=("${final_outputs[$idx]}")
    done
    LARCH_QUIET_DISABLE=1 "$SCRIPT_DIR/collect-agent-results.sh" --timeout "$TIMEOUT" \
        "${_wf_tail_replay_paths[@]}" >/dev/null || true
fi

warn=""
threshold="${LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD:-3}"
case "$threshold" in ''|*[!0-9]*) threshold=3 ;; esac
if (( combined_fallback > threshold )); then
    warn="cost-fallback-exceeded-threshold"
fi

resolved_paths_file="${WATERFALL_PATHS_FILE:-${SLOTS_FILE}.output-files}"
paths_dir=$(dirname "$resolved_paths_file")
[[ -d "$paths_dir" ]] || {
    larch_err "dispatch-with-waterfall.sh: paths-file parent directory does not exist: $paths_dir"
    exit 2
}
for ((i=0; i<slot_count; i++)); do
    p="${final_outputs[$i]}"
    case "$p" in
        *$'\n'*|*$'\r'*)
            larch_err "dispatch-with-waterfall.sh: output path for slot '${slot_names[$i]}' contains a newline or carriage return (line-oriented paths-file contract)"
            exit 2
            ;;
    esac
done

all_output_files=()
all_output_tools=()
for ((i=0; i<slot_count; i++)); do
    [[ "$NO_FALLBACK" == "true" && -z "${final_outputs[$i]}" ]] && continue
    all_output_files+=("${final_outputs[$i]}")
    all_output_tools+=("${final_tools[$i]}")
done

emit_kv PHASE1_SLOTS "${phase1_outputs[*]-}"
emit_kv PHASE2_SLOTS "${phase2_outputs[*]-}"
emit_kv PHASE3_SLOTS "${phase3_outputs[*]-}"
emit_kv ALL_OUTPUT_FILES "${all_output_files[*]-}"
emit_kv ALL_OUTPUT_FILES_PATH "$resolved_paths_file"
emit_kv ALL_OUTPUT_TOOLS "${all_output_tools[*]-}"
emit_kv FALLBACK_COUNT "$fallback_count"
emit_kv COMBINED_FALLBACK_COUNT "$combined_fallback"
[[ -n "$warn" ]] && emit_kv WARN "$warn"
emit_kv DISPATCH_OK "$dispatch_ok"
emit_kv STATIC_DISPATCH_OK "$static_dispatch_ok"
emit_kv DYNAMIC_DISPATCH_OK "$dynamic_dispatch_ok"
if [[ "$NO_FALLBACK" == "true" && ${#all_output_files[@]} -eq 0 && slot_count -gt 0 ]]; then
    emit_kv ALL_SLOTS_DROPPED true
fi

# Per-slot drop diagnostics (#3392). Under --no-fallback a slot with empty
# final_outputs was dropped; surface each as a TSV record
# (slot<TAB>tool<TAB>reason<TAB>snippet) in a sidecar so the caller can record a
# per-slot reason in execution-issues.md instead of only seeing one terse
# aggregate WARN. Reason/snippet are single-line and tab-free by construction
# (snippet_from_file flattens). The sidecar is written only when ≥1 slot dropped.
if [[ "$NO_FALLBACK" == "true" ]]; then
    drops_tmp=$(mktemp "${paths_dir}/.dispatch-waterfall-drops.XXXXXX")
    drop_any=0
    for ((i=0; i<slot_count; i++)); do
        [[ -n "${final_outputs[$i]}" ]] && continue
        drop_any=1
        # Flatten any TAB/newline/CR out of the externally-derived slot/tool
        # fields so the line-oriented TSV cannot be corrupted (e.g. a dynamic
        # archetype slug carrying a tab). Replacement is a literal space, so the
        # `&`-corruption hazard of `${var//…}` does not apply. reason is an
        # internal constant; detail is already flattened by snippet_from_file.
        _ds_slot=${slot_names[$i]}
        _ds_slot=${_ds_slot//$'\t'/ }; _ds_slot=${_ds_slot//$'\n'/ }; _ds_slot=${_ds_slot//$'\r'/ }
        _ds_tool=${slot_tools[$i]}
        _ds_tool=${_ds_tool//$'\t'/ }; _ds_tool=${_ds_tool//$'\n'/ }; _ds_tool=${_ds_tool//$'\r'/ }
        printf '%s\t%s\t%s\t%s\n' \
            "$_ds_slot" "$_ds_tool" \
            "${slot_drop_reason[$i]:-unknown}" "${slot_drop_detail[$i]:-}" >> "$drops_tmp"
    done
    if (( drop_any )); then
        dropped_slots_file="${resolved_paths_file}.dropped-slots"
        mv -f "$drops_tmp" "$dropped_slots_file"
        emit_kv DROPPED_SLOTS_FILE "$dropped_slots_file"
    else
        rm -f "$drops_tmp"
    fi
fi

paths_tmp=$(mktemp "${paths_dir}/.dispatch-waterfall-paths.XXXXXX")
for ((i=0; i<slot_count; i++)); do
    p="${final_outputs[$i]}"
    if [[ "$NO_FALLBACK" == "true" && -z "$p" ]]; then
        continue
    fi
    printf '%s\n' "$p" >> "$paths_tmp"
done
mv -f "$paths_tmp" "$resolved_paths_file"
