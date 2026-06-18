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
STARTING_ROUND=""
STARTING_ROUND_SEEN=false
RESUME_PHASE=""
RESUME_PHASE_SEEN=false
RESUME_FINDINGS_FILE=""
RESUME_FINDINGS_FILE_SEEN=false
POSTPLAN_OPERATOR_CONTINUE=false
READ_RESULT_ENV=false

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
    --phase)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --phase requires a value' >&2
        exit 2
      fi
      RESUME_PHASE_SEEN=true
      RESUME_PHASE="${2:-}"
      shift 2
      ;;
    --findings-file)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --findings-file requires a value' >&2
        exit 2
      fi
      RESUME_FINDINGS_FILE_SEEN=true
      RESUME_FINDINGS_FILE="${2:-}"
      shift 2
      ;;
    --postplan-operator-continue) POSTPLAN_OPERATOR_CONTINUE=true; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --read-result-env) READ_RESULT_ENV=true; shift ;;
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

if [ "$RESUME_PHASE_SEEN" = true ] && [ -z "$RESUME_PHASE" ]; then
  printf '%s\n' 'design-step3-review.sh: --phase requires a value' >&2
  exit 2
fi

if [ "$RESUME_FINDINGS_FILE_SEEN" = true ] && [ -z "$RESUME_FINDINGS_FILE" ]; then
  printf '%s\n' 'design-step3-review.sh: --findings-file requires a value' >&2
  exit 2
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
larch_err() { printf '%s\n' "$*" >&2; }

STEP3_REVIEW_HAS_RESUME_STATE=false
if [ "$RESUME_PHASE_SEEN" = true ] || [ "$RESUME_FINDINGS_FILE_SEEN" = true ] || [ "${POSTPLAN_OPERATOR_CONTINUE:-false}" = true ]; then
  STEP3_REVIEW_HAS_RESUME_STATE=true
fi

step3_review_usage_error() {
  printf '%s\n' "design-step3-review.sh: $*" >&2
  exit 2
}

step3_review_read_round_count() {
  local _count_file="$DESIGN_TMPDIR/review-round-count.txt" _raw=""
  if [ -s "$_count_file" ]; then
    _raw="$(tr -d '[:space:]' <"$_count_file" 2>/dev/null || true)"
    case "$_raw" in
      ''|*[!0-9]*) printf '0\n' ;;
      *) printf '%s\n' "$((10#$_raw))" ;;
    esac
  else
    printf '0\n'
  fi
}

