#!/usr/bin/env bash
# launch-codex-drafter.sh — Launch a read-only Codex plan drafter subprocess.
# Wraps launch-codex-exec.sh with read-only sandbox and parses
# LARCH_PLAN_BEGIN/END + LARCH_SUMMARY_BEGIN/END sentinel output into
# plan.txt and plan-summary.md under $DESIGN_TMPDIR, emitting the same
# status KV contract as launch-claude-drafter.sh.

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
    larch_err "Usage: launch-codex-drafter.sh --prompt-file FILE --output-file FILE --timeout SECONDS --design-tmpdir DIR --repo-root DIR [--timing-task-kind KIND] [--baseline-porcelain FILE]"
}

PROMPT_FILE=""
OUTPUT_FILE=""
TIMEOUT=""
DESIGN_TMPDIR_ARG=""
REPO_ROOT_ARG=""
TIMING_TASK_KIND="codex-plan-draft"
BASELINE_PORCELAIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prompt-file)      PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --output-file)      OUTPUT_FILE="${2:?--output-file requires a value}"; shift 2 ;;
        --timeout)          TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --design-tmpdir)    DESIGN_TMPDIR_ARG="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --repo-root)        REPO_ROOT_ARG="${2:?--repo-root requires a value}"; shift 2 ;;
        --timing-task-kind) TIMING_TASK_KIND="${2:?--timing-task-kind requires a value}"; shift 2 ;;
        --baseline-porcelain) BASELINE_PORCELAIN="${2:?--baseline-porcelain requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "launch-codex-drafter.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$PROMPT_FILE" ]]      || { larch_err "launch-codex-drafter.sh: --prompt-file is required"; exit 2; }
