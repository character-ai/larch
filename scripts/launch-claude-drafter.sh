#!/usr/bin/env bash
# launch-claude-drafter.sh — Launch a read-mostly Claude plan drafter subprocess.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh"
larch_quiet_init

usage() {
    larch_err "Usage: launch-claude-drafter.sh --model MODEL --prompt-file FILE --output-file FILE --timeout SECONDS --design-tmpdir DIR --repo-root DIR [--timing-task-kind KIND] [--baseline-porcelain FILE]"
}

MODEL=""
PROMPT_FILE=""
OUTPUT_FILE=""
TIMEOUT=""
DESIGN_TMPDIR=""
REPO_ROOT_ARG=""
TIMING_TASK_KIND="claude-plan-draft"
BASELINE_PORCELAIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="${2:?--model requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --output-file) OUTPUT_FILE="${2:?--output-file requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --repo-root) REPO_ROOT_ARG="${2:?--repo-root requires a value}"; shift 2 ;;
        --timing-task-kind) TIMING_TASK_KIND="${2:?--timing-task-kind requires a value}"; shift 2 ;;
        --baseline-porcelain) BASELINE_PORCELAIN="${2:?--baseline-porcelain requires a value}"; shift 2 ;;
        --read-tools|--read-tools-add-dir)
            larch_err "launch-claude-drafter.sh: $1 is a larch wrapper-only flag and is not supported here"
            exit 2
            ;;
        --help) usage; exit 0 ;;
        *) larch_err "launch-claude-drafter.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

has_control_chars() {
    printf '%s' "$1" | LC_ALL=C command grep -q '[[:cntrl:]]'
}

canonical_existing_file() {
    local p="$1" dir base
    [[ -n "$p" ]] || return 1
    has_control_chars "$p" && return 1
    [[ "$p" != *..* ]] || return 1
    [[ -f "$p" ]] || return 1
    [[ ! -L "$p" ]] || return 1
    dir=$(cd "$(dirname "$p")" && pwd -P) || return 1
    base=$(basename "$p")
    printf '%s/%s\n' "$dir" "$base"
}

canonical_output_path() {
    local p="$1" dir base
    [[ -n "$p" ]] || return 1
    has_control_chars "$p" && return 1
    [[ "$p" != *..* ]] || return 1
    [[ ! -e "$p" || ! -L "$p" ]] || return 1
    dir=$(cd "$(dirname "$p")" && pwd -P) || return 1
    base=$(basename "$p")
    printf '%s/%s\n' "$dir" "$base"
}

canonical_existing_dir() {
    local p="$1"
    [[ -n "$p" ]] || return 1
    has_control_chars "$p" && return 1
    [[ "$p" != *..* ]] || return 1
    [[ -d "$p" ]] || return 1
    [[ ! -L "$p" ]] || return 1
    (cd "$p" && pwd -P) || return 1
}

under_root() {
    local path="$1" root="$2"
    [[ "$path" == "$root" || "$path" == "$root/"* ]]
}

fail_prelaunch() {
    local reason="$1"
    if [[ -n "${OUTPUT_CANON:-}" ]]; then
        write_status_file "ERROR" "false" 0 0 "false" "false" "$reason" || true
        exit_code=2
        status="ERROR"
    fi
    larch_err "launch-claude-drafter.sh: $reason"
    exit 2
}

write_status_file() {
    local status_value="$1" plan_written="$2" plan_lines="$3" diff_lines="$4" summary_written="$5" launched="$6" reason="${7:-}"
    local tmp="${OUTPUT_CANON}.tmp.$$"
    {
        printf 'STATUS=%s\n' "$status_value"
        printf 'PLAN_WRITTEN=%s\n' "$plan_written"
        printf 'PLAN_LINES=%s\n' "$plan_lines"
        printf 'DIFF_LINES=%s\n' "$diff_lines"
        printf 'SUMMARY_WRITTEN=%s\n' "$summary_written"
        printf 'DRAFTER_LAUNCHED=%s\n' "$launched"
        [[ -z "$reason" ]] || printf 'REASON=%s\n' "$reason"
    } > "$tmp"
    mv -f "$tmp" "$OUTPUT_CANON"
}

