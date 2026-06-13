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
STARTING_ROUND=""
STARTING_ROUND_SEEN=false

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
    --starting-round)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
        exit 2
      fi
      STARTING_ROUND_SEEN=true
      STARTING_ROUND="${2:-}"
      shift 2
      ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ "$STARTING_ROUND_SEEN" = true ]; then
  case "$STARTING_ROUND" in
    ''|*[!0-9]*)
      printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
      exit 2
      ;;
  esac
  if [ "$((10#$STARTING_ROUND))" -le 0 ]; then
    printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
    exit 2
  fi
fi

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


design_bg_wait_marker_start() {
  local step="$1"
  _bg_wait_marker="$DESIGN_TMPDIR/.bg-wait-active"
  _bg_wait_tmp="${_bg_wait_marker}.tmp.$$"
  {
    printf 'PID=%s\n' "$$"
    printf 'CLAUDE_PID=%s\n' "${CLAUDE_PID:-}"
    printf 'START_EPOCH=%s\n' "$(date +%s)"
    printf 'STEP=%s\n' "$step"
    printf 'TIMEOUT_S=21600\n'
  } >"$_bg_wait_tmp" || return 1
  mv -f "$_bg_wait_tmp" "$_bg_wait_marker" || { rm -f "$_bg_wait_tmp" 2>/dev/null || true; return 1; }
  trap 'rm -f "${_bg_wait_marker:-}" "${_bg_wait_tmp:-}"' EXIT
  return 0
}
design_source_env_optional
if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' "/design wrapper: DESIGN_TMPDIR required" >&2
  exit 1
fi
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
# Marker step id: STEP=design-step3-review
design_bg_wait_marker_start design-step3-review || true
_plan_review_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate run-step3-review stdout capture; aborting plan review**" >&2
  exit 1
}
_loop_pid=""
_step3_review_monitor_was_enabled=0
case $- in *m*) _step3_review_monitor_was_enabled=1 ;; esac
_step3_review_monitor_enabled_by_wrapper=0

_step3_review_write_prelaunch_failure() {
  local _result_env="$DESIGN_TMPDIR/.step3-review-result.env"
  local _tmp=""
  rm -f "$_result_env" 2>/dev/null || true
  _tmp="$(mktemp "$DESIGN_TMPDIR/.step3-review-result.env.XXXXXX" 2>/dev/null || true)"
  if [[ -n "$_tmp" ]]; then
    if {
      printf '%s\n' 'STEP3_REVIEW_LOOP_STATUS=panel-failed'
      printf '%s\n' 'LOOP_STATUS=panel-failed'
      printf '%s\n' 'REASON=monitor-mode-unavailable'
      printf '%s\n' 'TALLY_PLAN_REVIEW_STATUS=panel-failed'
      printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
      printf '%s\n' 'STEP3_REVIEW_ROUND_NUM='
      printf '%s\n' 'ROUND_NUM='
      printf '%s\n' 'ROUNDS_COMPLETED=0'
      printf '%s\n' 'REVIEW_ROUND_COUNT=0'
    } >"$_tmp"; then
      mv "$_tmp" "$_result_env" 2>/dev/null || {
        rm -f "$_tmp" "$_result_env" 2>/dev/null || true
      }
    else
      rm -f "$_tmp" "$_result_env" 2>/dev/null || true
    fi
  fi
  printf '%s\n' 'STEP3_REVIEW_LOOP_STATUS=panel-failed'
  printf '%s\n' 'LOOP_STATUS=panel-failed'
  printf '%s\n' 'REASON=monitor-mode-unavailable'
  printf '%s\n' 'TALLY_PLAN_REVIEW_STATUS=panel-failed'
  printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
  printf '%s\n' 'ROUNDS_COMPLETED=0'
  printf '%s\n' 'REVIEW_ROUND_COUNT=0'
  exit 0
}

_step3_review_teardown_loop_group() {
  local _pid="${1:-}"
  [[ -n "$_pid" ]] || return 0
  kill -- -"$_pid" 2>/dev/null || true
}

_step3_review_cleanup() {
  local _rc=$?
  trap - EXIT
  if [[ -n "${_loop_pid:-}" ]]; then
    _step3_review_teardown_loop_group "$_loop_pid"
    wait "$_loop_pid" 2>/dev/null || true
  fi
  if [[ "${_step3_review_monitor_enabled_by_wrapper:-0}" -eq 1 ]]; then
    set +m 2>/dev/null || true
  fi
  exit "$_rc"
}

if [[ "$_step3_review_monitor_was_enabled" -eq 0 ]]; then
  set +e
  set -m 2>/dev/null
  _step3_review_set_m_rc=$?
  set -e
  case $- in
    *m*) _step3_review_monitor_enabled_by_wrapper=1 ;;
    *) _step3_review_monitor_enabled_by_wrapper=0 ;;
  esac