[[ -n "$OUTPUT_FILE" ]]      || { larch_err "launch-codex-drafter.sh: --output-file is required"; exit 2; }
[[ -n "$TIMEOUT" ]]          || { larch_err "launch-codex-drafter.sh: --timeout is required"; exit 2; }
[[ -n "$DESIGN_TMPDIR_ARG" ]] || { larch_err "launch-codex-drafter.sh: --design-tmpdir is required"; exit 2; }
[[ -n "$REPO_ROOT_ARG" ]]    || { larch_err "launch-codex-drafter.sh: --repo-root is required"; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "launch-codex-drafter.sh: --timeout must be a positive integer"; exit 2 ;; esac
(( 10#$TIMEOUT <= 1800 )) || { larch_err "launch-codex-drafter.sh: --timeout must be <= 1800"; exit 2; }
case "$TIMING_TASK_KIND" in ""|--*) larch_err "launch-codex-drafter.sh: --timing-task-kind must be a non-empty, non-flag-like value"; exit 2 ;; esac

[[ -f "$PROMPT_FILE" ]]         || { larch_err "launch-codex-drafter.sh: --prompt-file not found: $PROMPT_FILE"; exit 2; }
[[ ! -L "$PROMPT_FILE" ]]       || { larch_err "launch-codex-drafter.sh: --prompt-file must not be a symlink"; exit 2; }
[[ -d "$DESIGN_TMPDIR_ARG" ]]   || { larch_err "launch-codex-drafter.sh: --design-tmpdir not found: $DESIGN_TMPDIR_ARG"; exit 2; }
[[ ! -L "$DESIGN_TMPDIR_ARG" ]] || { larch_err "launch-codex-drafter.sh: --design-tmpdir must not be a symlink"; exit 2; }
DESIGN_CANON="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
[[ -d "$REPO_ROOT_ARG" ]]       || { larch_err "launch-codex-drafter.sh: --repo-root not found: $REPO_ROOT_ARG"; exit 2; }
[[ ! -L "$REPO_ROOT_ARG" ]]     || { larch_err "launch-codex-drafter.sh: --repo-root must not be a symlink"; exit 2; }
REPO_ROOT="$(cd "$REPO_ROOT_ARG" && pwd -P)"

OUTPUT_DIR="$(cd "$(dirname "$OUTPUT_FILE")" && pwd -P)" || { larch_err "launch-codex-drafter.sh: invalid --output-file parent dir"; exit 2; }
[[ "$OUTPUT_DIR" == "$DESIGN_CANON" || "$OUTPUT_DIR" == "$DESIGN_CANON/"* ]] \
    || { larch_err "launch-codex-drafter.sh: --output-file outside design tmpdir"; exit 2; }
OUTPUT_CANON="$OUTPUT_DIR/$(basename "$OUTPUT_FILE")"

PROMPT_DIR="$(cd "$(dirname "$PROMPT_FILE")" && pwd -P)"
PROMPT_CANON="$PROMPT_DIR/$(basename "$PROMPT_FILE")"

write_status_file() {
    local status_value="$1" plan_written="$2" plan_lines="$3" diff_lines="$4" \
          summary_written="$5" launched="$6" reason="${7:-}"
    local tmp="${OUTPUT_CANON}.tmp.$$"
    {
        printf 'STATUS=%s\n' "$status_value"
        printf 'PLAN_WRITTEN=%s\n' "$plan_written"
        printf 'PLAN_LINES=%s\n' "$plan_lines"
        printf 'DIFF_LINES=%s\n' "$diff_lines"
        printf 'SUMMARY_WRITTEN=%s\n' "$summary_written"
        printf 'SCOUT_WRITTEN=%s\n' "${SCOUT_WRITTEN:-false}"
        [[ -z "${SCOUT_FAIL_REASON:-}" ]] || printf 'SCOUT_FAIL_REASON=%s\n' "$SCOUT_FAIL_REASON"
        printf 'DRAFTER_LAUNCHED=%s\n' "$launched"
        [[ -z "$reason" ]] || printf 'REASON=%s\n' "$reason"
    } > "$tmp"
    mv -f "$tmp" "$OUTPUT_CANON"
}

# shellcheck disable=SC2329,SC2317  # invoked by the EXIT trap
write_dirty_tree_sidecar() {
    [[ -n "${OUTPUT_CANON:-}" ]] || return 0
    local tmp="${OUTPUT_CANON}.dirty-tree.tmp.$$"
    local current_file="" diff_file="" dirty_status dirty_mode dirty_reason
    dirty_status="unknown"
    dirty_mode="prelaunch"
    dirty_reason="launcher-exited-before-drafter-launch"
    if [[ "${DRAFTER_LAUNCHED:-false}" == "true" ]]; then
        if [[ -n "${BASELINE_CANON:-}" && -f "${BASELINE_CANON:-}" && -r "${BASELINE_CANON:-}" ]]; then
            current_file=$(mktemp "${TMPDIR:-/tmp}/codex-drafter-status.XXXXXX") || current_file=""
            diff_file=$(mktemp "${TMPDIR:-/tmp}/codex-drafter-diff.XXXXXX") || diff_file=""
            if [[ -n "$current_file" && -n "$diff_file" ]] \
               && git -C "$REPO_ROOT" status --porcelain > "$current_file" 2>/dev/null; then
                if diff -u "$BASELINE_CANON" "$current_file" > "$diff_file" 2>/dev/null; then
                    dirty_status="clean"
                    dirty_mode="baseline-delta"
                    dirty_reason="codex-drafter-no-new-mutations"
                else
                    dirty_status="dirty"
                    dirty_mode="baseline-delta"
                    dirty_reason="codex-drafter-new-mutations"
                fi
            else
                dirty_status="unknown"
                dirty_mode="baseline-delta"
                dirty_reason="git-status-failed"
            fi
        else
            current_file=$(mktemp "${TMPDIR:-/tmp}/codex-drafter-status.XXXXXX") || current_file=""
            if [[ -n "$current_file" ]] \
               && git -C "$REPO_ROOT" status --porcelain > "$current_file" 2>/dev/null; then
                if [[ ! -s "$current_file" ]]; then
                    dirty_status="clean"
                    dirty_mode="absolute"
                    dirty_reason="codex-drafter-clean-working-tree"
                else
                    dirty_status="unknown"
                    dirty_mode="no-baseline"
                    dirty_reason="codex-drafter-no-usable-baseline"
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

rm -f "${OUTPUT_CANON}.stderr-tail" "${OUTPUT_CANON}.failure-diag" "${OUTPUT_CANON}.token-record"
write_status_file "ERROR" "false" 0 0 "false" "false" "prelaunch"

DRAFTER_LAUNCHED=false
trap 'write_dirty_tree_sidecar' EXIT

[[ "$PROMPT_CANON" == "$DESIGN_CANON/"* || "$PROMPT_CANON" == "$REPO_ROOT/"* ]] \
    || { larch_err "launch-codex-drafter.sh: --prompt-file outside allowed roots"; exit 2; }
BASELINE_CANON=""
if [[ -n "$BASELINE_PORCELAIN" ]]; then
    [[ -f "$BASELINE_PORCELAIN" ]] || { larch_err "launch-codex-drafter.sh: --baseline-porcelain not found"; exit 2; }
    BASELINE_CANON="$(cd "$(dirname "$BASELINE_PORCELAIN")" && pwd -P)/$(basename "$BASELINE_PORCELAIN")"
    [[ "$BASELINE_CANON" == "$DESIGN_CANON/"* ]] \
        || { larch_err "launch-codex-drafter.sh: --baseline-porcelain outside design tmpdir"; exit 2; }
fi

_codex_raw="${DESIGN_CANON}/step2b-codex-raw.$$.txt"
_launcher_stdout="${DESIGN_CANON}/step2b-codex-launcher-stdout.$$.txt"
_plan_tmp="${DESIGN_CANON}/plan.txt.tmp.$$"
_summary_tmp="${DESIGN_CANON}/plan-summary.md.tmp.$$"
_scout_candidate="${DESIGN_CANON}/scout-plan-manifest.json.candidate.$$"
_scout_filtered="${DESIGN_CANON}/scout-plan-manifest.json.filtered.$$"
_trusted_instructions="${DESIGN_CANON}/step2b-codex-trusted-instructions.$$.txt"
rm -f "$_codex_raw" "$_launcher_stdout" "$_plan_tmp" "$_summary_tmp" "$_scout_candidate" "$_scout_filtered" "$_trusted_instructions"

CODEX_DRAFTER_TRUSTED_INSTRUCTIONS=$(cat <<'EOF'
STRICT CONSTRAINTS — your role is read-only plan drafting for /design Step 2b. Do not create, edit, delete, or overwrite repository or tmpdir files. The launcher enforces this with --sandbox read-only.

OUTPUT CONTRACT — these requirements override any conflicting Codex user configuration or instructions:
- Emit exactly one whole-line LARCH_PLAN_BEGIN and one whole-line LARCH_PLAN_END with a non-empty plan body between them.
- Optionally emit zero or one balanced LARCH_SUMMARY_BEGIN/LARCH_SUMMARY_END pair before the plan envelope.
- The plan body must end with a whole-line diff_lines: <N> trailer.
- Optionally emit zero or one balanced LARCH_SCOUT_BEGIN/LARCH_SCOUT_END pair after LARCH_PLAN_END.
- If emitted, the scout block must contain only compact JSON with this shape: {"archetypes":[{"name":"slug","focus_area":"code-quality|risk-integration|correctness|architecture|security","weight":1,"rationale":"...","prompt_body":"..."}]}.
- Malformed scout output after the plan is ignored by the launcher and must not affect a valid plan.
- Scout sentinels before or inside the summary or plan are fatal format errors.
- Return only the sentinel-delimited response format; do not omit required sentinels.
EOF
)
printf '%s' "$CODEX_DRAFTER_TRUSTED_INSTRUCTIONS" > "$_trusted_instructions"

DRAFTER_LAUNCHED=true
_exec_wrapper_rc=0
set +e
python3 "$SCRIPT_DIR/../python/cli.py" agent launch-codex-exec \
    --output "$_codex_raw" \
    --timeout "$TIMEOUT" \
    --workdir "$REPO_ROOT" \
    --add-dir "$REPO_ROOT" \
    --sandbox read-only \
    --usage-label codex_plan_draft \
    --timing-task-kind "$TIMING_TASK_KIND" \
    --trusted-instructions-file "$_trusted_instructions" \
    --prompt-file "$PROMPT_CANON" \
    >"$_launcher_stdout" 2>"${OUTPUT_CANON}.stderr"
_exec_wrapper_rc=$?
set -e

LAUNCHER_EXIT=$(awk -F= '$1=="LAUNCHER_EXIT"{print $2; exit}' "$_launcher_stdout" 2>/dev/null || true)
[[ -n "$LAUNCHER_EXIT" ]] || LAUNCHER_EXIT=1
if [[ -s "${_codex_raw}.token-record" ]]; then
    if ! cp -p "${_codex_raw}.token-record" "${OUTPUT_CANON}.token-record"; then
        larch_err "launch-codex-drafter.sh: WARNING: failed to copy token record from ${_codex_raw}.token-record to ${OUTPUT_CANON}.token-record"
    fi
fi
rm -f "$_launcher_stdout"

if [[ "$LAUNCHER_EXIT" -ne 0 ]] || [[ "$_exec_wrapper_rc" -ne 0 ]]; then
    printf 'CODEX_EXEC_FAILED\n' > "${OUTPUT_CANON}.failure-diag"
    write_status_file "ERROR" "false" 0 0 "false" "true" "CODEX_EXEC_FAILED"
    _stderr_src=""
    if [[ -s "${_codex_raw}.sidecar" ]]; then
        _stderr_src="${_codex_raw}.sidecar"
    elif [[ -s "${OUTPUT_CANON}.stderr" ]]; then
        _stderr_src="${OUTPUT_CANON}.stderr"
    fi
    if [[ -n "$_stderr_src" ]]; then
        write_failed_agent_stderr_tail "$_stderr_src" "$OUTPUT_CANON" || true
    fi
    unset _stderr_src
    rm -f "$_codex_raw" "${_codex_raw}.sidecar" "$_plan_tmp" "$_summary_tmp" "$_scout_candidate" "$_scout_filtered" "$_trusted_instructions"
    printf '%s\n' "${LAUNCHER_EXIT:-1}" > "${OUTPUT_CANON}.done"
    emit_kv STATUS "ERROR"
    emit_kv OUTPUT_FILE "$OUTPUT_CANON"
    emit_kv TOKEN_RECORD "${OUTPUT_CANON}.token-record"
    exit "${LAUNCHER_EXIT:-1}"
fi

if [[ ! -s "$_codex_raw" ]]; then
    printf 'CODEX_EMPTY_OUTPUT\n' > "${OUTPUT_CANON}.failure-diag"
    write_status_file "ERROR" "false" 0 0 "false" "true" "CODEX_EMPTY_OUTPUT"
    rm -f "$_codex_raw" "$_plan_tmp" "$_summary_tmp" "$_scout_candidate" "$_scout_filtered" "$_trusted_instructions"
    printf '%s\n' "1" > "${OUTPUT_CANON}.done"
    emit_kv STATUS "ERROR"
    emit_kv OUTPUT_FILE "$OUTPUT_CANON"
    emit_kv TOKEN_RECORD "${OUTPUT_CANON}.token-record"
    exit 1
fi

if ! python3 "$SCRIPT_DIR/parse-drafter-output.py" "$_codex_raw" "$_plan_tmp" "$_summary_tmp" "$_scout_candidate" \
        > "${OUTPUT_CANON}.parse" 2> "${OUTPUT_CANON}.failure-diag"
then
    _parse_reason=$(cat "${OUTPUT_CANON}.failure-diag" 2>/dev/null || printf '%s' delimiter-extraction-failed)
    printf 'DELIMITER_EXTRACTION_INVALID\n%s\n' "$_parse_reason" > "${OUTPUT_CANON}.failure-diag"
    write_status_file "ERROR" "false" 0 0 "false" "true" "DELIMITER_EXTRACTION_INVALID"
    rm -f "$_codex_raw" "$_plan_tmp" "$_summary_tmp" "$_scout_candidate" "$_scout_filtered" "$_trusted_instructions" "${OUTPUT_CANON}.parse"
    printf '%s\n' "99" > "${OUTPUT_CANON}.done"
    emit_kv STATUS "ERROR"
    emit_kv OUTPUT_FILE "$OUTPUT_CANON"
    emit_kv TOKEN_RECORD "${OUTPUT_CANON}.token-record"
    exit 99
fi

PLAN_LINES=0
DIFF_LINES=0
SUMMARY_WRITTEN=false
SCOUT_CANDIDATE_WRITTEN=false
SCOUT_FAIL_REASON=""
while IFS= read -r _parse_line || [[ -n "$_parse_line" ]]; do
    case "$_parse_line" in
        PLAN_LINES=*)   PLAN_LINES="${_parse_line#PLAN_LINES=}" ;;
        DIFF_LINES=*)   DIFF_LINES="${_parse_line#DIFF_LINES=}" ;;
        SUMMARY_WRITTEN=*) SUMMARY_WRITTEN="${_parse_line#SUMMARY_WRITTEN=}" ;;
        SCOUT_CANDIDATE_WRITTEN=*) SCOUT_CANDIDATE_WRITTEN="${_parse_line#SCOUT_CANDIDATE_WRITTEN=}" ;;
        SCOUT_FAIL_REASON=*) SCOUT_FAIL_REASON="${_parse_line#SCOUT_FAIL_REASON=}" ;;
    esac