# shellcheck disable=SC2329,SC2317 # invoked by the EXIT trap.
write_dirty_tree_sidecar() {
    [[ -n "${OUTPUT_CANON:-}" ]] || return 0
    local tmp="${OUTPUT_CANON}.dirty-tree.tmp.$$"
    local current_file="" diff_file="" dirty_status dirty_mode dirty_reason
    dirty_status="unknown"
    dirty_mode="prelaunch"
    dirty_reason="launcher-exited-before-drafter-launch"
    if [[ "${DRAFTER_LAUNCHED:-false}" == "true" ]]; then
        if [[ -n "${BASELINE_CANON:-}" && -f "${BASELINE_CANON:-}" && -r "${BASELINE_CANON:-}" ]]; then
            current_file=$(mktemp "${TMPDIR:-/tmp}/claude-drafter-status.XXXXXX") || current_file=""
            diff_file=$(mktemp "${TMPDIR:-/tmp}/claude-drafter-diff.XXXXXX") || diff_file=""
            if [[ -n "$current_file" && -n "$diff_file" ]] && git -C "$REPO_ROOT" status --porcelain > "$current_file" 2>/dev/null; then
                if diff -u "$BASELINE_CANON" "$current_file" > "$diff_file" 2>/dev/null; then
                    dirty_status="clean"
                    dirty_mode="baseline-delta"
                    dirty_reason="claude-drafter-no-new-mutations"
                else
                    dirty_status="dirty"
                    dirty_mode="baseline-delta"
                    dirty_reason="claude-drafter-new-mutations"
                fi
            else
                dirty_status="unknown"
                dirty_mode="baseline-delta"
                dirty_reason="git-status-failed"
            fi
        else
            current_file=$(mktemp "${TMPDIR:-/tmp}/claude-drafter-status.XXXXXX") || current_file=""
            if [[ -n "$current_file" ]] && git -C "$REPO_ROOT" status --porcelain > "$current_file" 2>/dev/null; then
                if [[ ! -s "$current_file" ]]; then
                    dirty_status="clean"
                    dirty_mode="absolute"
                    dirty_reason="claude-drafter-clean-working-tree"
                else
                    dirty_status="unknown"
                    dirty_mode="no-baseline"
                    dirty_reason="claude-drafter-no-usable-baseline"
                fi
            else
                dirty_status="unknown"
                dirty_mode="no-baseline"
                dirty_reason="git-status-failed"
            fi
        fi
    fi
    {
        printf 'STATUS=%s\n' "$dirty_status"
        printf 'MODE=%s\n' "$dirty_mode"
        printf 'REASON=%s\n' "$dirty_reason"
    } > "$tmp" 2>/dev/null && mv -f "$tmp" "${OUTPUT_CANON}.dirty-tree" 2>/dev/null || true
    [[ -z "$current_file" ]] || rm -f "$current_file"
    [[ -z "$diff_file" ]] || rm -f "$diff_file"
}