else
  _step3_review_set_m_rc=0
fi

case $- in
  *m*) : ;;
  *)
    printf '%s\n' "**⚠ Step 3: process-group isolation is unavailable (monitor-mode-unavailable); treating plan review as panel-failed before launch**"
    _step3_review_write_prelaunch_failure
    ;;
esac

trap _step3_review_cleanup EXIT
set +e
if [ -n "$STARTING_ROUND" ]; then
  "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/run-step3-review.sh" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --starting-round "$STARTING_ROUND" \
    >"$_plan_review_stdout_file" &
else
  "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/run-step3-review.sh" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    >"$_plan_review_stdout_file" &
fi
_loop_pid=$!
wait "$_loop_pid"
_plan_review_rc=$?
set -e
_step3_review_teardown_loop_group "$_loop_pid"
_loop_pid=""
trap - EXIT
if [[ "${_step3_review_monitor_enabled_by_wrapper:-0}" -eq 1 ]]; then
  set +m 2>/dev/null || true
fi
_step3_primary_regular=false
if [[ -f "$DESIGN_TMPDIR/.step3-review-result.env" && ! -L "$DESIGN_TMPDIR/.step3-review-result.env" ]]; then
  _step3_primary_regular=true
fi
_safe_step3_env="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-env.XXXXXX")" || {
  rm -f "$_plan_review_stdout_file"
  printf '%s\n' "**⚠ Step 3: could not allocate safe step3 review result env; aborting plan review**" >&2
  exit 1
}
set +e
"${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh" \
  --input "$DESIGN_TMPDIR/.step3-review-result.env" \
  --fallback-input "$_plan_review_stdout_file" \
  --allow LOOP_STATUS \
  --allow STEP3_REVIEW_LOOP_STATUS \
  --allow POSTPLAN_RC \
  --allow DEDUP_RC \
  --allow PLAN_REVIEW_CONTINUE_REASON \
  --allow FINAL_ROUND_NUM \
  --allow ACCEPTED_COUNT \
  --allow IMPORTANT_ACCEPTED_COUNT \
  --allow DEGRADED_PANEL \
  --allow ROUNDS_COMPLETED \
  --allow TALLY_PLAN_REVIEW_STATUS \
  --allow AGGREGATOR_STATUS \
  --allow VOTING_TALLY_FILE \
  --allow SCOPE_ANCHOR_FILE \
  --allow STEP3_REVIEW_CAP_REACHED \
  --allow STEP3_REVIEW_ROUND_NUM \
  --allow ROUND_NUM \
  --allow REVIEW_ROUND_COUNT \
  --output "$_safe_step3_env"
_rre_rc=$?
set -e
if [[ "${_rre_rc:-0}" -ne 0 ]]; then
  rm -f "$_plan_review_stdout_file" "$_safe_step3_env"
  printf '%s\n' "**⚠ Step 3: could not read step3 review result env; treating plan review as panel-failed**" >&2
  STEP3_REVIEW_LOOP_STATUS=panel-failed
  LOOP_STATUS=panel-failed
  export PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
  # shellcheck source=skills/design/scripts/lib-phase-driver.sh
  source "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/lib-phase-driver.sh"
  larch_quiet_init
  # shellcheck source=skills/design/scripts/review-design-step3-loop.sh
  source "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/review-design-step3-loop.sh"
  step3_record_report_evidence panel-failed
else
  # shellcheck source=/dev/null
  . "$_safe_step3_env"
fi
while IFS= read -r _line || [[ -n "$_line" ]]; do
  _key="${_line%%=*}"; _value="${_line#*=}"
  case "$_key" in
    STEP3_REVIEW_LOOP_STATUS|POSTPLAN_RC|DEDUP_RC|FINAL_ROUND_NUM)
      [[ -n "$_value" ]] && printf -v "$_key" '%s' "$_value"
      ;;
    WARN)
      if [[ "$_step3_primary_regular" == true ]]; then
        printf '%s\n' "WARN=$_value"
      fi
      ;;
  esac
done <"$_plan_review_stdout_file"
rm -f "$_plan_review_stdout_file" "$_safe_step3_env"
if [[ "${_plan_review_rc:-0}" -eq 2 ]]; then
  larch_err "**⚠ Step 3: run-step3-review.sh configuration error (exit 2); aborting plan review**"
  exit 1
