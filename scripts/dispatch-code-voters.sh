#!/usr/bin/env bash
# dispatch-code-voters.sh — Launch /review code-review judge panel through waterfall fallback.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-voter-parse-rate.sh
source "$SCRIPT_DIR/lib-voter-parse-rate.sh"

usage() {
    larch_err "Usage: dispatch-code-voters.sh --ballot-file FILE --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE] [--diff-file FILE] [--plan-file FILE] [--round-num N]"
}

BALLOT_FILE=""
REVIEW_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
DIFF_FILE=""
PLAN_FILE=""
ROUND_NUM="1"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-code-voters.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "dispatch-code-voters.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "dispatch-code-voters.sh: --review-tmpdir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --cursor-available must be true or false"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "dispatch-code-voters.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "dispatch-code-voters.sh: --round-num must be a positive integer"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

make_voter_prompt_file() {
    local label="$1"
    local prompt_file="$REVIEW_TMPDIR/${label}-vote-prompt.txt"
    "$PLUGIN_ROOT/skills/shared/scripts/render-voter-prompt.sh" \
        --ballot-file "$BALLOT_FILE" \
        --panel-role "scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted" \
        --id-grammar finding-only \
        --verification-context code > "$prompt_file"
    printf '%s' "$prompt_file"
}

make_bounded_context_copy() {
    local label="$1"
    local src="$2"
    local max_bytes="$3"
    local dest
    [[ -n "$src" && -f "$src" ]] || return 0
    dest="$REVIEW_TMPDIR/${label}-context.txt"
    python3 - "$src" "$dest" "$max_bytes" <<'PY'
import pathlib
import sys

src = pathlib.Path(sys.argv[1])
dest = pathlib.Path(sys.argv[2])
limit = int(sys.argv[3])
data = src.read_bytes()[:limit]
dest.write_bytes(data)
PY
    printf '%s' "$dest"
}

ctx_args=()
mode="description"
bounded_diff="$(make_bounded_context_copy diff "$DIFF_FILE" 200000)"
bounded_plan="$(make_bounded_context_copy plan "$PLAN_FILE" 60000)"
[[ -n "$bounded_diff" ]] && ctx_args+=(--diff-file "$bounded_diff")
[[ -n "$bounded_plan" ]] && ctx_args+=(--plan-file "$bounded_plan")

LARCH_VPR_BALLOT_FILE="$BALLOT_FILE"
LARCH_VPR_ID_GRAMMAR=finding-only
LARCH_VPR_REVIEW_TMPDIR="$REVIEW_TMPDIR"
LARCH_VPR_RETRY_PREFIX_KIND=code
LARCH_VPR_LAUNCH_MODE="$mode"
LARCH_VPR_PLUGIN_ROOT="$PLUGIN_ROOT"
LARCH_VPR_DISPATCH_LABEL="dispatch-code-voters.sh"
LARCH_VPR_CTX=()
[[ -n "$bounded_diff" ]] && LARCH_VPR_CTX+=(--diff-file "$bounded_diff")
[[ -n "$bounded_plan" ]] && LARCH_VPR_CTX+=(--plan-file "$bounded_plan")

VOTER_1_PATH="$REVIEW_TMPDIR/claude-vote-output.txt"
claude_prompt=$(make_voter_prompt_file claude)
set +e
"$SCRIPT_DIR/launch-claude-review.sh" \
    --output "$VOTER_1_PATH" \
    --prompt-file "$claude_prompt" \
    --mode "$mode" \
    --role voter \
    --timeout 1200 \
    --timing-task-kind claude-code-voter \
    "${ctx_args[@]+"${ctx_args[@]}"}" >/dev/null 2> "${VOTER_1_PATH}.launcher-stderr"
voter1_rc=$?
set -e
[[ -f "$VOTER_1_PATH.done" ]] || printf '%s\n' "$voter1_rc" > "$VOTER_1_PATH.done"