[[ -n "$MODEL" ]] || { larch_err "launch-claude-drafter.sh: --model is required"; exit 2; }
[[ -n "$PROMPT_FILE" ]] || { larch_err "launch-claude-drafter.sh: --prompt-file is required"; exit 2; }
[[ -n "$OUTPUT_FILE" ]] || { larch_err "launch-claude-drafter.sh: --output-file is required"; exit 2; }
[[ -n "$TIMEOUT" ]] || { larch_err "launch-claude-drafter.sh: --timeout is required"; exit 2; }
[[ -n "$DESIGN_TMPDIR" ]] || { larch_err "launch-claude-drafter.sh: --design-tmpdir is required"; exit 2; }
[[ -n "$REPO_ROOT_ARG" ]] || { larch_err "launch-claude-drafter.sh: --repo-root is required"; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "launch-claude-drafter.sh: --timeout must be a positive integer"; exit 2 ;; esac
(( 10#$TIMEOUT <= 1800 )) || { larch_err "launch-claude-drafter.sh: --timeout must be <= 1800"; exit 2; }
case "$MODEL" in *[[:space:]]*|*[$'\n\r\t']*|"") larch_err "launch-claude-drafter.sh: --model must be a single non-empty token"; exit 2 ;; esac
case "$TIMING_TASK_KIND" in ""|--*) larch_err "launch-claude-drafter.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2 ;; esac

DESIGN_CANON=$(canonical_existing_dir "$DESIGN_TMPDIR") || { larch_err "launch-claude-drafter.sh: invalid --design-tmpdir"; exit 2; }
REPO_ROOT=$(canonical_existing_dir "$REPO_ROOT_ARG") || { larch_err "launch-claude-drafter.sh: invalid --repo-root"; exit 2; }
PROMPT_CANON=$(canonical_existing_file "$PROMPT_FILE") || { larch_err "launch-claude-drafter.sh: invalid --prompt-file"; exit 2; }
OUTPUT_CANON=$(canonical_output_path "$OUTPUT_FILE") || { larch_err "launch-claude-drafter.sh: invalid --output-file"; exit 2; }

under_root "$OUTPUT_CANON" "$DESIGN_CANON" || { larch_err "launch-claude-drafter.sh: --output-file outside design tmpdir"; exit 2; }
# From here on, failures are post-output-canonicalization and must leave a dirty-tree sidecar.
DRAFTER_LAUNCHED=false
status="ERROR"
exit_code=2
START_S=$(date +%s)
trap 'write_dirty_tree_sidecar' EXIT
rm -f "${OUTPUT_CANON}.stderr-tail" "${OUTPUT_CANON}.failure-diag" "${OUTPUT_CANON}.json" "${OUTPUT_CANON}.result"
write_status_file "ERROR" "false" 0 0 "false" "false" "prelaunch"

under_root "$PROMPT_CANON" "$DESIGN_CANON" || under_root "$PROMPT_CANON" "$PLUGIN_ROOT" || fail_prelaunch "--prompt-file outside allowed roots"
BASELINE_CANON=""
if [[ -n "$BASELINE_PORCELAIN" ]]; then
    BASELINE_CANON=$(canonical_existing_file "$BASELINE_PORCELAIN") || fail_prelaunch "invalid --baseline-porcelain"
    under_root "$BASELINE_CANON" "$DESIGN_CANON" || fail_prelaunch "--baseline-porcelain outside design tmpdir"
fi

case "$TIMING_TASK_KIND" in
    *draft*) TOKEN_RAW=claude_draft ;;
    *scout*) TOKEN_RAW=claude_scout ;;
    *voter*) TOKEN_RAW=claude_vote ;;
    *)       TOKEN_RAW=claude_review ;;
esac

# Verified locally from `claude --help`: `--allowedTools` accepts a comma-separated
# list, and composes with `--add-dir`, `--print`, `--output-format json`, and
# `--permission-mode plan`. Do not pass larch wrapper-only `--read-tools*` flags.
CMD_JSON=$(jq -cn --arg model "$MODEL" --arg repo "$REPO_ROOT" \
    '["claude","--model",$model,"--print","--output-format","json","--add-dir",$repo,"--allowedTools","Read,Glob,Grep,LS","--permission-mode","plan"]')
{
    printf 'OUTER_LAUNCHER=claude-drafter\n'
    printf 'TIMEOUT=%s\n' "$TIMEOUT"
    printf 'TOOL=claude\n'
    printf 'CMD_JSON=%s\n' "$CMD_JSON"
} > "${OUTPUT_CANON}.meta"

json_tmp="${OUTPUT_CANON}.json.$$"
result_tmp="${OUTPUT_CANON}.extract.$$"
plan_tmp="${DESIGN_CANON}/plan.txt.tmp.$$"
summary_tmp="${DESIGN_CANON}/plan-summary.md.tmp.$$"
rm -f "$json_tmp" "$result_tmp" "$plan_tmp" "$summary_tmp"

DRAFTER_LAUNCHED=true
_claude_argv=(claude --model "$MODEL" --print --output-format json --add-dir "$REPO_ROOT" --allowedTools "Read,Glob,Grep,LS" --permission-mode plan)
if command -v timeout >/dev/null 2>&1; then
    if timeout "$TIMEOUT" "${_claude_argv[@]}" < "$PROMPT_CANON" > "$json_tmp" 2> "${OUTPUT_CANON}.stderr"; then
        exit_code=0
    else
        exit_code=$?
        [[ "$exit_code" -eq 124 ]] && status="TIMEOUT" || status="ERROR"
    fi