fi
if [[ -n "${STEP3_REVIEW_LOOP_STATUS:-}" ]]; then
  if [[ ! "${STEP3_REVIEW_LOOP_STATUS}" =~ ^(complete|cap-hit|main-agent-vote-required|main-agent-apply-required|per-round-approval-required|postplan-operator-required|postplan-failed|panel-failed|tally-error|degraded-empty-collector)$ ]]; then
    larch_err "**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS after run-step3-review.sh; treating plan review as panel-failed**"
    STEP3_REVIEW_LOOP_STATUS=panel-failed
  fi
  case "${STEP3_REVIEW_LOOP_STATUS}" in
    cap-hit) LOOP_STATUS=cap-reached ;;
    complete|panel-failed|tally-error|degraded-empty-collector|main-agent-vote-required|postplan-failed) LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS}" ;;
    main-agent-apply-required|per-round-approval-required|postplan-operator-required) LOOP_STATUS=complete ;;
  esac
elif [[ -z "${LOOP_STATUS:-}" || ! "${LOOP_STATUS}" =~ ^(complete|cap-reached|zero-findings-degraded-panel|tally-error|degraded-empty-collector|panel-failed|main-agent-vote-required|main-agent-apply-required|per-round-approval-required|postplan-operator-required|postplan-failed)$ ]]; then
  larch_err "**⚠ Step 3: missing or invalid LOOP_STATUS after run-step3-review.sh; treating plan review as panel-failed**"
  LOOP_STATUS=panel-failed
fi
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
[[ -n "${STEP3_REVIEW_LOOP_STATUS:-}" ]] && printf 'STEP3_REVIEW_LOOP_STATUS=%s\n' "$STEP3_REVIEW_LOOP_STATUS"
[[ -n "${LOOP_STATUS:-}" ]] && printf 'LOOP_STATUS=%s\n' "$LOOP_STATUS"
[[ -n "${POSTPLAN_RC:-}" ]] && printf 'POSTPLAN_RC=%s\n' "$POSTPLAN_RC"
[[ -n "${DEDUP_RC:-}" ]] && printf 'DEDUP_RC=%s\n' "$DEDUP_RC"
[[ -n "${FINAL_ROUND_NUM:-}" ]] && printf 'FINAL_ROUND_NUM=%s\n' "$FINAL_ROUND_NUM"
[[ -n "${TALLY_PLAN_REVIEW_STATUS:-}" ]] && printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "$TALLY_PLAN_REVIEW_STATUS"
[[ -n "${SCOPE_ANCHOR_FILE:-}" ]] && printf 'SCOPE_ANCHOR_FILE=%s\n' "$SCOPE_ANCHOR_FILE"
[[ -n "${STEP3_REVIEW_ROUND_NUM:-}" ]] && printf 'STEP3_REVIEW_ROUND_NUM=%s\n' "$STEP3_REVIEW_ROUND_NUM"
[[ -n "${ROUND_NUM:-}" ]] && printf 'ROUND_NUM=%s\n' "$ROUND_NUM"
[[ -n "${REVIEW_ROUND_COUNT:-}" ]] && printf 'REVIEW_ROUND_COUNT=%s\n' "$REVIEW_ROUND_COUNT"
[[ -n "${ROUNDS_COMPLETED:-}" ]] && printf 'ROUNDS_COMPLETED=%s\n' "$ROUNDS_COMPLETED"
[[ -n "${ACCEPTED_COUNT:-}" ]] && printf 'ACCEPTED_COUNT=%s\n' "$ACCEPTED_COUNT"
[[ -n "${IMPORTANT_ACCEPTED_COUNT:-}" ]] && printf 'IMPORTANT_ACCEPTED_COUNT=%s\n' "$IMPORTANT_ACCEPTED_COUNT"
[[ -n "${STEP3_REVIEW_CAP_REACHED:-}" ]] && printf 'STEP3_REVIEW_CAP_REACHED=%s\n' "$STEP3_REVIEW_CAP_REACHED"
[[ -n "${AGGREGATOR_STATUS:-}" ]] && printf 'AGGREGATOR_STATUS=%s\n' "$AGGREGATOR_STATUS"
[[ -n "${VOTING_TALLY_FILE:-}" ]] && printf 'VOTING_TALLY_FILE=%s\n' "$VOTING_TALLY_FILE"
[[ -n "${DEGRADED_PANEL:-}" ]] && printf 'DEGRADED_PANEL=%s\n' "$DEGRADED_PANEL"
[[ -n "${PLAN_REVIEW_CONTINUE_REASON:-}" ]] && printf 'PLAN_REVIEW_CONTINUE_REASON=%s\n' "$PLAN_REVIEW_CONTINUE_REASON"
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == postplan-failed ]]; then
  printf '%s\n' 'SUMMARY_OUTCOME=failed-postplan'
  exit 1
fi
