#!/usr/bin/env bash
# dispatch-code-voters.sh — Launch the /review code-review judge panel: Claude
# (always) plus each available external (Codex, Cursor). Missing-binary externals
# are dropped via the waterfall's --no-fallback mode (shrink-not-backfill), never
# replaced by a duplicate judge; the acceptance-threshold table compensates for
# the smaller panel.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
CLI="$PLUGIN_ROOT/python/cli.py"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
[[ -f "$CLI" ]] || { larch_err "dispatch-code-voters.sh: missing python/cli.py at $CLI"; exit 2; }

usage() {
    larch_err "Usage: dispatch-code-voters.sh --ballot-file FILE --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE] [--diff-file FILE] [--plan-file FILE] [--round-num N]"
}

BALLOT_FILE=""
REVIEW_TMPDIR=""
CODEX_BINARY_FOUND=""
CURSOR_BINARY_FOUND=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
DIFF_FILE=""
PLAN_FILE=""
ROUND_NUM="1"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_BINARY_FOUND="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_BINARY_FOUND="${2:?--cursor-available requires a value}"; shift 2 ;;
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
[[ "$CODEX_BINARY_FOUND" == "true" || "$CODEX_BINARY_FOUND" == "false" ]] || { larch_err "dispatch-code-voters.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_BINARY_FOUND" == "true" || "$CURSOR_BINARY_FOUND" == "false" ]] || { larch_err "dispatch-code-voters.sh: --cursor-available must be true or false"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "dispatch-code-voters.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "dispatch-code-voters.sh: --round-num must be a positive integer"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

make_voter_prompt_file() {
    local label="$1"
    local prompt_file="$REVIEW_TMPDIR/${label}-vote-prompt.txt"
    if ! python3 "$PLUGIN_ROOT/python/cli.py" render voter \
            --ballot-file "$BALLOT_FILE" \
            --panel-role "scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted" \
            --id-grammar finding-oos \
            --verification-context code > "$prompt_file"; then
        larch_err "dispatch-code-voters.sh: python/cli.py render voter failed for $label voter; aborting"
        exit 2
    fi
    if ! grep -qF 'Read the ballot from this path' "$prompt_file"; then
        larch_err "dispatch-code-voters.sh: python/cli.py render voter output for $label voter is missing ballot pointer; aborting"
        exit 2
    fi
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

DISPATCH_LABEL="dispatch-code-voters.sh"
LAUNCH_MODE="$mode"
VPR_ARGS=(--ballot-file "$BALLOT_FILE" --id-grammar finding-oos --review-tmpdir "$REVIEW_TMPDIR" --plugin-root "$PLUGIN_ROOT" --dispatch-label "$DISPATCH_LABEL" --retry-prefix-kind code --launch-mode "$LAUNCH_MODE")
[[ -n "$bounded_diff" ]] && VPR_ARGS+=(--ctx=--diff-file --ctx "$bounded_diff")
[[ -n "$bounded_plan" ]] && VPR_ARGS+=(--ctx=--plan-file --ctx "$bounded_plan")

VOTER_1_PATH="$REVIEW_TMPDIR/claude-vote-output.txt"
claude_prompt=$(make_voter_prompt_file claude)
codex_prompt=$(make_voter_prompt_file codex)
cursor_prompt=$(make_voter_prompt_file cursor)

# #3704: dispatch all three voters in parallel. The Claude voter is backgrounded
# (its `.done` sentinel stays launcher-owned per #2973, so the wait barrier below
# still arbitrates completion) and the Codex+Cursor waterfall launches
# immediately — no serial gate between the Claude lane and the external lanes.
python3 "$CLI" agent launch-claude-review \
    --output "$VOTER_1_PATH" \
    --prompt-file "$claude_prompt" \
    --mode "$mode" \
    --role voter \
    --timeout 1200 \
    --timing-task-kind claude-code-voter \
    "${ctx_args[@]+"${ctx_args[@]}"}" >/dev/null 2> "${VOTER_1_PATH}.launcher-stderr" &
voter1_pid=$!

VOTER_2_BASE="$REVIEW_TMPDIR/codex-vote-output.txt"
VOTER_3_BASE="$REVIEW_TMPDIR/cursor-vote-output.txt"
manifest="$REVIEW_TMPDIR/code-voter-slots.ndjson"
{
    printf '{"slot":"voter-2","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$VOTER_2_BASE" "$codex_prompt"
    printf '{"slot":"voter-3","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$VOTER_3_BASE" "$cursor_prompt"
} > "$manifest"

codex_present_for_waterfall="$CODEX_BINARY_FOUND"
# Shrink-not-backfill: pass --no-fallback so an unavailable (or failed) external
# slot is dropped from the result set instead of being replaced by a duplicate
# judge (the alternate external, then Claude). The panel is Claude (always) plus
# each binary-present external; the acceptance-threshold table compensates for the
# smaller panel (2 judges → unanimous, 1 → binding single).
# Guard against non-zero exit from waterfall (e.g. a reviewer launcher exiting
# abnormally mid-run) so set -e does not abort dispatch before tally.
set +e
waterfall_output=$(python3 "$CLI" agent dispatch-waterfall \
    --slots-file "$manifest" \
    --codex-present "$codex_present_for_waterfall" \
    --cursor-present "$CURSOR_BINARY_FOUND" \
    --mode "$mode" \
    --timeout 1200 \
    --no-fallback \
    "${ctx_args[@]+"${ctx_args[@]}"}")
_waterfall_rc=$?
set -e
if [[ $_waterfall_rc -ne 0 ]]; then
    larch_err "dispatch-code-voters.sh: agent dispatch-waterfall exited $_waterfall_rc — proceeding with partial or empty result"
fi

# Reap the parallel Claude voter; it has been running concurrently with the
# external waterfall since dispatch.
set +e
wait "$voter1_pid"
voter1_rc=$?
set -e

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
    if command -v python3 >/dev/null 2>&1 && [[ -f "$PLUGIN_ROOT/python/cli.py" ]]; then
        _status_label="failed"
        [[ "$voter1_rc" -eq 0 ]] && _status_label="warning"
        python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$_issues_log" \
            --site "dispatch-code-voters.sh voter1" \
            --tool "agent launch-claude-review (claude voter)" \
            --exit-code "$voter1_rc" \
            --status-label "$_status_label" \
            --category Warnings \
            --output-file "$_voter1_diag" \
            --redact >/dev/null 2>&1 || true
    fi
    unset _voter1_diag _issues_log _status_label
fi

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
# Map waterfall outputs back to the codex/cursor slots by TOOL name, not by
# position. Under --no-fallback an absent or failed external is dropped from
# ALL_OUTPUT_FILES, so positional indexing is unreliable: when only cursor
# survives it would otherwise be mis-assigned to the codex slot. Externals never
# back-fill to Claude under --no-fallback, so each present output's tool is its
# own primary (codex or cursor).
VOTER_2_PATH=""
VOTER_3_PATH=""
VOTER_2_TOOL="codex"
VOTER_3_TOOL="cursor"
for _wf_i in "${!tools_arr[@]}"; do
    case "${tools_arr[$_wf_i]}" in
        codex)  VOTER_2_PATH="${outputs_arr[$_wf_i]:-}" ;;
        cursor) VOTER_3_PATH="${outputs_arr[$_wf_i]:-}" ;;
    esac