else
    if "${_claude_argv[@]}" < "$PROMPT_CANON" > "$json_tmp" 2> "${OUTPUT_CANON}.stderr"; then
        exit_code=0
    else
        exit_code=$?
        status="ERROR"
    fi
fi

if [[ "$exit_code" -eq 0 ]]; then
    _claude_json_reason=""
    if ! command -v jq >/dev/null 2>&1 || ! [[ -s "$json_tmp" ]] || ! jq -e . "$json_tmp" >/dev/null 2>&1; then
        _claude_json_reason="claude JSON envelope could not be parsed"
    elif jq -e '(.is_error // false) == true' "$json_tmp" >/dev/null 2>&1; then
        _claude_json_reason="claude JSON envelope reported is_error=true"
    elif ! jq -er 'if (.result | type) == "string" and (.result | length) > 0 then .result else empty end' "$json_tmp" > "$result_tmp" 2>/dev/null || [[ ! -s "$result_tmp" ]]; then
        _claude_json_reason="claude JSON envelope missing non-empty string result"
    fi
    if [[ -n "$_claude_json_reason" ]]; then
        printf '%s\n' "CLAUDE_JSON_RESULT_INVALID" > "${OUTPUT_CANON}.failure-diag"
        printf '%s\n' "$_claude_json_reason" >> "${OUTPUT_CANON}.stderr"
        write_status_file "ERROR" "false" 0 0 "false" "true" "CLAUDE_JSON_RESULT_INVALID"
        exit_code=99
        status="ERROR"
    fi
fi

if [[ "$exit_code" -eq 0 ]]; then
    if ! python3 - "$result_tmp" "$plan_tmp" "$summary_tmp" > "${OUTPUT_CANON}.parse" 2> "${OUTPUT_CANON}.failure-diag" <<'PY'
import re
import sys
from pathlib import Path

src = Path(sys.argv[1])
plan_tmp = Path(sys.argv[2])
summary_tmp = Path(sys.argv[3])
text = src.read_text(encoding='utf-8')
lines = text.splitlines()

def positions(marker):
    return [i for i, line in enumerate(lines) if line == marker]

pb = positions('LARCH_PLAN_BEGIN')
pe = positions('LARCH_PLAN_END')
sb = positions('LARCH_SUMMARY_BEGIN')
se = positions('LARCH_SUMMARY_END')
if len(pb) != 1 or len(pe) != 1:
    raise SystemExit('invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END')
if pb[0] >= pe[0]:
    raise SystemExit('invalid plan sentinels: reversed or empty plan envelope')
if (len(sb) == 0) != (len(se) == 0) or len(sb) > 1 or len(se) > 1:
    raise SystemExit('invalid summary sentinels: require zero or one balanced pair')
if sb and sb[0] >= se[0]:
    raise SystemExit('invalid summary sentinels: reversed or empty summary envelope')
if sb and (pb[0] < sb[0] < pe[0] or pb[0] < se[0] < pe[0]):
    raise SystemExit('invalid sentinels: nested summary inside plan envelope')
plan_lines = lines[pb[0] + 1:pe[0]]
if not plan_lines or not ''.join(plan_lines).strip():
    raise SystemExit('empty extracted plan body')
while plan_lines and plan_lines[-1] == '':
    plan_lines.pop()
if not plan_lines or not re.match(r'^diff_lines: [0-9][0-9]*$', plan_lines[-1]):
    raise SystemExit('missing final diff_lines trailer')
plan_body = '\n'.join(plan_lines) + '\n'
plan_tmp.write_text(plan_body, encoding='utf-8')
summary_written = False
if sb:
    summary_lines = lines[sb[0] + 1:se[0]]
    if ''.join(summary_lines).strip():
        summary_tmp.write_text('\n'.join(summary_lines).rstrip('\n') + '\n', encoding='utf-8')
        summary_written = True
    else:
        raise SystemExit('empty extracted summary body')
