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
        printf 'Use any provided diff/plan context files to verify the ballot claims before voting.\n'
        printf '\nFor every ballot item, output exactly one line using the same FINDING_N: id from the ballot heading:\n'
        printf '  FINDING_N: YES\n'
        printf '  FINDING_N: NO -- one-line reason\n'
        printf '  FINDING_N: EXONERATE -- one-line reason\n'
        printf 'You must vote on every item. Do NOT skip any.\n'
        printf 'IMPORTANT: lines that do not start with FINDING_N: followed by YES, NO, or EXONERATE are silently ignored. Use the exact ID from the ballot heading.\n'
    } > "$prompt_file"
    printf '%s' "$prompt_file"
}

VOTER_PARSE_RATE_RETRY_PREFIX='IMPORTANT: Your previous attempt produced narrative output instead of structured votes. Each line MUST start with FINDING_N: followed by exactly one of YES, NO, or EXONERATE. Do not output any prose, reasoning, or status updates before, between, or after the vote lines. If you need to verify claims, do so silently. Output ONLY vote lines.'

make_voter_retry_prompt_file() {
    local label="$1"
    local src_prompt_file="$2"
    local retry_prompt_file="$REVIEW_TMPDIR/${label}-vote-prompt-retry.txt"
    {
        printf '%s\n\n' "$VOTER_PARSE_RATE_RETRY_PREFIX"
        cat "$src_prompt_file"
    } > "$retry_prompt_file"
    printf '%s' "$retry_prompt_file"
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

parse_rate_check_tool_label() {
    local voter_tool="$1"
    case "$voter_tool" in
        claude) printf 'launch-claude-review.sh (voter parse-rate check)\n' ;;
        codex|cursor) printf 'launch-review.sh --tool %s (voter parse-rate check)\n' "$voter_tool" ;;
        *) printf 'voter parse-rate check (%s)\n' "$voter_tool" ;;
    esac
}