done
unset _wf_i
# A missing-binary external is intentionally skipped (no duplicate judge launched);
# Claude (voter 1) remains the always-on floor. A genuine failure of an
# *available* external is detected later by the size/sentinel re-evaluation and
# marked "failed" (which the degraded-panel check still counts as a degradation).
VOTER_2_STATUS="launched"
VOTER_3_STATUS="launched"
[[ "$CODEX_BINARY_FOUND" != "true" ]] && VOTER_2_STATUS="skipped"
[[ "$CURSOR_BINARY_FOUND" != "true" ]] && VOTER_3_STATUS="skipped"
voter1_wait_timed_out=false
_wait_rc=0

# FINDING_2: capture stdout — agent wait-reviewers emits TIMEOUT rows on
# stdout and exits 0 even when sentinels never appear, so an exit-only check
# would silently miss timeouts. FINDING_5: use if/fi (not arithmetic && cmd)
# because the arithmetic test returns 1 on the normal zero-exit path and would
# abort dispatch-code-voters.sh under set -e before parse-rate/tally.
wait_sentinels=()
[[ -n "$VOTER_1_PATH" ]] && wait_sentinels+=("${VOTER_1_PATH}.done")
[[ "$VOTER_2_STATUS" != "skipped" && -n "$VOTER_2_PATH" ]] && wait_sentinels+=("${VOTER_2_PATH}.done")
[[ "$VOTER_3_STATUS" != "skipped" && -n "$VOTER_3_PATH" ]] && wait_sentinels+=("${VOTER_3_PATH}.done")
if (( ${#wait_sentinels[@]} > 0 )); then
    _wait_out_file=$(mktemp "${REVIEW_TMPDIR}/voter-wait.XXXXXX")
    set +e
    python3 "$PLUGIN_ROOT/python/cli.py" agent wait-reviewers \
        --timeout "${LARCH_VOTER_WAIT_TIMEOUT:-60}" \
        "${wait_sentinels[@]}" >"$_wait_out_file" 2>&1
    _wait_rc=$?
    set -e
    # FINDING_2: detect TIMEOUT rows on stdout (wait-for-reviewers exits 0
    # even when sentinels never appear).
    if grep -q '^TIMEOUT ' "$_wait_out_file" 2>/dev/null; then
        while IFS= read -r _to_line; do
            larch_err "dispatch-code-voters.sh: voter sentinel $_to_line"
            case "$_to_line" in
                "TIMEOUT 1 "*) voter1_wait_timed_out=true ;;
            esac
        done < <(grep '^TIMEOUT ' "$_wait_out_file")
    fi
    # FINDING_5: rc=1 is a usage error (not a sentinel timeout); log distinctly.
    if (( _wait_rc != 0 )); then
        larch_err "dispatch-code-voters.sh: wait-for-reviewers.sh exited $_wait_rc (usage/config error) - proceeding with whatever state exists"
    fi
    rm -f "$_wait_out_file"
    unset _wait_out_file
fi

# If Claude returned successfully with substantive output but its launcher-owned
# sentinel still never appeared, publish a local sentinel only after the wait
# barrier so Voter 1 cannot be treated as complete before launcher completion
# had a chance to land.
if [[ ! -f "$VOTER_1_PATH.done" && "$voter1_rc" -eq 0 && -s "$VOTER_1_PATH" \
      && "$voter1_wait_timed_out" != "true" && "$_wait_rc" -eq 0 ]]; then
    printf '%s\n' "$voter1_rc" > "$VOTER_1_PATH.done"
fi
unset _wait_rc

read_done_exit_code() {
    local sentinel="$1"
    local rc=""
    [[ -f "$sentinel" ]] || return 0
    IFS= read -r rc < "$sentinel" || true
    printf '%s' "$rc"
}

voter1_done_rc=""
voter2_done_rc=""
voter3_done_rc=""
[[ -n "$VOTER_1_PATH" ]] && voter1_done_rc="$(read_done_exit_code "$VOTER_1_PATH.done")"
[[ -n "$VOTER_2_PATH" ]] && voter2_done_rc="$(read_done_exit_code "$VOTER_2_PATH.done")"
[[ -n "$VOTER_3_PATH" ]] && voter3_done_rc="$(read_done_exit_code "$VOTER_3_PATH.done")"

# Re-evaluate size-based statuses AFTER the wait barrier so a voter whose
# output became visible during the wait is correctly classified. A non-zero or
# missing launcher-owned `.done` sentinel is still a failed slot even if the
# output file is non-empty.
[[ "$voter1_rc" -eq 0 && -s "$VOTER_1_PATH" && "$voter1_done_rc" == "0" ]] || VOTER_1_STATUS="failed"
[[ "$VOTER_2_STATUS" == "skipped" || ( -s "$VOTER_2_PATH" && "$voter2_done_rc" == "0" ) ]] || VOTER_2_STATUS="failed"
[[ "$VOTER_3_STATUS" == "skipped" || ( -s "$VOTER_3_PATH" && "$voter3_done_rc" == "0" ) ]] || VOTER_3_STATUS="failed"

VOTER_1_PARSE_RATE_STATUS="SKIPPED"
VOTER_2_PARSE_RATE_STATUS="SKIPPED"
VOTER_3_PARSE_RATE_STATUS="SKIPPED"
[[ "$VOTER_1_STATUS" != "failed" ]] && VOTER_1_PARSE_RATE_STATUS=$(python3 "$CLI" voting parse-rate-retry "${VPR_ARGS[@]}" --slot 1 --voter-file "$VOTER_1_PATH" --voter-tool "$VOTER_1_TOOL" --prompt-file "$claude_prompt")
[[ "$VOTER_2_STATUS" != "failed" && "$VOTER_2_STATUS" != "skipped" ]] && VOTER_2_PARSE_RATE_STATUS=$(python3 "$CLI" voting parse-rate-retry "${VPR_ARGS[@]}" --slot 2 --voter-file "$VOTER_2_PATH" --voter-tool "$VOTER_2_TOOL" --prompt-file "$codex_prompt")
[[ "$VOTER_3_STATUS" != "failed" && "$VOTER_3_STATUS" != "skipped" ]] && VOTER_3_PARSE_RATE_STATUS=$(python3 "$CLI" voting parse-rate-retry "${VPR_ARGS[@]}" --slot 3 --voter-file "$VOTER_3_PATH" --voter-tool "$VOTER_3_TOOL" --prompt-file "$cursor_prompt")

# Shrink-not-backfill: the expected (eligible) panel is Claude (always) plus each
# binary-present external. Missing-binary externals are intentionally skipped, not
# back-filled, so they are NOT counted toward expected_judges — their absence is
# the designed state, not a degradation. The degraded-panel warning below then
# fires only when an *available* judge failed to produce substantive output.
expected_judges=1
[[ "$CODEX_BINARY_FOUND" == "true" ]] && expected_judges=$((expected_judges + 1))
[[ "$CURSOR_BINARY_FOUND" == "true" ]] && expected_judges=$((expected_judges + 1))

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
if [[ "$VOTER_3_STATUS" != "skipped" && -n "$VOTER_3_PATH" ]]; then
    printf '%s\n' "$VOTER_3_PATH" >> "$cv_tmp"
fi
mv -f "$cv_tmp" "$code_voter_paths_file"
emit_kv VOTER_PATHS_FILE "$code_voter_paths_file"

[[ "$VOTER_1_STATUS" == "failed" ]] && dispatch_ok="false"
emit_kv DISPATCH_OK "$dispatch_ok"