print(f'PLAN_LINES={len(plan_lines)}')
print(f'DIFF_LINES={plan_lines[-1].split(": ", 1)[1]}')
print(f'SUMMARY_WRITTEN={str(summary_written).lower()}')
PY
    then
        parse_reason=$(cat "${OUTPUT_CANON}.failure-diag" 2>/dev/null || printf '%s' delimiter-extraction-failed)
        printf 'DELIMITER_EXTRACTION_INVALID\n%s\n' "$parse_reason" > "${OUTPUT_CANON}.failure-diag"
        write_status_file "ERROR" "false" 0 0 "false" "true" "DELIMITER_EXTRACTION_INVALID"
        exit_code=99
        status="ERROR"
    else
        PLAN_LINES=0
        DIFF_LINES=0
        SUMMARY_WRITTEN=false
        while IFS= read -r _parse_line || [[ -n "$_parse_line" ]]; do
            case "$_parse_line" in
                PLAN_LINES=*) PLAN_LINES="${_parse_line#PLAN_LINES=}" ;;
                DIFF_LINES=*) DIFF_LINES="${_parse_line#DIFF_LINES=}" ;;
                SUMMARY_WRITTEN=*) SUMMARY_WRITTEN="${_parse_line#SUMMARY_WRITTEN=}" ;;
            esac
        done < "${OUTPUT_CANON}.parse"
        mv -f "$plan_tmp" "$DESIGN_CANON/plan.txt"
        if [[ "$SUMMARY_WRITTEN" == "true" ]]; then
            mv -f "$summary_tmp" "$DESIGN_CANON/plan-summary.md"
        else
            rm -f "$summary_tmp"
        fi
        write_status_file "OK" "true" "$PLAN_LINES" "$DIFF_LINES" "$SUMMARY_WRITTEN" "true" ""
        status="OK"
        read -r _cl_in _cl_out _cl_cr _cl_cc < <(jq -r '.usage // {} | "\(.input_tokens // 0) \(.output_tokens // 0) \(.cache_read_input_tokens // 0) \(.cache_creation_input_tokens // 0)"' "$json_tmp" 2>/dev/null || echo "0 0 0 0")
        if [[ "$_cl_in" =~ ^[0-9]+$ && "$_cl_out" =~ ^[0-9]+$ && "$_cl_cr" =~ ^[0-9]+$ && "$_cl_cc" =~ ^[0-9]+$ ]]; then
            _cl_total=$((_cl_in + _cl_out + _cl_cr + _cl_cc))
            "$SCRIPT_DIR/token-ledger.sh" record-vendor claude_sub \
                input="$_cl_in" output="$_cl_out" cache_read="$_cl_cr" \
                cache_create="$_cl_cc" total="$_cl_total" raw="$TOKEN_RAW" >/dev/null 2>&1 || true
        fi
    fi
fi

rm -f "$json_tmp" "$result_tmp" "$plan_tmp" "$summary_tmp" "${OUTPUT_CANON}.parse" "${OUTPUT_CANON}.json" "${OUTPUT_CANON}.result"
if [[ "$exit_code" -ne 0 ]]; then
    if [[ -s "${OUTPUT_CANON}.stderr" ]]; then
        write_failed_agent_stderr_tail "${OUTPUT_CANON}.stderr" "$OUTPUT_CANON" || true
    fi
    if [[ ! -s "${OUTPUT_CANON}.failure-diag" ]]; then
        write_failure_diag "$OUTPUT_CANON" --sink "${OUTPUT_CANON}.stderr" >/dev/null 2>&1 || true
    fi
else
    rm -f "${OUTPUT_CANON}.stderr-tail" "${OUTPUT_CANON}.failure-diag"
fi
printf '%s\n' "$exit_code" > "${OUTPUT_CANON}.done"

END_S=$(date +%s)
"$SCRIPT_DIR/timing-ledger.sh" record-vendor-task \
    --vendor claude \
    --task-kind "$TIMING_TASK_KIND" \
    --start-s "$START_S" \
    --end-s "$END_S" \
    --output "$OUTPUT_CANON" \
    --exit-code "$exit_code" \
    --status "$status" || true

emit_kv STATUS "$status"
emit_kv OUTPUT_FILE "$OUTPUT_CANON"
emit_kv ELAPSED "$((END_S - START_S))"
exit "$exit_code"
