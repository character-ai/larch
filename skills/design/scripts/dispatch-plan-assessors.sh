#!/usr/bin/env bash
# dispatch-plan-assessors.sh — Launch 3-model plan-quality assessor panel.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init
larch_quiet_append_done_trap
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"

ASSESSMENT_PATTERN='^[[:space:]]*\**[Aa][Ss][Ss][Ee][Ss][Ss][Mm][Ee][Nn][Tt][[:space:]]*[:=]'

usage() {
    larch_err "Usage: dispatch-plan-assessors.sh --design-tmpdir DIR --round-num N --plan-original PATH --plan-prev PATH --plan-current PATH --feature-file PATH --codex-present true|false --cursor-present true|false [--timeout SECS]"
}

DESIGN_TMPDIR=""
ROUND_NUM=""
PLAN_ORIGINAL=""
PLAN_PREV=""
PLAN_CURRENT=""
FEATURE_FILE=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
TIMEOUT="1860"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?}"; shift 2 ;;
        --plan-original) PLAN_ORIGINAL="${2:?}"; shift 2 ;;
        --plan-prev) PLAN_PREV="${2:?}"; shift 2 ;;
        --plan-current) PLAN_CURRENT="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-plan-assessors.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" ]] || { usage; exit 2; }
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
mkdir -p "$DESIGN_TMPDIR"
export DESIGN_TMPDIR
case "$ROUND_NUM" in
    ''|*[!0-9]*|0) larch_err "dispatch-plan-assessors.sh: --round-num must be a positive integer"; exit 2 ;;
esac
ROUND_NUM=$((10#$ROUND_NUM))

for f in "$PLAN_ORIGINAL" "$PLAN_PREV" "$PLAN_CURRENT" "$FEATURE_FILE"; do
    [[ -f "$f" ]] || { larch_err "dispatch-plan-assessors.sh: missing input file: $f"; exit 2; }
done
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "dispatch-plan-assessors.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "dispatch-plan-assessors.sh: --cursor-present must be true or false"; exit 2; }
larch_quiet_write_paired_pid_file

RENDER_SH="${LARCH_RENDER_ASSESSOR_PROMPT_SH:-$PLUGIN_ROOT/skills/shared/scripts/render-assessor-prompt.sh}"
prompt_file="$DESIGN_TMPDIR/assessor-prompt-round-${ROUND_NUM}.txt"
"$RENDER_SH" \
    --plan-original "$PLAN_ORIGINAL" \
    --plan-prev "$PLAN_PREV" \
    --plan-current "$PLAN_CURRENT" \
    --feature-file "$FEATURE_FILE" \
    --output "$prompt_file"

CLAUDE_PATH="$DESIGN_TMPDIR/claude-plan-assessor-round-${ROUND_NUM}.txt"
CODEX_PATH="$DESIGN_TMPDIR/codex-plan-assessor-round-${ROUND_NUM}.txt"
CURSOR_PATH="$DESIGN_TMPDIR/cursor-plan-assessor-round-${ROUND_NUM}.txt"

LAUNCH_CLAUDE="${LARCH_LAUNCH_CLAUDE_REVIEW_SH:-$PLUGIN_ROOT/scripts/launch-claude-review.sh}"
set +e
"$LAUNCH_CLAUDE" \
    --output "$CLAUDE_PATH" \
    --prompt-file "$prompt_file" \
    --mode description \
    --role assessor \
    --timeout "$TIMEOUT" \
    --timing-task-kind claude-plan-assessor \
    >/dev/null 2>"${CLAUDE_PATH}.launcher-stderr"
claude_rc=$?
set -e
[[ -f "${CLAUDE_PATH}.done" ]] || printf '%s\n' "$claude_rc" >"${CLAUDE_PATH}.done"

CLAUDE_STATUS=launched
[[ "$claude_rc" -eq 0 && -s "$CLAUDE_PATH" ]] || CLAUDE_STATUS=failed

manifest="$DESIGN_TMPDIR/plan-assessor-slots.ndjson"
{
    printf '{"slot":"plan-assessor","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$CODEX_PATH" "$prompt_file"
    printf '{"slot":"plan-assessor","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$CURSOR_PATH" "$prompt_file"
} >"$manifest"

WATERFALL_SH="${LARCH_DISPATCH_WITH_WATERFALL_SH:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"
unset LARCH_PAIRED_PID_FILE
set +e
waterfall_output=$("$WATERFALL_SH" \
    --slots-file "$manifest" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --mode description \
    --timeout "$TIMEOUT" \
    --feature-file "$FEATURE_FILE" \
    --require-result-pattern "$ASSESSMENT_PATTERN")
wf_rc=$?
set -e

dispatch_ok=true
all_outputs=""
all_tools=""
while IFS= read -r line || [[ -n "$line" ]]; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        ALL_OUTPUT_FILES) all_outputs="$value" ;;
        ALL_OUTPUT_TOOLS) all_tools="$value" ;;
        DISPATCH_OK) dispatch_ok="$value" ;;
        WARN) emit_kv WARN "$value" ;;
    esac
done <<<"$waterfall_output"

read -r -a outputs_arr <<< "$all_outputs"
read -r -a tools_arr <<< "$all_tools"
CODEX_PATH="${outputs_arr[0]:-$CODEX_PATH}"
CURSOR_PATH="${outputs_arr[1]:-$CURSOR_PATH}"
CODEX_TOOL="${tools_arr[0]:-codex}"
CURSOR_TOOL="${tools_arr[1]:-cursor}"

CODEX_STATUS=launched
CURSOR_STATUS=launched
[[ "$CODEX_TOOL" == "claude" ]] && CODEX_STATUS=fallback
[[ "$CURSOR_TOOL" == "claude" ]] && CURSOR_STATUS=fallback
[[ -s "$CODEX_PATH" ]] || CODEX_STATUS=failed
[[ -s "$CURSOR_PATH" ]] || CURSOR_STATUS=failed

degraded_warning=false
effective=0
for st in "$CLAUDE_STATUS" "$CODEX_STATUS" "$CURSOR_STATUS"; do
    [[ "$st" != "failed" ]] && effective=$((effective + 1))
done
if (( effective < 3 )); then degraded_warning=true; fi

[[ "$dispatch_ok" != "true" || "$wf_rc" -ne 0 ]] && dispatch_ok=false
[[ "$dispatch_ok" != "true" ]] && degraded_warning=true

emit_kv DISPATCH_OK "$dispatch_ok"
emit_kv CLAUDE_ASSESSOR_PATH "$CLAUDE_PATH"
emit_kv CODEX_ASSESSOR_PATH "$CODEX_PATH"
emit_kv CURSOR_ASSESSOR_PATH "$CURSOR_PATH"
emit_kv CLAUDE_ASSESSOR_STATUS "$CLAUDE_STATUS"
emit_kv CODEX_ASSESSOR_STATUS "$CODEX_STATUS"
emit_kv CURSOR_ASSESSOR_STATUS "$CURSOR_STATUS"
emit_kv DEGRADED_PANEL_WARNING "$degraded_warning"
exit 0