is_harness_review_path() {
    local path="$1"
    case "$path" in
        */test-dispatch-code-voters.*|\
        */test-collect-*|\
        */test-check-*|\
        */test-tally-*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

should_suppress_parse_rate_issue_append() {
    local voter_path="$1"
    [[ "$voter_path" == "$REVIEW_TMPDIR"/* ]] || return 1
    is_harness_review_path "$REVIEW_TMPDIR" || is_harness_review_path "$voter_path"
}

check_voter_parse_rate() {
    local voter_path="$1" voter_tool="$2" slot_num="${3:-}" log_mode="${4:-log}"
    local diag_file
    diag_file="$(voter_parse_rate_diag_path "$voter_path")"
    [[ -s "$voter_path" ]] || { printf 'PARSE_RATE_STATUS=OK\n'; return 0; }
    local ids_count judge_error_count
    ids_count=$(grep -cE '^### (FINDING_[0-9]+):' "$BALLOT_FILE" 2>/dev/null || true)
    ids_count="${ids_count:-0}"
    [[ "$ids_count" -gt 0 ]] || { printf 'PARSE_RATE_STATUS=OK\n'; return 0; }
    # Count how many ballot IDs produce JUDGE_ERROR in the voter file.
    judge_error_count=$(grep -oE '^### FINDING_[0-9]+:' "$BALLOT_FILE" 2>/dev/null | \
        awk '{sub(/:$/, "", $2); print $2}' | \
        while IFS= read -r id; do
            awk -v id="$id" '
              BEGIN { result="JUDGE_ERROR" }
              {
                upper=toupper($0)
                prefix="^" toupper(id) ":[[:space:]]*"
                if (upper ~ (prefix "(YES|NO|EXONERATE)([[:space:]-]|$)")) {
                    rest=upper; sub(prefix, "", rest)
                    if (rest ~ /^YES([[:space:]-]|$)/) result="YES"
                    else if (rest ~ /^NO([[:space:]-]|$)/) result="NO"
                    else if (rest ~ /^EXONERATE([[:space:]-]|$)/) result="EXONERATE"
                }
              }
              END { print result }
            ' "$voter_path"
        done | grep -c '^JUDGE_ERROR' || true)
    judge_error_count="${judge_error_count:-0}"
    # >=80% JUDGE_ERROR threshold
    if awk -v n="$judge_error_count" -v t="$ids_count" 'BEGIN { exit (n / t >= 0.8) ? 0 : 1 }'; then
        {
            [[ -n "$slot_num" ]] && printf 'slot=%s\n' "$slot_num"
            printf 'voter_tool=%s\n' "$voter_tool"
            printf 'judge_error_count=%s\n' "$judge_error_count"
            printf 'total_findings=%s\n' "$ids_count"
            printf 'voter_file=%s\n' "$voter_path"
            printf 'voter_sha256=%s\n' "$(voter_output_sha256 "$voter_path")"
            printf -- '--- first 200 bytes of voter output ---\n'
            head -c 200 "$voter_path" 2>/dev/null || true
            printf '\n'
        } > "$diag_file" || true
        if [[ "$log_mode" == "log" ]]; then
            larch_err "**⚠ Voter ${voter_tool}: ${judge_error_count}/${ids_count} findings returned JUDGE_ERROR — voter likely produced prose without FINDING_N: VOTE lines. Check voter output at ${voter_path}.**"
            _issues_log="${LARCH_EXECUTION_ISSUES_LOG:-}"
            [[ -z "$_issues_log" && -n "${SESSION_ENV_PATH:-}" ]] && _issues_log="$(dirname "$SESSION_ENV_PATH")/execution-issues.md"
            [[ -z "$_issues_log" && -n "${IMPLEMENT_TMPDIR:-}" ]] && _issues_log="$IMPLEMENT_TMPDIR/execution-issues.md"
            [[ -z "$_issues_log" ]] && _issues_log="$REVIEW_TMPDIR/execution-issues.md"
            if ! should_suppress_parse_rate_issue_append "$voter_path" && [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]]; then
                "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
                    --log "$_issues_log" \
                    --site "dispatch-code-voters.sh ${voter_tool}" \
                    --tool "$(parse_rate_check_tool_label "$voter_tool")" \
                    --exit-code 0 \
                    --status-label "warning" \
                    --category Warnings \
                    --output-file "$diag_file" \
                    --redact >/dev/null 2>&1 || true
            fi
            unset _issues_log
        fi
        printf 'PARSE_RATE_STATUS=NOT_SUBSTANTIVE\n'
    else
        rm -f "$diag_file"
        printf 'PARSE_RATE_STATUS=OK\n'
    fi
}

parse_rate_status_from_output() {
    awk -F= '$1=="PARSE_RATE_STATUS" { print $2; found=1 } END { if (!found) print "OK" }'
}

launch_voter_retry() {
    local voter_tool="$1" retry_output="$2" retry_prompt="$3" timing_task="$4"
    set +e
    case "$voter_tool" in
        claude)
            "$SCRIPT_DIR/launch-claude-review.sh" \
                --output "$retry_output" \
                --prompt-file "$retry_prompt" \
                --mode "$mode" \
                --role voter \
                --timeout 1200 \
                --timing-task-kind "$timing_task" \
                "${ctx_args[@]+"${ctx_args[@]}"}" >/dev/null 2> "${retry_output}.launcher-stderr"
            ;;
        codex|cursor)
            "$SCRIPT_DIR/launch-review.sh" \
                --tool "$voter_tool" \
                --output "$retry_output" \
                --prompt-file "$retry_prompt" \
                --mode "$mode" \
                --timeout 1200 \
                --timing-task-kind "$timing_task" \
                "${ctx_args[@]+"${ctx_args[@]}"}" >/dev/null 2> "${retry_output}.launcher-stderr"
            ;;
        *)
            larch_err "dispatch-code-voters.sh: unknown voter retry tool: $voter_tool"
            return 2
            ;;
    esac
    local rc=$?
    set -e
    [[ -f "${retry_output}.done" ]] || printf '%s\n' "$rc" > "${retry_output}.done"
    return "$rc"
}

check_and_retry_voter_parse_rate() {
    local slot_num="$1" voter_path="$2" voter_tool="$3" prompt_file="$4"
    local status retry_prompt retry_output retry_rc retry_status diag_file retry_diag_file first_pass_sidecar
    diag_file="$(voter_parse_rate_diag_path "$voter_path")"
    case "$voter_path" in
        *.txt) first_pass_sidecar="${voter_path%.txt}-first-pass.txt" ;;
        *) first_pass_sidecar="${voter_path}-first-pass" ;;
    esac
    rm -f "$first_pass_sidecar" || true
    status=$(check_voter_parse_rate "$voter_path" "$voter_tool" "$slot_num" silent | parse_rate_status_from_output)
    [[ "$status" == "NOT_SUBSTANTIVE" ]] || { printf '%s\n' "$status"; return 0; }

    retry_prompt=$(make_voter_retry_prompt_file "$voter_tool" "$prompt_file")
    case "$voter_path" in
        *.txt) retry_output="${voter_path%.txt}-parse-retry.txt" ;;
        *) retry_output="${voter_path}-parse-retry" ;;
    esac
    retry_diag_file="$(voter_parse_rate_diag_path "$retry_output")"
    rm -f "$retry_output" "${retry_output}.done" "${retry_output}.launcher-stderr"

    set +e
    launch_voter_retry "$voter_tool" "$retry_output" "$retry_prompt" "${voter_tool}-voter-${slot_num}-parse-retry"
    retry_rc=$?
    set -e
    if [[ "$retry_rc" -eq 0 && -s "$retry_output" ]]; then
        retry_status=$(check_voter_parse_rate "$retry_output" "$voter_tool" "$slot_num" silent | parse_rate_status_from_output)
        if [[ "$retry_status" == "OK" ]]; then
            if cp "$voter_path" "$first_pass_sidecar" 2>/dev/null; then
                # Stderr so callers that capture this function's stdout (parse-rate status) are not polluted.
                { emit_breadcrumb "voter-${voter_tool}: first-pass content preserved at $(basename "$first_pass_sidecar") (parse-rate retry succeeded)"; } >&2
            else
                larch_err "dispatch-code-voters.sh: warning: failed to preserve first-pass voter output at $first_pass_sidecar after parse-rate retry succeeded"
            fi
            mv "$retry_output" "$voter_path"
            if [[ -f "${retry_output}.done" ]]; then
                mv "${retry_output}.done" "${voter_path}.done"
            else
                printf '0\n' > "${voter_path}.done"
            fi
            rm -f "$diag_file" "$retry_diag_file" "${retry_output}.launcher-stderr"
            printf 'OK\n'
            return 0
        fi
    fi

    rm -f "$retry_output" "${retry_output}.done" "${retry_output}.launcher-stderr" "$retry_diag_file"
    check_voter_parse_rate "$voter_path" "$voter_tool" "$slot_num" log | parse_rate_status_from_output
}

ctx_args=()
mode="description"
bounded_diff="$(make_bounded_context_copy diff "$DIFF_FILE" 200000)"
bounded_plan="$(make_bounded_context_copy plan "$PLAN_FILE" 60000)"
[[ -n "$bounded_diff" ]] && ctx_args+=(--diff-file "$bounded_diff")
[[ -n "$bounded_plan" ]] && ctx_args+=(--plan-file "$bounded_plan")

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

VOTER_1_PARSE_RATE_STATUS="SKIPPED"
VOTER_2_PARSE_RATE_STATUS="SKIPPED"
VOTER_3_PARSE_RATE_STATUS="SKIPPED"
[[ "$VOTER_1_STATUS" != "failed" ]] && VOTER_1_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 1 "$VOTER_1_PATH" "$VOTER_1_TOOL" "$claude_prompt")
[[ "$VOTER_2_STATUS" != "failed" ]] && VOTER_2_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 2 "$VOTER_2_PATH" "$VOTER_2_TOOL" "$codex_prompt")
[[ "$VOTER_3_STATUS" != "failed" ]] && VOTER_3_PARSE_RATE_STATUS=$(check_and_retry_voter_parse_rate 3 "$VOTER_3_PATH" "$VOTER_3_TOOL" "$cursor_prompt")

effective_judges=0
for slot_record in \
    "$VOTER_1_STATUS"$'\t'"$VOTER_1_PATH"$'\t'"$VOTER_1_PARSE_RATE_STATUS" \
    "$VOTER_2_STATUS"$'\t'"$VOTER_2_PATH"$'\t'"$VOTER_2_PARSE_RATE_STATUS" \
    "$VOTER_3_STATUS"$'\t'"$VOTER_3_PATH"$'\t'"$VOTER_3_PARSE_RATE_STATUS"; do
    IFS=$'\t' read -r status path parse_rate_status <<< "$slot_record"
    [[ "$status" != "failed" && "$parse_rate_status" != "NOT_SUBSTANTIVE" && -s "$path" ]] && effective_judges=$((effective_judges + 1))
done
if (( effective_judges < 3 )); then
    _warn_msg="**⚠ Degraded code-review panel: ${effective_judges}/3 effective judges produced output.**"
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
[[ "$VOTER_1_STATUS" == "failed" ]] && dispatch_ok="false"
emit_kv DISPATCH_OK "$dispatch_ok"
