#!/usr/bin/env bash
# dispatch-panel.sh — Plan and launch /review reviewer slots.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"

usage() { echo "Usage: dispatch-panel.sh --mode diff|description --review-tmpdir DIR --codex-available true|false --cursor-available true|false [context flags]" >&2; }

MODE=""
DIFF_FILE=""
COMMIT_COUNT="0"
SCOPE_FILES=""
REVIEW_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
COMPETITION_NOTICE_FILE=""
PLAN_FILE=""
FEATURE_FILE=""
TIMING_TASK_PREFIX="review"
LAUNCH_CLAUDE="$PLUGIN_ROOT/scripts/launch-claude-subprocess.sh"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --competition-notice-file) COMPETITION_NOTICE_FILE="${2:?--competition-notice-file requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --timing-task-prefix) TIMING_TASK_PREFIX="${2:?--timing-task-prefix requires a value}"; shift 2 ;;
        --launch-claude-subprocess) LAUNCH_CLAUDE="${2:?--launch-claude-subprocess requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "dispatch-panel.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { echo "dispatch-panel.sh: --mode must be diff or description" >&2; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { echo "dispatch-panel.sh: --review-tmpdir is required" >&2; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { echo "dispatch-panel.sh: --codex-available must be true or false" >&2; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { echo "dispatch-panel.sh: --cursor-available must be true or false" >&2; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

manifest="$REVIEW_TMPDIR/panel-manifest.ndjson"
: > "$manifest"
external_outputs=()
claude_outputs=()
slot_count=0

make_prompt() {
    local name="$1"
    local prompt="$REVIEW_TMPDIR/claude-${name}-prompt.md"
    {
        printf 'Review mode: %s\n' "$MODE"
        printf 'Reviewer: %s\n' "$name"
        printf 'Focus areas: code-quality / risk-integration / correctness / architecture / security\n'
        [[ -n "$COMPETITION_NOTICE_FILE" && -f "$COMPETITION_NOTICE_FILE" ]] && cat "$COMPETITION_NOTICE_FILE"
    } > "$prompt"
    printf '%s' "$prompt"
}

launch_claude_slot() {
    local name="$1" out="$2" prompt
    prompt=$(make_prompt "$name")
    args=(--prompt-file "$prompt" --output-file "$out" --timeout 1800 --timing-task-kind "${TIMING_TASK_PREFIX}-claude-${name}")
    [[ -n "$DIFF_FILE" && -f "$DIFF_FILE" ]] && args+=(--context-files "$DIFF_FILE")
    [[ -n "$SCOPE_FILES" && -f "$SCOPE_FILES" ]] && args+=(--context-files "$SCOPE_FILES")
    "$LAUNCH_CLAUDE" "${args[@]}" >/dev/null &
    printf '{"slot":"%s","tool":"claude","output":"%s"}\n' "$name" "$out" >> "$manifest"
    claude_outputs+=("$out")
    slot_count=$((slot_count + 1))
}

launch_external_slot() {
    local tool="$1" name="$2" out="$3"
    local agent="$PLUGIN_ROOT/agents/reviewer-${name}.md"
    args=(--tool "$tool" --output "$out" --timeout 1800 --agent-file "$agent" --mode "$MODE" --competition-notice --timing-task-kind "${tool}-specialist-${name}")
    [[ "$MODE" == "diff" && -n "$DIFF_FILE" ]] && args+=(--diff-file "$DIFF_FILE" --commit-count "$COMMIT_COUNT")
    [[ "$MODE" == "description" && -n "$SCOPE_FILES" ]] && args+=(--description-text "description review" --scope-files "$SCOPE_FILES")
    [[ "$name" == "correctness" && -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && args+=(--plan-file "$PLAN_FILE")
    [[ "$name" == "correctness" && -n "$FEATURE_FILE" && -f "$FEATURE_FILE" ]] && args+=(--feature-file "$FEATURE_FILE")
    "$PLUGIN_ROOT/scripts/launch-review.sh" "${args[@]}" >/dev/null &
    printf '{"slot":"%s","tool":"%s","output":"%s"}\n' "$name" "$tool" "$out" >> "$manifest"
    external_outputs+=("$out")
    slot_count=$((slot_count + 1))
}

specialists=(structure correctness testing security edge-cases)
if [[ "$CODEX_AVAILABLE" == "false" && "$CURSOR_AVAILABLE" == "false" ]]; then
    launch_claude_slot "generic" "$REVIEW_TMPDIR/claude-generic-output.txt"
    panel_mode="both-down"
else
    panel_mode="normal"
    for name in "${specialists[@]}"; do
        if [[ "$CURSOR_AVAILABLE" == "true" ]]; then
            launch_external_slot cursor "$name" "$REVIEW_TMPDIR/cursor-specialist-${name}-output.txt"
        else
            launch_claude_slot "cursor-fallback-${name}" "$REVIEW_TMPDIR/claude-cursor-fallback-${name}-output.txt"
        fi
        if [[ "$CODEX_AVAILABLE" == "true" ]]; then
            launch_external_slot codex "$name" "$REVIEW_TMPDIR/codex-specialist-${name}-output.txt"
        else
            launch_claude_slot "codex-fallback-${name}" "$REVIEW_TMPDIR/claude-codex-fallback-${name}-output.txt"
        fi
    done
    launch_claude_slot "generic" "$REVIEW_TMPDIR/claude-generic-output.txt"
fi

printf 'EXTERNAL_OUTPUT_FILES='
printf '%q ' "${external_outputs[@]+"${external_outputs[@]}"}"
printf '\nCLAUDE_OUTPUT_FILES='
printf '%q ' "${claude_outputs[@]+"${claude_outputs[@]}"}"
printf '\nPANEL_MODE=%s\n' "$panel_mode"
printf 'SLOT_COUNT=%s\n' "$slot_count"
printf 'PANEL_MANIFEST=%q\n' "$manifest"
printf 'DISPATCH_OK=true\n'
