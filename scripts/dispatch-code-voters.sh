#!/usr/bin/env bash
# dispatch-code-voters.sh — Launch /review code-review judge panel through waterfall fallback.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-code-voters.sh --ballot-file FILE --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE] [--diff-file FILE] [--plan-file FILE]"
}

BALLOT_FILE=""
REVIEW_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
DIFF_FILE=""
PLAN_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-code-voters.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "dispatch-code-voters.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "dispatch-code-voters.sh: --review-tmpdir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --cursor-available must be true or false"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

make_voter_prompt_file() {
    local label="$1"
    local prompt_file="$REVIEW_TMPDIR/${label}-vote-prompt.txt"
    {
        printf 'You are a scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted.\n'
        printf 'Vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants.\n'
        printf 'For items prefixed with [OUT_OF_SCOPE]: YES means file a GitHub issue for future tracking; NO means trivial/incorrect; EXONERATE means legitimate but not issue-worthy.\n'
        printf 'Do NOT modify files. Do NOT commit. Do NOT push.\n'
        printf '\nRead the ballot from this path: %s\n' "$BALLOT_FILE"
        printf '\nFor every ballot item, output exactly one line using the same FINDING_N: id from the ballot heading:\n'
        printf '  FINDING_N: YES\n'
        printf '  FINDING_N: NO -- one-line reason\n'
        printf '  FINDING_N: EXONERATE -- one-line reason\n'
        printf 'You must vote on every item. Do NOT skip any.\n'
    } > "$prompt_file"
    printf '%s' "$prompt_file"
}

ctx_args=()
mode="description"
[[ -n "$DIFF_FILE" && -f "$DIFF_FILE" ]] && mode="diff" && ctx_args+=(--diff-file "$DIFF_FILE")
[[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && ctx_args+=(--plan-file "$PLAN_FILE")

VOTER_1_PATH="$REVIEW_TMPDIR/claude-vote-output.txt"
claude_prompt=$(make_voter_prompt_file claude)
set +e
"$SCRIPT_DIR/launch-claude-review.sh" \
    --output "$VOTER_1_PATH" \
    --prompt-file "$claude_prompt" \
    --mode "$mode" \
    --timeout 1200 \
    --timing-task-kind claude-code-voter \
    "${ctx_args[@]+"${ctx_args[@]}"}" >/dev/null 2>&1
voter1_rc=$?
set -e
[[ -f "$VOTER_1_PATH.done" ]] || printf '%s\n' "$voter1_rc" > "$VOTER_1_PATH.done"

codex_prompt=$(make_voter_prompt_file codex)
cursor_prompt=$(make_voter_prompt_file cursor)
VOTER_2_BASE="$REVIEW_TMPDIR/codex-vote-output.txt"
VOTER_3_BASE="$REVIEW_TMPDIR/cursor-vote-output.txt"
manifest="$REVIEW_TMPDIR/code-voter-slots.ndjson"
{
    printf '{"slot":"voter-2","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$VOTER_2_BASE" "$codex_prompt"
    printf '{"slot":"voter-3","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$VOTER_3_BASE" "$cursor_prompt"
} > "$manifest"

waterfall_output=$("$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present "$CODEX_AVAILABLE" \
    --cursor-present "$CURSOR_AVAILABLE" \
    --mode "$mode" \
    --timeout 1200 \
    "${ctx_args[@]+"${ctx_args[@]}"}")

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

read -r -a outputs_arr <<< "$all_outputs"
read -r -a tools_arr <<< "$all_tools"

VOTER_1_TOOL="claude"
VOTER_1_STATUS="launched"
[[ "$voter1_rc" -eq 0 && -s "$VOTER_1_PATH" ]] || VOTER_1_STATUS="failed"
VOTER_2_PATH="${outputs_arr[0]:-}"
VOTER_3_PATH="${outputs_arr[1]:-}"
VOTER_2_TOOL="${tools_arr[0]:-codex}"
VOTER_3_TOOL="${tools_arr[1]:-cursor}"
VOTER_2_STATUS="launched"
VOTER_3_STATUS="launched"
[[ "$VOTER_2_TOOL" == "claude" ]] && VOTER_2_STATUS="fallback"
[[ "$VOTER_3_TOOL" == "claude" ]] && VOTER_3_STATUS="fallback"
[[ -s "$VOTER_2_PATH" ]] || VOTER_2_STATUS="failed"
[[ -s "$VOTER_3_PATH" ]] || VOTER_3_STATUS="failed"

effective_judges=0
for status_path in "$VOTER_1_STATUS:$VOTER_1_PATH" "$VOTER_2_STATUS:$VOTER_2_PATH" "$VOTER_3_STATUS:$VOTER_3_PATH"; do
    status="${status_path%%:*}"
    path="${status_path#*:}"
    [[ "$status" != "failed" && -s "$path" ]] && effective_judges=$((effective_judges + 1))
done
if (( effective_judges < 3 )); then
    _warn_msg="**⚠ Degraded code-review panel: ${effective_judges}/3 effective judges produced output.**"
    larch_err "$_warn_msg"
    emit_kv DEGRADED_PANEL_WARNING "$_warn_msg"
fi

emit_kv VOTER_1_PATH "$VOTER_1_PATH"
emit_kv VOTER_1_TOOL "$VOTER_1_TOOL"
emit_kv VOTER_1_STATUS "$VOTER_1_STATUS"
emit_kv VOTER_2_PATH "$VOTER_2_PATH"
emit_kv VOTER_2_TOOL "$VOTER_2_TOOL"
emit_kv VOTER_2_STATUS "$VOTER_2_STATUS"
emit_kv VOTER_3_PATH "$VOTER_3_PATH"
emit_kv VOTER_3_TOOL "$VOTER_3_TOOL"
emit_kv VOTER_3_STATUS "$VOTER_3_STATUS"
[[ "$VOTER_1_STATUS" == "failed" ]] && dispatch_ok="false"
emit_kv DISPATCH_OK "$dispatch_ok"