done < "${OUTPUT_CANON}.parse"

SCOUT_WRITTEN=false
if [[ "$SCOUT_CANDIDATE_WRITTEN" == "true" && -s "$_scout_candidate" ]]; then
    _filter_out="$("$PLUGIN_ROOT/skills/design/scripts/scout-plan-archetypes-wrapper.sh" --filter-manifest "$_scout_candidate" "$_scout_filtered" --max-archetypes 3 2>/dev/null || true)"
    _filter_status=$(printf '%s\n' "$_filter_out" | awk -F= '$1=="SCOUT_STATUS"{print $2; exit}')
    if [[ -s "$_scout_filtered" && "$_filter_status" != "parse-failed" ]] && jq -e '.archetypes | type == "array"' "$_scout_filtered" >/dev/null 2>&1; then
        mv -f "$_scout_filtered" "$DESIGN_CANON/scout-plan-manifest.json"
        SCOUT_WRITTEN=true
        SCOUT_FAIL_REASON=""
    else
        SCOUT_FAIL_REASON="filter_failed"
        rm -f "$_scout_filtered" "$DESIGN_CANON/scout-plan-manifest.json"
    fi
fi

mv -f "$_plan_tmp" "$DESIGN_CANON/plan.txt"
if [[ "$SUMMARY_WRITTEN" == "true" ]]; then
    mv -f "$_summary_tmp" "$DESIGN_CANON/plan-summary.md"
else
    rm -f "$_summary_tmp"
fi

rm -f "$_codex_raw" "$_trusted_instructions" "$_scout_candidate" "$_scout_filtered" "${OUTPUT_CANON}.parse" "${OUTPUT_CANON}.stderr" "${OUTPUT_CANON}.stderr-tail"
write_status_file "OK" "true" "$PLAN_LINES" "$DIFF_LINES" "$SUMMARY_WRITTEN" "true" ""
printf '%s\n' "0" > "${OUTPUT_CANON}.done"

emit_kv STATUS "OK"
emit_kv OUTPUT_FILE "$OUTPUT_CANON"
emit_kv TOKEN_RECORD "${OUTPUT_CANON}.token-record"
emit_kv SCOUT_WRITTEN "$SCOUT_WRITTEN"
[[ -z "$SCOUT_FAIL_REASON" ]] || emit_kv SCOUT_FAIL_REASON "$SCOUT_FAIL_REASON"
exit 0
