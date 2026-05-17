#!/usr/bin/env bash
# dispatch-panel.sh — Plan and launch /review reviewer slots.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: dispatch-panel.sh --mode diff|description --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--panel simple|hard] [context flags]"; }

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
DISPATCH_WATERFALL="$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"
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
        --timing-task-prefix) shift 2 ;; # accepted for old harnesses; waterfall owns timing-task-kind naming
        --launch-claude-subprocess) shift 2 ;; # accepted for old harnesses; waterfall owns Claude launch
        --launch-review) shift 2 ;; # accepted for backward compat; waterfall owns launch routing
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-panel.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

# Export so launch-review.sh subprocesses inherit it and timing-ledger.sh
# can resolve the per-run ledger via the SESSION_ENV_PATH fallback.
export SESSION_ENV_PATH

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "dispatch-panel.sh: --mode must be diff or description"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "dispatch-panel.sh: --review-tmpdir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "dispatch-panel.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "dispatch-panel.sh: --cursor-available must be true or false"; exit 2; }
[[ "$PANEL" == "simple" || "$PANEL" == "hard" ]] || { larch_err "dispatch-panel.sh: --panel must be simple or hard"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

manifest="$REVIEW_TMPDIR/panel-manifest.ndjson"
: > "$manifest"
external_outputs=()
claude_outputs=()
slot_count=0

queue_external_slot() {
    local tool="$1" name="$2" out="$3"
    local agent="$PLUGIN_ROOT/agents/reviewer-${name}.md"
    printf '{"slot":"%s","tool":"%s","output":"%s","agent":"%s"}\n' "$name" "$tool" "$out" "$agent" >> "$manifest"
    slot_count=$((slot_count + 1))
}

queue_external_generalist_slot() {
    local tool="$1" out="$2"
    local agent="$PLUGIN_ROOT/agents/code-reviewer.md"
    printf '{"slot":"generic","tool":"%s","output":"%s","agent":"%s"}\n' "$tool" "$out" "$agent" >> "$manifest"
    slot_count=$((slot_count + 1))
}

# Plan file is required when reviewers run; plan-fidelity is always dispatched.
[[ -n "$PLAN_FILE" ]] || { larch_err "dispatch-panel.sh: --plan-file is required (plan-fidelity specialist is always dispatched)"; exit 2; }
[[ -f "$PLAN_FILE" ]] || { larch_err "dispatch-panel.sh: plan file not found: $PLAN_FILE"; exit 2; }

# Simple panel: 6 Cursor specialists + 1 Codex generalist.
# Hard panel: 6 Cursor specialists + 6 Codex specialists.
# Both panels always include plan-fidelity (plan file required above).
cursor_specialists=(structure correctness testing security edge-cases plan-fidelity)
if [[ "$PANEL" == "hard" ]]; then
    codex_specialists=(structure correctness testing security edge-cases plan-fidelity)
fi

for name in "${cursor_specialists[@]}"; do
    queue_external_slot cursor "$name" "$REVIEW_TMPDIR/cursor-specialist-${name}-output.txt"
done
if [[ "$PANEL" == "hard" ]]; then
    for name in "${codex_specialists[@]}"; do
        queue_external_slot codex "$name" "$REVIEW_TMPDIR/codex-specialist-${name}-output.txt"
    done
else
    queue_external_generalist_slot codex "$REVIEW_TMPDIR/codex-generalist-output.txt"
fi

waterfall_args=(--slots-file "$manifest" --codex-present "$CODEX_AVAILABLE" --cursor-present "$CURSOR_AVAILABLE" --mode "$MODE" --timeout 1800)
[[ "$MODE" == "diff" && -n "$DIFF_FILE" ]] && waterfall_args+=(--diff-file "$DIFF_FILE" --commit-count "$COMMIT_COUNT")
[[ "$MODE" == "description" && -n "$SCOPE_FILES" ]] && waterfall_args+=(--description-text "${DESCRIPTION_TEXT:-description review}" --scope-files "$SCOPE_FILES")
[[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && waterfall_args+=(--plan-file "$PLAN_FILE")
[[ -n "$FEATURE_FILE" && -f "$FEATURE_FILE" ]] && waterfall_args+=(--feature-file "$FEATURE_FILE")
[[ -n "$COMPETITION_NOTICE_FILE" && -f "$COMPETITION_NOTICE_FILE" ]] && waterfall_args+=(--competition-notice "$COMPETITION_NOTICE_FILE")

waterfall_output=$("$DISPATCH_WATERFALL" "${waterfall_args[@]}")
all_outputs=""
all_tools=""
dispatch_ok="true"
while IFS= read -r line || [[ -n "$line" ]]; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        ALL_OUTPUT_FILES) all_outputs="$value" ;;
        ALL_OUTPUT_TOOLS) all_tools="$value" ;;
        DISPATCH_OK) dispatch_ok="$value" ;;
        WARN) emit_kv WARN "$value" ;;
    esac
done <<< "$waterfall_output"

external_outputs=()
claude_outputs=()
read -r -a outputs_arr <<< "$all_outputs"
read -r -a tools_arr <<< "$all_tools"
for idx in "${!outputs_arr[@]}"; do
    if [[ "${tools_arr[$idx]:-}" == "claude" ]]; then
        claude_outputs+=("${outputs_arr[$idx]}")
    else
        external_outputs+=("${outputs_arr[$idx]}")
    fi
done

emit_kv EXTERNAL_OUTPUT_FILES "${external_outputs[*]-}"
emit_kv CLAUDE_OUTPUT_FILES "${claude_outputs[*]-}"
emit_kv PANEL_MODE waterfall
emit_kv PANEL_SHAPE "$PANEL"
emit_kv SLOT_COUNT "$slot_count"
emit_kv PANEL_MANIFEST "$manifest"
emit_kv DISPATCH_OK "$dispatch_ok"
