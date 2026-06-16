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
OPERATOR_CANCEL=false
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
    --operator-cancel) OPERATOR_CANCEL=true; shift ;;
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
design_derive_binary_found() {
  if [ -z "${CODEX_BINARY_FOUND:-}" ]; then
    if command -v codex >/dev/null 2>&1; then CODEX_BINARY_FOUND=true; else CODEX_BINARY_FOUND=false; fi
  fi
  if [ -z "${CURSOR_BINARY_FOUND:-}" ]; then
    if command -v cursor >/dev/null 2>&1; then CURSOR_BINARY_FOUND=true; else CURSOR_BINARY_FOUND=false; fi
  fi
  export CODEX_BINARY_FOUND CURSOR_BINARY_FOUND
}
design_derive_binary_found
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}

validator_autofix_operator_cancel_audit() {
  local forced=${1:-}
  if [ "$forced" != forced ]; then
    case "${SUMMARY_OUTCOME:-}" in
      cancelled-*) ;;
      *) return 0 ;;
    esac
  fi
  design_require_plugin_root
  [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]] || return 0
  local sentinel="$DESIGN_TMPDIR/design-failure-operator-action.env"
  local chat="$DESIGN_TMPDIR/design-failure-operator-action-chat.md"
  local detail="$DESIGN_TMPDIR/design-failure-validator-cancel-audit.log"
  local outcome="${SUMMARY_OUTCOME:-operator-action}"
  [ -e "$sentinel" ] && return 0
  cat >"$sentinel" <<EOF2
DESIGN_FAILURE_OPERATOR_ACTION=true
REASON=validator-operator-cancel
OUTCOME=$outcome
EOF2
  {
    printf '**ℹ /design auto-report skipped:** operator action or cancellation outcome `%s`.\n\n' "$outcome"
    printf 'No public larch bug was filed. The skip was recorded in the run log.\n'
  } >"$chat"
  printf 'design validator autofix operator cancel: %s\n' "$outcome" >"$detail"
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design validator autofix" \
    --tool "design-step-validator-autofix.sh" \
    --exit-code 0 \
    --category Warnings \
    --output-file "$detail" \
    --redact >/dev/null 2>&1 || true
}

if [ "$OPERATOR_CANCEL" = true ]; then
  validator_autofix_operator_cancel_audit forced
  exit 0
fi

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
  _repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$CLAUDE_PLUGIN_ROOT")"
  set +e
  _autofix_out=$(env LARCH_QUIET_DISABLE=1 python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan auto-fix-commands \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --plan-file "$_validator_target_file" \
    --repo-root "$_repo_root" \
    --codex-binary-found "${CODEX_BINARY_FOUND:-}" \
    --cursor-binary-found "${CURSOR_BINARY_FOUND:-}" \
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

autofix_site_token() {
  case "${SITE:-}" in
    *"Step 5c"*) printf '%s\n' step5c ;;
    *"Gate B"*|*"Step 3.5"*) printf '%s\n' gate-b ;;
    *discussion-round2*) printf '%s\n' discussion-round2 ;;
    *"Step 2b"*) printf '%s\n' step2b ;;
    *) printf '%s\n' validator ;;
  esac
}

autofix_trigger_token() {
  case "${_autofix_status:-}" in
    exhausted|failed|unavailable|skipped-cycle-cap) printf '%s\n' "$_autofix_status" ;;
    *) printf '%s\n' failed ;;
  esac
}

validator_autofix_record_escalation() {
  case "${_autofix_status:-}" in
    exhausted|failed|unavailable|skipped-cycle-cap) ;;
    *) return 0 ;;
  esac
  design_require_plugin_root
  [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]] || return 0
  local helper site trigger args
  helper_cmd=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery)
  command -v python3 >/dev/null 2>&1 || return 0
  site=$(autofix_site_token)
  trigger=$(autofix_trigger_token)
  args=(
    record-escalation --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR"
    --site "$site" --trigger "$trigger"
    --step validator --phase validation --dispatcher design-step-validator-autofix
    --exit-code "${_autofix_rc:-unknown}"
  )
  case "${_autofix_log_file:-}" in
    "$DESIGN_TMPDIR"/*)
      if [ -f "$_autofix_log_file" ] && [ ! -L "$_autofix_log_file" ]; then
        args+=(--failure-detail-log "$_autofix_log_file")
      fi
      ;;
  esac
  set +e
  "${helper_cmd[@]}" "${args[@]}" \
    >"$DESIGN_TMPDIR/validator-autofix-record-escalation.stdout.log" \
    2>"$DESIGN_TMPDIR/validator-autofix-record-escalation.stderr.log"
  set -e
}

validator_autofix_record_escalation
validator_autofix_operator_cancel_audit
