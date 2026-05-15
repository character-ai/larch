#!/usr/bin/env bash
# dispatch-panel.sh — Plan and launch /review reviewer slots.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { echo "Usage: dispatch-panel.sh --mode diff|description --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--panel simple|hard] [context flags]" >&2; }

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
DESCRIPTION_TEXT=""
TIMING_TASK_PREFIX="review"
LAUNCH_CLAUDE="$PLUGIN_ROOT/scripts/launch-claude-subprocess.sh"
LAUNCH_REVIEW="$PLUGIN_ROOT/scripts/launch-review.sh"
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
PANEL="hard"

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
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --timing-task-prefix) TIMING_TASK_PREFIX="${2:?--timing-task-prefix requires a value}"; shift 2 ;;
        --launch-claude-subprocess) LAUNCH_CLAUDE="${2:?--launch-claude-subprocess requires a value}"; shift 2 ;;
        --launch-review) LAUNCH_REVIEW="${2:?--launch-review requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "dispatch-panel.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

# Export so launch-review.sh subprocesses inherit it and timing-ledger.sh
# can resolve the per-run ledger via the SESSION_ENV_PATH fallback.
export SESSION_ENV_PATH

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { echo "dispatch-panel.sh: --mode must be diff or description" >&2; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { echo "dispatch-panel.sh: --review-tmpdir is required" >&2; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { echo "dispatch-panel.sh: --codex-available must be true or false" >&2; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { echo "dispatch-panel.sh: --cursor-available must be true or false" >&2; exit 2; }
[[ "$PANEL" == "simple" || "$PANEL" == "hard" ]] || { echo "dispatch-panel.sh: --panel must be simple or hard" >&2; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

manifest="$REVIEW_TMPDIR/panel-manifest.ndjson"
: > "$manifest"
external_outputs=()
claude_outputs=()
slot_count=0

execution_issue_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"
        return
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md' "$REVIEW_TMPDIR"
    fi
}

append_launch_failure() {
    local site="$1" tool="$2" rc="$3" output_file="$4"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$(execution_issue_log)" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --category "External Reviewer Issues" \
        --output-file "$output_file" \
        --redact >/dev/null 2>&1 || true
}

make_prompt() {
    local name="$1"
    local prompt="$REVIEW_TMPDIR/claude-${name}-prompt.md"
    {
        printf 'Review mode: %s\n' "$MODE"
        printf 'Reviewer: %s\n' "$name"
        printf 'Focus areas: code-quality / risk-integration / correctness / architecture / security\n'
        [[ -n "$DESCRIPTION_TEXT" ]] && printf 'Description: %s\n' "$DESCRIPTION_TEXT"
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
    {
        launch_log="$REVIEW_TMPDIR/dispatch-claude-${name}.log"
        # set +e: capture launcher non-zero exits and surface them via
        # append_launch_failure. Without this, set -e (inherited from the
        # parent) aborts the subshell before rc capture and the failure
        # logging path is bypassed.
        set +e
        "$LAUNCH_CLAUDE" "${args[@]}" > "$launch_log" 2>&1
        rc=$?
        set -e
        [[ "$rc" -eq 0 ]] || append_launch_failure "review Step 2" "launch-claude-subprocess.sh $name" "$rc" "$launch_log"
    } &
    printf '{"slot":"%s","tool":"claude","output":"%s"}\n' "$name" "$out" >> "$manifest"
    claude_outputs+=("$out")
    slot_count=$((slot_count + 1))
}

launch_external_slot() {
    local tool="$1" name="$2" out="$3"
    local agent="$PLUGIN_ROOT/agents/reviewer-${name}.md"
    args=(--tool "$tool" --output "$out" --timeout 1800 --agent-file "$agent" --mode "$MODE" --competition-notice --timing-task-kind "${tool}-specialist-${name}")
    [[ "$MODE" == "diff" && -n "$DIFF_FILE" ]] && args+=(--diff-file "$DIFF_FILE" --commit-count "$COMMIT_COUNT")
    [[ "$MODE" == "description" && -n "$SCOPE_FILES" ]] && args+=(--description-text "${DESCRIPTION_TEXT:-description review}" --scope-files "$SCOPE_FILES")
    [[ ( "$name" == "correctness" || "$name" == "testing" || "$name" == "structure" || "$name" == "plan-fidelity" ) && -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && args+=(--plan-file "$PLAN_FILE")
    [[ ( "$name" == "correctness" || "$name" == "testing" || "$name" == "structure" || "$name" == "plan-fidelity" ) && -n "$FEATURE_FILE" && -f "$FEATURE_FILE" ]] && args+=(--feature-file "$FEATURE_FILE")
    {
        launch_log="$REVIEW_TMPDIR/dispatch-${tool}-${name}.log"
        # set +e: capture launcher non-zero exits and surface them via
        # append_launch_failure. Without this, set -e (inherited from the
        # parent) aborts the subshell before rc capture and the failure
        # logging path is bypassed.
        set +e
        "$LAUNCH_REVIEW" "${args[@]}" > "$launch_log" 2>&1
        rc=$?
        set -e
        [[ "$rc" -eq 0 ]] || append_launch_failure "review Step 2" "launch-review.sh $tool $name" "$rc" "$launch_log"
    } &
    printf '{"slot":"%s","tool":"%s","output":"%s"}\n' "$name" "$tool" "$out" >> "$manifest"
    external_outputs+=("$out")
    slot_count=$((slot_count + 1))
}

if [[ "$PANEL" == "simple" ]]; then
    cursor_specialists=(edge-cases)
    codex_specialists=(structure)
    if [[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]]; then
        cursor_specialists+=(plan-fidelity)
        codex_specialists+=(plan-fidelity)
    fi
else
    cursor_specialists=(structure correctness testing security edge-cases plan-fidelity)
    codex_specialists=(structure correctness testing security edge-cases plan-fidelity)
fi

# Fallback matrix (from SKILL.md): when a tool is unavailable, skip its specialist
# slots entirely — do NOT substitute Claude fallback slots for partial outages.
# Only the both-down path (no external tools) uses a single Claude generic reviewer.
if [[ "$CODEX_AVAILABLE" == "false" && "$CURSOR_AVAILABLE" == "false" ]]; then
    launch_claude_slot "generic" "$REVIEW_TMPDIR/claude-generic-output.txt"
    panel_mode="both-down"
else
    panel_mode="normal"
    if [[ "$CURSOR_AVAILABLE" == "true" ]]; then
        for name in "${cursor_specialists[@]}"; do
            launch_external_slot cursor "$name" "$REVIEW_TMPDIR/cursor-specialist-${name}-output.txt"
        done
    fi
    # Cursor unavailable: skip Cursor specialist slots (no Claude substitution).
    if [[ "$CODEX_AVAILABLE" == "true" ]]; then
        for name in "${codex_specialists[@]}"; do
            launch_external_slot codex "$name" "$REVIEW_TMPDIR/codex-specialist-${name}-output.txt"
        done
    fi
    # Codex unavailable: skip Codex specialist slots (no Claude substitution).
    launch_claude_slot "generic" "$REVIEW_TMPDIR/claude-generic-output.txt"
fi

emit_kv EXTERNAL_OUTPUT_FILES "${external_outputs[*]-}"
emit_kv CLAUDE_OUTPUT_FILES "${claude_outputs[*]-}"
emit_kv PANEL_MODE "$panel_mode"
emit_kv PANEL_SHAPE "$PANEL"
emit_kv SLOT_COUNT "$slot_count"
emit_kv PANEL_MANIFEST "$manifest"
emit_kv DISPATCH_OK true
