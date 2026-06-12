#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
MODE=""
SITE=""
SUMMARY_OUTCOME="${SUMMARY_OUTCOME:-}"
SKIP_VALIDATE=""
PUBLIC_ARGV_WORDS=()

# Prompt-side values may be supplied only as environment variables by Claude Code.
# Default them before sourced session env overrides to preserve the old inline-fence no-set-u behavior.
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_TMPDIR="${SESSION_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
ISSUE_TITLE="${ISSUE_TITLE:-}"
HAS_CLARIFY_LABEL="${HAS_CLARIFY_LABEL:-false}"
REPO="${REPO:-}"
CODEX_PRESENT="${CODEX_PRESENT:-false}"
CURSOR_PRESENT="${CURSOR_PRESENT:-false}"
CODEX_AVAILABLE="${CODEX_AVAILABLE:-$CODEX_PRESENT}"
CURSOR_AVAILABLE="${CURSOR_AVAILABLE:-$CURSOR_PRESENT}"
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-false}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-false}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
VALIDATE_STATUS="${VALIDATE_STATUS:-}"
VALIDATE_DEFECT_COUNT="${VALIDATE_DEFECT_COUNT:-}"
VALIDATE_UNSAFE_TOKEN_COUNT="${VALIDATE_UNSAFE_TOKEN_COUNT:-}"
VALIDATE_SKIPPED_COUNT="${VALIDATE_SKIPPED_COUNT:-}"
VALIDATE_LOG_FILE="${VALIDATE_LOG_FILE:-}"
_validator_target_file="${_validator_target_file:-}"
PUBLISH_OK="${PUBLISH_OK:-}"
PLAN_WRITE_OK="${PLAN_WRITE_OK:-}"
STANDALONE_HEAVY_FAILED="${STANDALONE_HEAVY_FAILED:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --site) SITE="$2"; shift 2 ;;
    --snapshot-original) SNAPSHOT_ORIGINAL=true; shift ;;
    --outcome) SUMMARY_OUTCOME="$2"; shift 2 ;;
    --skip-validate) SKIP_VALIDATE=1; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

design_require_plugin_root() {
  _cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort" >&2
    exit 1
  fi
  if [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal ${_cpr_literal}; abort" >&2
    exit 1
  fi
  export CLAUDE_PLUGIN_ROOT
}

design_source_env_optional() {
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_source_env_optional
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 0 degraded: DESIGN_TMPDIR required after session rehydration" >&2
  exit 1
fi
if [ -f "$DESIGN_TMPDIR/source-env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DESIGN_TMPDIR/source-env.sh"
fi
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT
_gate_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-degraded-gate-stdout.XXXXXX")" || {
  printf '%s\n' "/design Step 0 degraded: could not allocate gate stdout capture" >&2
  exit 1
}
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent degraded-tools-gate --skill design \
  --codex-present "${CODEX_PRESENT:-false}" \
  --cursor-present "${CURSOR_PRESENT:-false}" \
  --codex-binary-found "${CODEX_BINARY_FOUND:-false}" \
  --cursor-binary-found "${CURSOR_BINARY_FOUND:-false}" \
  >"$_gate_stdout_file"
DEGRADED=false
BOTH_DOWN=false
BOTH_DOWN_SEEN=false
PRESENCE_INPUT_EMPTY=false
_in_explanation=false
while IFS= read -r _gate_line || [[ -n "$_gate_line" ]]; do
  case "$_gate_line" in
    DEGRADED_EXPLANATION_BEGIN) _in_explanation=true; printf '%s\n' "$_gate_line" ;;
    DEGRADED_EXPLANATION_END) _in_explanation=false; printf '%s\n' "$_gate_line" ;;
    DEGRADED=*) DEGRADED="${_gate_line#DEGRADED=}"; printf '%s\n' "$_gate_line" ;;
    BOTH_DOWN=*) BOTH_DOWN="${_gate_line#BOTH_DOWN=}"; BOTH_DOWN_SEEN=true; printf '%s\n' "$_gate_line" ;;
    PRESENCE_INPUT_EMPTY=*) PRESENCE_INPUT_EMPTY="${_gate_line#PRESENCE_INPUT_EMPTY=}"; printf '%s\n' "$_gate_line" ;;
    CODEX_STATE=*|CURSOR_STATE=*)
      printf '%s\n' "$_gate_line"
      ;;
    *)
      if [[ "$_in_explanation" == true ]]; then
        printf '%s\n' "$_gate_line"
      fi
      ;;
  esac
done <"$_gate_stdout_file"
rm -f "$_gate_stdout_file"
if [[ "${PRESENCE_INPUT_EMPTY:-}" == true ]]; then
  printf '%s\n' '- Step 0 degraded-tools gate: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)' >>"$DESIGN_TMPDIR/execution-issues.md"
fi
_design_interactive=true
if [[ "${LARCH_SKILL_NON_INTERACTIVE:-}" == true ]]; then
  _design_interactive=false
fi
STEP0_STATUS=ok
if [[ "${DEGRADED:-false}" == true ]]; then
  if [[ "$BOTH_DOWN_SEEN" == true && "${BOTH_DOWN:-}" == false ]]; then
    : >"$DESIGN_TMPDIR/.degraded-tools-gate-prompted"
    STEP0_STATUS=degraded-one-down
  elif [[ "$BOTH_DOWN_SEEN" == true && "${BOTH_DOWN:-}" == true && "$_design_interactive" != true ]]; then
    printf '%s\n' '- Step 0 degraded-tools gate: both external tools unavailable; proceeding degraded (non-interactive)' >>"$DESIGN_TMPDIR/execution-issues.md"
    : >"$DESIGN_TMPDIR/.degraded-tools-gate-prompted"
    STEP0_STATUS=degraded-both-down-auto
  else
    STEP0_STATUS=needs-degraded-decision
  fi
fi
printf 'STEP0_STATUS=%s\n' "$STEP0_STATUS"
printf 'DEGRADED=%s\n' "${DEGRADED:-false}"
printf 'BOTH_DOWN=%s\n' "${BOTH_DOWN:-}"
