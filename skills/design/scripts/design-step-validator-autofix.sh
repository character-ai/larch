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
hard_requested="${hard_requested:-false}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
design_classification="${design_classification:-}"
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
    --validator-target-file) _validator_target_file="$2"; shift 2 ;;
    --validate-log-file) VALIDATE_LOG_FILE="$2"; shift 2 ;;
    --validate-defect-count) VALIDATE_DEFECT_COUNT="$2"; shift 2 ;;
    --validate-unsafe-token-count) VALIDATE_UNSAFE_TOKEN_COUNT="$2"; shift 2 ;;
    --validate-skipped-count) VALIDATE_SKIPPED_COUNT="$2"; shift 2 ;;
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
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
case "${SITE:-}" in
  "design Step 5c"|"design Step 5c "*) _validator_target_file="${_validator_target_file:-$DESIGN_TMPDIR/composed-plan.md}" ;;
  *) _validator_target_file="${_validator_target_file:-$DESIGN_TMPDIR/plan.txt}" ;;
esac
[ -n "${_validator_target_file:-}" ] || _validator_target_file="$DESIGN_TMPDIR/plan.txt"
_autofix_site_key=$(printf '%s' "$SITE" | tr -cs 'A-Za-z0-9._-' '_' | sed 's/^_//; s/_$//')
_autofix_target_key=$(basename "${_validator_target_file:-target}" | tr -cs 'A-Za-z0-9._-' '_' | sed 's/^_//; s/_$//')
_autofix_evidence_key="${VALIDATE_DEFECT_COUNT:-unknown}-${VALIDATE_UNSAFE_TOKEN_COUNT:-unknown}-${VALIDATE_SKIPPED_COUNT:-unknown}"
if [ -n "${VALIDATE_LOG_FILE:-}" ] && [ -f "$VALIDATE_LOG_FILE" ] && [ ! -L "$VALIDATE_LOG_FILE" ]; then
  if command -v shasum >/dev/null 2>&1; then
    _autofix_evidence_hash=$(shasum -a 256 "$VALIDATE_LOG_FILE" | awk '{print $1}')
  else
    _autofix_evidence_hash=$(sha256sum "$VALIDATE_LOG_FILE" | awk '{print $1}')
  fi
  _autofix_evidence_key="${_autofix_evidence_key}-${_autofix_evidence_hash:-nohash}"
fi
_autofix_cycle_key=$(printf '%s-%s-%s' "${_autofix_site_key:-site}" "${_autofix_target_key:-target}" "$_autofix_evidence_key" | tr -cs 'A-Za-z0-9._-' '_' | sed 's/^_//; s/_$//')
_autofix_attempted="$DESIGN_TMPDIR/.plan-command-autofix-${_autofix_cycle_key:-site}.attempted"
if [ -e "$_autofix_attempted" ]; then
  _autofix_out="AUTOFIX_STATUS=skipped-cycle-cap"
  _autofix_rc=0
else
  : > "$_autofix_attempted"
  set +e
  _autofix_out=$("$CLAUDE_PLUGIN_ROOT/skills/design/scripts/auto-fix-plan-commands.sh" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --plan-file "$_validator_target_file" \
    --repo-root "$PWD" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --codex-available "${CODEX_AVAILABLE:-$CODEX_PRESENT}" \
    --cursor-available "${CURSOR_AVAILABLE:-$CURSOR_PRESENT}" \
    --site "$SITE")
  _autofix_rc=$?
  set -e
fi
printf '%s\n' "${_autofix_out:-}"
_autofix_status=$(printf '%s\n' "$_autofix_out" | awk -F= '$1=="AUTOFIX_STATUS"{print $2; exit}')
_autofix_fixed_by=$(printf '%s\n' "$_autofix_out" | awk -F= '$1=="FIXED_BY"{print $2; exit}')
_autofix_log_file=$(printf '%s\n' "$_autofix_out" | awk -F= '$1=="ORIGINAL_VALIDATE_LOG_FILE"{print $2; exit}')
case "${_autofix_status:-}" in
  ok|exhausted|unavailable) ;;
  skipped-cycle-cap) ;;
  *) _autofix_status=failed ;;
esac
if [ "${_autofix_rc:-0}" -ne 0 ]; then
  _autofix_status=failed
fi
[ -n "${_autofix_log_file:-}" ] || _autofix_log_file="$DESIGN_TMPDIR/validate-plan-commands.log"