# Log diagnostic when Claude voter fails or produces empty output.
if [[ "$voter1_rc" -ne 0 || ! -s "$VOTER_1_PATH" ]]; then
    _voter1_diag="$REVIEW_TMPDIR/voter1-diag.txt"
    {
        printf 'voter1_rc=%s\n' "$voter1_rc"
        printf 'output_bytes=%s\n' "$(wc -c < "$VOTER_1_PATH" 2>/dev/null || echo 0)"
        if [[ "$voter1_rc" -ne 0 && -s "$VOTER_1_PATH" ]]; then
            printf -- '--- first 200 bytes of voter output ---\n'
            head -c 200 "$VOTER_1_PATH" || true
            printf '\n'
        fi
        if [[ -s "${VOTER_1_PATH}.diag" ]]; then
            printf -- '--- first 200 bytes of .diag ---\n'
            head -c 200 "${VOTER_1_PATH}.diag"
            printf '\n'
        fi
        if [[ -s "${VOTER_1_PATH}.launcher-stderr" ]]; then
            printf -- '--- launcher stderr (first 500 bytes) ---\n'
            head -c 500 "${VOTER_1_PATH}.launcher-stderr"
            printf '\n'
        fi
    } > "$_voter1_diag" || true
    _issues_log="${LARCH_EXECUTION_ISSUES_LOG:-}"
    if [[ -z "$_issues_log" && -n "${SESSION_ENV_PATH:-}" ]]; then
        _issues_log="$(dirname "$SESSION_ENV_PATH")/execution-issues.md"
    fi
    if [[ -z "$_issues_log" && -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        _issues_log="$IMPLEMENT_TMPDIR/execution-issues.md"
    fi
    [[ -z "$_issues_log" ]] && _issues_log="$REVIEW_TMPDIR/execution-issues.md"
    if [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]]; then
        _status_label="failed"
        [[ "$voter1_rc" -eq 0 ]] && _status_label="warning"
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$_issues_log" \
            --site "dispatch-code-voters.sh voter1" \
            --tool "launch-claude-review.sh (claude voter)" \
            --exit-code "$voter1_rc" \
            --status-label "$_status_label" \
            --category Warnings \
            --output-file "$_voter1_diag" \
            --redact >/dev/null 2>&1 || true
    fi
    unset _voter1_diag _issues_log _status_label
fi

codex_prompt=$(make_voter_prompt_file codex)
cursor_prompt=$(make_voter_prompt_file cursor)
VOTER_2_BASE="$REVIEW_TMPDIR/codex-vote-output.txt"
VOTER_3_BASE="$REVIEW_TMPDIR/cursor-vote-output.txt"
manifest="$REVIEW_TMPDIR/code-voter-slots.ndjson"
{
    printf '{"slot":"voter-2","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$VOTER_2_BASE" "$codex_prompt"
    printf '{"slot":"voter-3","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$VOTER_3_BASE" "$cursor_prompt"
} > "$manifest"

codex_present_for_waterfall="$CODEX_AVAILABLE"
waterfall_output=$("$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present "$codex_present_for_waterfall" \
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

VOTER_1_PARSE_RATE_STATUS="SKIPPED"
VOTER_2_PARSE_RATE_STATUS="SKIPPED"
VOTER_3_PARSE_RATE_STATUS="SKIPPED"
[[ "$VOTER_1_STATUS" != "failed" ]] && VOTER_1_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 1 "$VOTER_1_PATH" "$VOTER_1_TOOL" "$claude_prompt")
[[ "$VOTER_2_STATUS" != "failed" && "$VOTER_2_STATUS" != "skipped" ]] && VOTER_2_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 2 "$VOTER_2_PATH" "$VOTER_2_TOOL" "$codex_prompt")
[[ "$VOTER_3_STATUS" != "failed" ]] && VOTER_3_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 3 "$VOTER_3_PATH" "$VOTER_3_TOOL" "$cursor_prompt")

# Every round expects three judge slots (Claude + Codex + Cursor); unavailable externals waterfall to Claude.
expected_judges=3

effective_judges=0
for slot_record in \
    "$VOTER_1_STATUS"$'\t'"$VOTER_1_PATH"$'\t'"$VOTER_1_PARSE_RATE_STATUS" \
    "$VOTER_2_STATUS"$'\t'"$VOTER_2_PATH"$'\t'"$VOTER_2_PARSE_RATE_STATUS" \
    "$VOTER_3_STATUS"$'\t'"$VOTER_3_PATH"$'\t'"$VOTER_3_PARSE_RATE_STATUS"; do
    IFS=$'\t' read -r status path parse_rate_status <<< "$slot_record"
    [[ "$status" != "failed" && "$status" != "skipped" && "$parse_rate_status" != "NOT_SUBSTANTIVE" && -s "$path" ]] && effective_judges=$((effective_judges + 1))
done
if (( effective_judges < expected_judges )); then
    _warn_msg="**⚠ Degraded code-review panel: ${effective_judges}/${expected_judges} effective judges produced output.**"
    larch_err "$_warn_msg"
    emit_kv DEGRADED_PANEL_WARNING "$_warn_msg"
fi

emit_kv VOTER_1_PATH "$VOTER_1_PATH"
emit_kv VOTER_1_TOOL "$VOTER_1_TOOL"
emit_kv VOTER_1_STATUS "$VOTER_1_STATUS"
emit_kv VOTER_1_PARSE_RATE_STATUS "$VOTER_1_PARSE_RATE_STATUS"
emit_kv VOTER_2_PATH "$VOTER_2_PATH"
emit_kv VOTER_2_TOOL "$VOTER_2_TOOL"
emit_kv VOTER_2_STATUS "$VOTER_2_STATUS"
emit_kv VOTER_2_PARSE_RATE_STATUS "$VOTER_2_PARSE_RATE_STATUS"
emit_kv VOTER_3_PATH "$VOTER_3_PATH"
emit_kv VOTER_3_TOOL "$VOTER_3_TOOL"
emit_kv VOTER_3_STATUS "$VOTER_3_STATUS"
emit_kv VOTER_3_PARSE_RATE_STATUS "$VOTER_3_PARSE_RATE_STATUS"

code_voter_paths_file="$REVIEW_TMPDIR/code-voter-paths.txt"
cv_tmp=$(mktemp "${REVIEW_TMPDIR}/.code-voter-paths.XXXXXX")
if [[ -n "$VOTER_1_PATH" ]]; then
    printf '%s\n' "$VOTER_1_PATH" >> "$cv_tmp"
fi
if [[ "$VOTER_2_STATUS" != "skipped" && -n "$VOTER_2_PATH" ]]; then
    printf '%s\n' "$VOTER_2_PATH" >> "$cv_tmp"
fi
if [[ -n "$VOTER_3_PATH" ]]; then
    printf '%s\n' "$VOTER_3_PATH" >> "$cv_tmp"
fi
mv -f "$cv_tmp" "$code_voter_paths_file"
emit_kv VOTER_PATHS_FILE "$code_voter_paths_file"

[[ "$VOTER_1_STATUS" == "failed" ]] && dispatch_ok="false"
emit_kv DISPATCH_OK "$dispatch_ok"
