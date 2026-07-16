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
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-}"
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
  _cpr_literal='${CLAUDE_PLUGIN_ROOT}'
  _cpr_cli_root="${CLAUDE_PLUGIN_ROOT:-}"
  case "${_cpr_cli_root}" in
    ""|"$_cpr_literal")
      _cpr_cli_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
      ;;
  esac
  python3 "${_cpr_cli_root}/python/cli.py" session require-plugin-root || exit $?
  export CLAUDE_PLUGIN_ROOT
}

design_source_env_optional() {
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_source_env_optional
design_require_plugin_root
mkdir -p "$DESIGN_TMPDIR/.completed"
case "${STEP3_REVIEW_LOOP_STATUS:-}" in
  postplan-failed)
    printf '%s\n' "⏩ 3.5: Gate B — aborted (STEP3_REVIEW_LOOP_STATUS=postplan-failed)"
    ;;
  main-agent-apply-required|per-round-approval-required|postplan-operator-required)
    : > "$DESIGN_TMPDIR/.completed/step-3"
    ;;
  '')
    case "${LOOP_STATUS:-}" in
      complete|zero-findings-degraded-panel|main-agent-vote-required) : > "$DESIGN_TMPDIR/.completed/step-3" ;;
      *) printf '%s\n' "⏩ 3.5: Gate B — skipped (STEP3_REVIEW_LOOP_STATUS=${STEP3_REVIEW_LOOP_STATUS:-unset}, LOOP_STATUS=${LOOP_STATUS:-unset})" ;;
    esac
    ;;
  *)
    printf '%s\n' "⏩ 3.5: Gate B — skipped (loop envelope ${STEP3_REVIEW_LOOP_STATUS})"
    ;;
esac
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 3.5 — gate B" || true
_approve_requested=false
if command -v jq >/dev/null 2>&1; then
  case "$(jq -r '.approve_requested // false' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null)" in
    true) _approve_requested=true ;;
  esac
elif grep -Eq '"approve_requested"[[:space:]]*:[[:space:]]*true([,}[:space:]]|$)' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null; then
  _approve_requested=true
fi
printf 'APPROVE_REQUESTED=%s\n' "$_approve_requested"
