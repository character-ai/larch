#!/usr/bin/env bash
# launch-claude-review.sh — Launch Claude as a read-only reviewer subprocess.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: launch-claude-review.sh --output <file> (--agent-file <file>|--prompt-file <file>|--prompt <text>) --mode diff|description [context flags]"
}

OUTPUT=""
AGENT_FILE=""
PROMPT_FILE=""
PROMPT=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
DIFF_FILE=""
COMMIT_COUNT=""
PLAN_FILE=""
FEATURE_FILE=""
TIMEOUT="1800"
TIMING_TASK_KIND="claude-review"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|--output-file) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --agent-file) AGENT_FILE="${2:?--agent-file requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --timing-task-kind) TIMING_TASK_KIND="${2:?--timing-task-kind requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "launch-claude-review.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$OUTPUT" ]] || { larch_err "launch-claude-review.sh: --output is required"; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "launch-claude-review.sh: --timeout must be a positive integer"; exit 2 ;; esac

src_count=0
[[ -n "$AGENT_FILE" ]] && src_count=$((src_count + 1))
[[ -n "$PROMPT_FILE" ]] && src_count=$((src_count + 1))
[[ -n "$PROMPT" ]] && src_count=$((src_count + 1))
[[ "$src_count" -eq 1 ]] || { larch_err "launch-claude-review.sh: exactly one of --agent-file, --prompt-file, or --prompt is required"; exit 2; }

mkdir -p "$(dirname "$OUTPUT")"
TEMP_PROMPT=""
# shellcheck disable=SC2317
cleanup() {
    [[ -n "$TEMP_PROMPT" ]] && rm -f "$TEMP_PROMPT"
    return 0
}
trap cleanup EXIT

if [[ -n "$AGENT_FILE" ]]; then
    [[ -n "$MODE" ]] || { larch_err "launch-claude-review.sh: --mode is required with --agent-file"; exit 2; }
    render_args=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && render_args+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && render_args+=(--scope-files "$SCOPE_FILES")
    [[ -n "$DIFF_FILE" ]] && render_args+=(--diff-file "$DIFF_FILE")
    [[ -n "$COMMIT_COUNT" ]] && render_args+=(--commit-count "$COMMIT_COUNT")
    [[ -n "$PLAN_FILE" ]] && render_args+=(--plan-file "$PLAN_FILE")
    [[ -n "$FEATURE_FILE" ]] && render_args+=(--feature-file "$FEATURE_FILE")
    TEMP_PROMPT=$(mktemp "$(dirname "$OUTPUT")/claude-review-prompt.XXXXXX")
    "$SCRIPT_DIR/render-specialist-prompt.sh" "${render_args[@]}" > "$TEMP_PROMPT"
    PROMPT_FILE="$TEMP_PROMPT"
elif [[ -n "$PROMPT" ]]; then
    TEMP_PROMPT=$(mktemp "$(dirname "$OUTPUT")/claude-review-prompt.XXXXXX")
    printf '%s\n' "$PROMPT" > "$TEMP_PROMPT"
    PROMPT_FILE="$TEMP_PROMPT"
fi

ctx_args=()
allow_root_args=()
seen_allow_roots=""
append_context_file() {
    local path="$1" dir
    [[ -n "$path" && -f "$path" ]] || return 0
    ctx_args+=(--context-files "$path")
    dir="$(dirname "$path")"
    case ":$seen_allow_roots:" in
        *":$dir:"*) ;;
        *) allow_root_args+=(--allow-root "$dir"); seen_allow_roots="${seen_allow_roots}:$dir" ;;
    esac
}
append_context_file "$DIFF_FILE"
append_context_file "$SCOPE_FILES"
append_context_file "$PLAN_FILE"
append_context_file "$FEATURE_FILE"

set +e
"$SCRIPT_DIR/launch-claude-subprocess.sh" \
    --prompt-file "$PROMPT_FILE" \
    --output-file "$OUTPUT" \
    --timeout "$TIMEOUT" \
    --timing-task-kind "$TIMING_TASK_KIND" \
    ${allow_root_args[@]+"${allow_root_args[@]}"} \
    ${ctx_args[@]+"${ctx_args[@]}"}
rc=$?
set -e

if [[ ! -f "${OUTPUT}.done" ]]; then
    printf '%s\n' "$rc" > "${OUTPUT}.done"
fi
exit "$rc"