step3_review_canonical_file() {
  local _path="$1" _dir _base
  _dir="$(dirname "$_path")"
  _base="$(basename "$_path")"
  (cd "$_dir" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$_base") || return 1
}

step3_review_validate_resume_state() {
  local _last_count _start_dec _canon_findings
  [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ] || return 0
  [ "$STARTING_ROUND_SEEN" = true ] || step3_review_usage_error 'resume-state flags require --starting-round'
  case "${RESUME_PHASE:-}" in
    ''|awaiting-apply|awaiting-revise|awaiting-post-apply|awaiting-postplan-operator|awaiting-continuation) ;;
    awaiting-vote) step3_review_usage_error '--phase awaiting-vote is internal and cannot be used as a resume phase' ;;
    *) step3_review_usage_error "invalid --phase: ${RESUME_PHASE}" ;;
  esac
  _last_count="$(step3_review_read_round_count)"
  _start_dec=$((10#$STARTING_ROUND))
  if [ "$_start_dec" -gt "$((_last_count + 1))" ]; then
    step3_review_usage_error "--starting-round cannot exceed last consumed review round + 1 (got: $STARTING_ROUND, last consumed: $_last_count)"
  fi
  if [ -n "${RESUME_FINDINGS_FILE:-}" ]; then
    case "$RESUME_FINDINGS_FILE" in
      /*) ;;
      *) step3_review_usage_error '--findings-file must be an absolute path' ;;
    esac
    case "$RESUME_FINDINGS_FILE" in
      *$'\n'*|*$'\r'*) step3_review_usage_error '--findings-file must not contain newline or carriage return' ;;
    esac
    [ ! -L "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must not be a symlink'
    [ -f "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must be a regular file'
    [ -r "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must be readable'
    _canon_findings="$(step3_review_canonical_file "$RESUME_FINDINGS_FILE")" || step3_review_usage_error '--findings-file parent cannot be resolved'
    case "$_canon_findings" in
      "$DESIGN_TMPDIR"/*) RESUME_FINDINGS_FILE="$_canon_findings" ;;
      *) step3_review_usage_error '--findings-file must resolve under DESIGN_TMPDIR' ;;
    esac
  fi
}

step3_review_write_resume_state() {
  local _phase_file _phase_tmp _approval_env _approval_tmp _continue_file _continue_tmp
  [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ] || return 0
  if [ -n "${RESUME_PHASE:-}" ]; then
    _phase_file="$DESIGN_TMPDIR/.step3-round-${STARTING_ROUND}.phase"
    _phase_tmp="${_phase_file}.tmp.$$"
    printf '%s\n' "$RESUME_PHASE" >"$_phase_tmp"
    mv "$_phase_tmp" "$_phase_file"
  fi
  if [ -n "${RESUME_FINDINGS_FILE:-}" ]; then
    _approval_env="$DESIGN_TMPDIR/.gate-b-per-round-approval-round-${STARTING_ROUND}.env"
    _approval_tmp="${_approval_env}.tmp.$$"
    printf 'FINDINGS_FILE=%s\n' "$RESUME_FINDINGS_FILE" >"$_approval_tmp"
    mv "$_approval_tmp" "$_approval_env"
  fi
  if [ "${POSTPLAN_OPERATOR_CONTINUE:-false}" = true ]; then
    _continue_file="$DESIGN_TMPDIR/.postplan-operator-continue-${STARTING_ROUND}"
    _continue_tmp="${_continue_file}.tmp.$$"
    : >"$_continue_tmp"
    mv "$_continue_tmp" "$_continue_file"
  fi
}
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/lib-quiet.sh" ]; then
  # shellcheck source=scripts/lib-quiet.sh
  source "${CLAUDE_PLUGIN_ROOT}/scripts/lib-quiet.sh" || true
fi
if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' "/design wrapper: DESIGN_TMPDIR required" >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
fi
# #4431 Fix C: hook-safe result-env read. When the immediate-background poll guard
# blocks a direct Read of .step3-review-result.env (e.g. a <task-notification> that
# arrives in the same turn as the launch ack), the orchestrator re-invokes this
# wrapper with --read-result-env to recover STEP3_REVIEW_LOOP_STATUS through the
# wrapper-routed path the guard allows. Pure read: no marker, no review dispatch.
if [ "$READ_RESULT_ENV" = true ]; then
  _rre_file="$DESIGN_TMPDIR/.step3-review-result.env"
  _rre_review_loop_status=""
  _rre_loop_status=""
  _rre_rounds_completed=""
  _rre_final_round_num=""
  _rre_accepted_count=""
  if [ -f "$_rre_file" ] && [ ! -L "$_rre_file" ]; then
    while IFS= read -r _rre_line || [ -n "$_rre_line" ]; do
      case "$_rre_line" in
        STEP3_REVIEW_LOOP_STATUS=*) _rre_review_loop_status="${_rre_line#*=}" ;;
        LOOP_STATUS=*) _rre_loop_status="${_rre_line#*=}" ;;
        ROUNDS_COMPLETED=*) _rre_rounds_completed="${_rre_line#*=}" ;;
        FINAL_ROUND_NUM=*) _rre_final_round_num="${_rre_line#*=}" ;;
        ACCEPTED_COUNT=*) _rre_accepted_count="${_rre_line#*=}" ;;
      esac
    done <"$_rre_file"
    printf 'READ_RESULT_ENV_STATUS=ok\n'
  else
    printf 'READ_RESULT_ENV_STATUS=missing\n'
  fi
  printf 'STEP3_REVIEW_LOOP_STATUS=%s\n' "$_rre_review_loop_status"
  printf 'LOOP_STATUS=%s\n' "$_rre_loop_status"
  printf 'ROUNDS_COMPLETED=%s\n' "$_rre_rounds_completed"
  printf 'FINAL_ROUND_NUM=%s\n' "$_rre_final_round_num"
  printf 'ACCEPTED_COUNT=%s\n' "$_rre_accepted_count"
  exit 0
fi
step3_review_validate_resume_state
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = false ]; then
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
else
  step3_review_write_resume_state
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
fi
# Marker step id: STEP=design-step3-review
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = false ]; then
  rm -f "$DESIGN_TMPDIR/.step3-review-result.env" "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
else
  rm -f "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
fi
rm -f "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
design_bg_wait_marker_start design-step3-review || true
_plan_review_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate plan-review stdout capture; aborting plan review**" >&2
  exit 1
}
_loop_pid=""
_step3_review_monitor_was_enabled=0
case $- in *m*) _step3_review_monitor_was_enabled=1 ;; esac
_step3_review_monitor_enabled_by_wrapper=0

_step3_review_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

_step3_review_write_prelaunch_failure() {
  local _status="${1:-panel-init-failed}"
  local _reason="${2:-prelaunch-failure}"
  _status="${_status:-panel-init-failed}"
  _reason="${_reason:-prelaunch-failure}"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review prelaunch-failure \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --reason "$_reason"
}

_step3_review_stage_panel_init_failed() {
  :
}

# #4688 terminal-sentinel contract: the bash zero-coverage fallback that writes
# .step3-review-result.env directly (not via python cli.py plan-review run) must
# also write the hook-release sentinel pair, or the EXIT trap's current-pass
# guard never fires and the poll guard waits out the dead-process race.
_step3_review_write_terminal_sentinels() {
  mkdir -p "$DESIGN_TMPDIR/.completed" 2>/dev/null || return 0
  rm -f "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
  : >"$DESIGN_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
  : >"$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
}

_step3_review_write_result_env() {
  local _status="${1:-panel-init-failed}"
  local _reason="${2:-prelaunch-failure}"
  local _rounds="${3:-0}"
  local _result_env="$DESIGN_TMPDIR/.step3-review-result.env"
  local _tmp=""
  rm -f "$_result_env" 2>/dev/null || true
  _tmp="$(mktemp "$DESIGN_TMPDIR/.step3-review-result.env.XXXXXX" 2>/dev/null || true)"
  if [[ -n "$_tmp" ]]; then
    if {
      printf 'STEP3_REVIEW_LOOP_STATUS=%s\n' "$_status"
      printf 'LOOP_STATUS=%s\n' "$_status"
      printf 'REASON=%s\n' "$_reason"
      printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' "$_status"
      printf '%s\n' 'STEP3_REVIEW_CAP_REACHED=false'
      printf '%s\n' 'STEP3_REVIEW_ROUND_NUM='
      printf '%s\n' 'ROUND_NUM='
      printf 'ROUNDS_COMPLETED=%s\n' "$_rounds"
      printf 'REVIEW_ROUND_COUNT=%s\n' "$_rounds"
    } >"$_tmp"; then
      mv "$_tmp" "$_result_env" 2>/dev/null || {
        rm -f "$_tmp" "$_result_env" 2>/dev/null || true
      }
      if [[ -f "$_result_env" && ! -L "$_result_env" && -r "$_result_env" ]]; then
        _step3_review_write_terminal_sentinels
      fi
    else
      rm -f "$_tmp" "$_result_env" 2>/dev/null || true
    fi
  fi
}

_step3_review_zero_round_coverage_missing() {
  local _rounds_dec="${1:-0}"
  local _r1="$DESIGN_TMPDIR/plan-review/round-1"
  if [[ "$_rounds_dec" -eq 0 ]]; then
    return 0
  fi
  [[ -d "$_r1" ]] || return 0
  [[ -z "$(find "$_r1" -mindepth 1 -maxdepth 1 -type f -print -quit 2>/dev/null)" ]] && return 0
  return 1
}

# #4489: Guarantee the Step 3 completion sentinel on every terminal exit of this
# background entrypoint. hook-bg-poll-guard.sh gates on .completed/step-3-terminal
# and releases a live design-step3-review marker as soon as the current wrapper
# pass has persisted .step3-review-result.env. The wrapper clears stale terminal
# sentinels before marker start; this trap may recreate step-3-terminal only when
# the loop wrote the current-pass persist sidecar.
# Writes ONLY step-3, never step-3.5: step-3.5 is a deferred Gate C / pause-resume
# gate (design_pause.py step resolution, the Gate B post-apply idempotency guard,
# design-step3b-entry.sh). Creating it here would skip Gate B on apply-pending
# exits (main-agent-apply-required, per-round-approval-required). Idempotent and
# best-effort: only creates a missing sentinel and never alters $?.
_step3_review_should_guarantee_step3() {
  if [ -e "$DESIGN_TMPDIR/.completed/step-3" ]; then
    return 0
  fi
  if [[ ! -f "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" || -L "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" || ! -r "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" ]]; then
    return 1
  fi
  if [[ ! -f "$DESIGN_TMPDIR/.step3-review-result.env" || -L "$DESIGN_TMPDIR/.step3-review-result.env" || ! -r "$DESIGN_TMPDIR/.step3-review-result.env" ]]; then
    return 1
  fi
  local _status=""
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    case "$_line" in
      STEP3_REVIEW_LOOP_STATUS=*) _status="${_line#STEP3_REVIEW_LOOP_STATUS=}" ;;
    esac
  done <"$DESIGN_TMPDIR/.step3-review-result.env"
  case "$_status" in
    complete|cap-hit|panel-failed|panel-init-failed|tally-error|degraded-empty-collector|postplan-failed)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

_step3_review_guarantee_completed_sentinels() {
  [ -n "${DESIGN_TMPDIR:-}" ] && [ -d "${DESIGN_TMPDIR:-}" ] || return 0
  mkdir -p "$DESIGN_TMPDIR/.completed" 2>/dev/null || return 0
  if _step3_review_should_guarantee_step3; then
    [ -e "$DESIGN_TMPDIR/.completed/step-3" ] || : >"$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
  fi
  if [ -f "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" ] && [ ! -L "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" ] && [ -r "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" ]; then
    [ -e "$DESIGN_TMPDIR/.completed/step-3-terminal" ] || : >"$DESIGN_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
  fi
  return 0
}

_step3_review_teardown_loop_group() {
  local _pid="${1:-}"
  [[ -n "$_pid" ]] || return 0
  kill -- -"$_pid" 2>/dev/null || true
}

_step3_review_kill_tmpdir_processes() {
  local _cli=""
  [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]] || return 0
  [[ -n "${DESIGN_TMPDIR:-}" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  _cli="${CLAUDE_PLUGIN_ROOT}/python/cli.py"
  [[ -f "$_cli" ]] || return 0
  python3 "$_cli" session kill-background-processes --design-tmpdir "$DESIGN_TMPDIR" >/dev/null 2>&1 || true
}

_step3_review_cleanup() {
  local _rc=$?
  trap - EXIT
  _step3_review_guarantee_completed_sentinels  # #4489: sentinel before exit
  if [[ -n "${_loop_pid:-}" ]]; then
    _step3_review_teardown_loop_group "$_loop_pid"
    _step3_review_kill_tmpdir_processes
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
    printf '%s\n' "**⚠ Step 3: process-group isolation is unavailable (monitor-mode-unavailable); treating plan review as panel-init-failed before launch**" >&2
    _step3_review_write_prelaunch_failure panel-init-failed monitor-mode-unavailable
    _step3_review_stage_panel_init_failed monitor-mode-unavailable
    printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
    exit 1
    ;;
esac

if ! python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" scope-anchor validate \
  --mode design \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --path "$DESIGN_TMPDIR/plan-review-scope-anchor.txt" >/dev/null; then
  larch_err "**⚠ Step 3: plan-review-scope-anchor.txt is missing, empty, invalid, or outside DESIGN_TMPDIR; treating plan review as panel-init-failed before launch**"
  _step3_review_write_prelaunch_failure panel-init-failed scope-anchor-missing
  _step3_review_stage_panel_init_failed scope-anchor-missing
  printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
  exit 1
fi

trap _step3_review_cleanup EXIT
set +e
if [ -n "$STARTING_ROUND" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --starting-round "$STARTING_ROUND" \
    >"$_plan_review_stdout_file" &
else
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    >"$_plan_review_stdout_file" &
fi
_loop_pid=$!
wait "$_loop_pid"
_plan_review_rc=$?
set -e
_step3_review_teardown_loop_group "$_loop_pid"
_step3_review_kill_tmpdir_processes
_loop_pid=""
# #4489 / #4724: loop teardown is done; from here every terminal exit (config-error,
# postplan-failed, panel-init-failed, or the normal complete/cap-hit/main-agent
# fall-through) must leave .completed/step-3 in place. The hook-release sentinel
# .completed/step-3-terminal is written only after the current wrapper pass
# persists the result envelope. Replace the loop-cleanup trap with the guarantee
# trap in a single atomic assignment: bash overwrites the active EXIT handler in
# one step, so there is no window where no EXIT trap is registered. The earlier
# two-step `trap - EXIT` removal followed by a re-arm left a gap in which a crash
# or signal could skip the completion sentinel (#4724).
trap '_step3_review_guarantee_completed_sentinels' EXIT
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
_step3_read_result_env() {
  local _input="$1"
  local _output="$2"
  shift 2
  "${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh" \
    --input "$_input" \
    "$@" \
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
    --output "$_output"
}
set +e
_step3_read_result_env \
  "$DESIGN_TMPDIR/.step3-review-result.env" \
  "$_safe_step3_env" \
  --fallback-input "$_plan_review_stdout_file"
_rre_rc=$?
if [[ "${_rre_rc:-0}" -ne 0 ]]; then
  _safe_step3_stdout_env="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout-env.XXXXXX")" || _safe_step3_stdout_env=""
  if [[ -n "$_safe_step3_stdout_env" ]]; then
    _step3_read_result_env "$_plan_review_stdout_file" "$_safe_step3_stdout_env"
    _rre_stdout_rc=$?
    if [[ "${_rre_stdout_rc:-0}" -eq 0 ]]; then
      mv -f "$_safe_step3_stdout_env" "$_safe_step3_env"
      _rre_rc=0
    else
      rm -f "$_safe_step3_stdout_env"
    fi
  fi
fi
set -e
if [[ "${_rre_rc:-0}" -eq 0 ]]; then
  # shellcheck source=/dev/null
  . "$_safe_step3_env"
else
  rm -f "$_safe_step3_env"
  printf '%s\n' "**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**" >&2
fi
while IFS= read -r _line || [[ -n "$_line" ]]; do
  _key="${_line%%=*}"; _value="${_line#*=}"
  case "$_key" in
    LOOP_STATUS|STEP3_REVIEW_LOOP_STATUS|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|TALLY_PLAN_REVIEW_STATUS|AGGREGATOR_STATUS|VOTING_TALLY_FILE|SCOPE_ANCHOR_FILE|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|REVIEW_ROUND_COUNT)
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
  larch_err "**⚠ Step 3: plan-review run configuration error (exit 2); aborting plan review**"
  exit 1
fi
if [[ -z "${STEP3_REVIEW_LOOP_STATUS:-}" ]]; then
  case "${LOOP_STATUS:-}" in
    complete) STEP3_REVIEW_LOOP_STATUS=complete ;;
    cap-reached) STEP3_REVIEW_LOOP_STATUS=cap-hit ;;
    main-agent-vote-required) STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required ;;
    main-agent-apply-required) STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required ;;
    per-round-approval-required) STEP3_REVIEW_LOOP_STATUS=per-round-approval-required ;;
    postplan-operator-required) STEP3_REVIEW_LOOP_STATUS=postplan-operator-required ;;
    postplan-failed) STEP3_REVIEW_LOOP_STATUS=postplan-failed ;;
    panel-failed) STEP3_REVIEW_LOOP_STATUS=panel-failed ;;
    panel-init-failed) STEP3_REVIEW_LOOP_STATUS=panel-init-failed ;;
    tally-error) STEP3_REVIEW_LOOP_STATUS=tally-error ;;
    degraded-empty-collector) STEP3_REVIEW_LOOP_STATUS=degraded-empty-collector ;;
    zero-findings-degraded-panel) ;;
  esac
  if [[ -z "${STEP3_REVIEW_LOOP_STATUS:-}" && "${LOOP_STATUS:-}" != zero-findings-degraded-panel ]]; then
    larch_err "**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**"
    STEP3_REVIEW_LOOP_STATUS=panel-failed
    LOOP_STATUS=panel-failed
  fi
fi
if [[ -n "${STEP3_REVIEW_LOOP_STATUS:-}" ]]; then
  if [[ ! "${STEP3_REVIEW_LOOP_STATUS}" =~ ^(complete|cap-hit|main-agent-vote-required|main-agent-apply-required|per-round-approval-required|postplan-operator-required|postplan-failed|panel-failed|panel-init-failed|tally-error|degraded-empty-collector)$ ]]; then
    larch_err "**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS after plan-review run; treating plan review as panel-failed**"
    STEP3_REVIEW_LOOP_STATUS=panel-failed
  fi
  case "${STEP3_REVIEW_LOOP_STATUS}" in
    cap-hit) LOOP_STATUS=cap-reached ;;
    complete|panel-failed|panel-init-failed|tally-error|degraded-empty-collector|main-agent-vote-required|postplan-failed) LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS}" ;;
    main-agent-apply-required|per-round-approval-required|postplan-operator-required) LOOP_STATUS=complete ;;
  esac
elif [[ -z "${LOOP_STATUS:-}" || ! "${LOOP_STATUS}" =~ ^(complete|cap-reached|zero-findings-degraded-panel|tally-error|degraded-empty-collector|panel-failed|panel-init-failed|main-agent-vote-required|main-agent-apply-required|per-round-approval-required|postplan-operator-required|postplan-failed)$ ]]; then
  larch_err "**⚠ Step 3: missing or invalid LOOP_STATUS after plan-review run; treating plan review as panel-failed**"
  LOOP_STATUS=panel-failed
fi
_step3_rounds_completed_dec=0
case "${ROUNDS_COMPLETED:-${REVIEW_ROUND_COUNT:-0}}" in
  ''|*[!0-9]*) _step3_rounds_completed_dec=0 ;;
  *) _step3_rounds_completed_dec=$((10#${ROUNDS_COMPLETED:-${REVIEW_ROUND_COUNT:-0}})) ;;
esac
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == panel-failed ]]; then
  if _step3_review_zero_round_coverage_missing "$_step3_rounds_completed_dec"; then
    larch_err "**⚠ Step 3: panel failed before any reviewer round launched; treating as panel-init-failed**"
    STEP3_REVIEW_LOOP_STATUS=panel-init-failed
    LOOP_STATUS=panel-init-failed
    TALLY_PLAN_REVIEW_STATUS=panel-init-failed
    ROUNDS_COMPLETED=0
    REVIEW_ROUND_COUNT=0
    REASON=panel-failed-zero-coverage
    _step3_review_write_result_env panel-init-failed panel-failed-zero-coverage 0
  fi
fi
# #4724: A terminal failure status can reach this point without a persisted
# .step3-review-result.env when the plan-review loop launched reviewers but died
# before its round-persist step (e.g. the collector failed mid-run). The
# guarantee EXIT trap mints .completed/step-3 only when BOTH the result env and
# the .step3-terminal-persisted-this-run marker exist, so a missing result env
# leaves the completion sentinel unwritten and the orchestrator's Step 3 recovery
# waiter hangs. Synthesize the result env (the helper also writes the terminal
# persist marker) for terminal failure statuses so the guarantee trap can release
# the orchestrator. Apply-pending / vote / operator statuses are intentionally
# excluded: minting step-3 / step-3-terminal for them would skip Gate B.
case "${STEP3_REVIEW_LOOP_STATUS:-}" in
  panel-failed|panel-init-failed|tally-error|degraded-empty-collector|postplan-failed)
    if [[ ! -f "$DESIGN_TMPDIR/.step3-review-result.env" || -L "$DESIGN_TMPDIR/.step3-review-result.env" || ! -r "$DESIGN_TMPDIR/.step3-review-result.env" ]]; then
      larch_err "**⚠ Step 3: ${STEP3_REVIEW_LOOP_STATUS} without a persisted result env; synthesizing terminal result env so the Step 3 completion sentinel is written**"
      # Best-effort, per the sentinel contract: a synthesis failure (e.g. mktemp)
      # must not abort under set -e before the KV emission below, so the
      # orchestrator still receives the terminal status on stdout.
      _step3_review_write_result_env "${STEP3_REVIEW_LOOP_STATUS}" "${REASON:-result-env-missing-after-loop}" "$_step3_rounds_completed_dec" || true
    fi
    ;;
esac
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
case "${STEP3_REVIEW_LOOP_STATUS:-}" in
  panel-failed|panel-init-failed|tally-error|degraded-empty-collector|main-agent-vote-required|main-agent-apply-required|postplan-operator-required)
    if ! python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
      --design-tmpdir "$DESIGN_TMPDIR" \
      --record-report-evidence "${STEP3_REVIEW_LOOP_STATUS}" >/dev/null 2>&1; then
      larch_err "**⚠ Step 3: failed to record escalation evidence for ${STEP3_REVIEW_LOOP_STATUS}**"
    fi
    ;;
esac
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == postplan-failed ]]; then
  printf '%s\n' 'SUMMARY_OUTCOME=failed-postplan'
  exit 1
fi
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == panel-init-failed ]]; then
  _step3_review_stage_panel_init_failed "${REASON:-panel-init-failed}"
  printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
  exit 1
fi
