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
DEGRADED_PANEL_WARNING="${DEGRADED_PANEL_WARNING:-}"
INVALID_SLOT_PANEL_WARNING="${INVALID_SLOT_PANEL_WARNING:-}"
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
  rm -f "$DESIGN_TMPDIR/no-progress-turns.count" "$DESIGN_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
  case "$step" in
    design-step3-review) rm -f "$DESIGN_TMPDIR/bg-poll-guard-probe-denials.step-3-terminal.count" 2>/dev/null || true ;;
    design-step5c) rm -f "$DESIGN_TMPDIR/bg-poll-guard-probe-denials.step-5c-terminal.count" 2>/dev/null || true ;;
    design-step-final-summary) rm -f "$DESIGN_TMPDIR/bg-poll-guard-probe-denials.step-final-summary.count" 2>/dev/null || true ;;
  esac
  _bg_wait_marker="$DESIGN_TMPDIR/.bg-wait-active"
  _bg_wait_tmp="${_bg_wait_marker}.tmp.$$"
  _bg_wait_clone_path=""
  if [ -f "$DESIGN_TMPDIR/.larch-keepalive" ] && [ ! -L "$DESIGN_TMPDIR/.larch-keepalive" ]; then
    _bg_wait_clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$DESIGN_TMPDIR/.larch-keepalive" 2>/dev/null || true)
  fi
  {
    printf 'PID=%s\n' "$$"
    printf 'CLAUDE_PID=%s\n' "${CLAUDE_PID:-}"
    printf 'START_EPOCH=%s\n' "$(date +%s)"
    printf 'STEP=%s\n' "$step"
    printf 'TIMEOUT_S=21600\n'
    printf 'CLONE_PATH=%s\n' "$_bg_wait_clone_path"
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
  exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status --design-tmpdir "$DESIGN_TMPDIR" --read-result-env
fi
step3_review_validate_resume_state
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = false ]; then
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
else
  step3_review_write_resume_state
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
fi
# Marker step id: STEP=design-step3-review
_step3_review_detached_marker="$DESIGN_TMPDIR/.step3-wrapper-detached"
_step3_review_has_detached_marker=false
if [ -f "$_step3_review_detached_marker" ] && [ ! -L "$_step3_review_detached_marker" ]; then
  _step3_review_has_detached_marker=true
fi
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = false ] && [ "$_step3_review_has_detached_marker" = false ]; then
  rm -f "$DESIGN_TMPDIR/.step3-review-result.env" "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
elif [ "$_step3_review_has_detached_marker" = false ]; then
  rm -f "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
fi
if [ "$_step3_review_has_detached_marker" = false ]; then
  rm -f "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
fi
rm -f "$DESIGN_TMPDIR"/bg-poll-guard-probe-denials.*.count 2>/dev/null || true
design_bg_wait_marker_start design-step3-review || true
_plan_review_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate plan-review stdout capture; aborting plan review**" >&2
  exit 1
}
_loop_pid=""
_step3_review_loop_identity_ready=false
_step3_review_external_signal=""
_step3_review_external_signal_rc=0

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
  [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]] || return 0
  [[ -n "${DESIGN_TMPDIR:-}" ]] || return 0
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review teardown-loop-identity \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --pid "$_pid" >/dev/null 2>&1 || true
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

_step3_review_signal_exit() {
  _step3_review_external_signal="${1:-signal}"
  _step3_review_external_signal_rc="${2:-143}"
  exit "$_step3_review_external_signal_rc"
}

_step3_review_write_detached_marker() {
  local _pid="${1:-}" _signal="${2:-}" _stdout_file="${3:-}" _marker _tmp
  [[ -n "${DESIGN_TMPDIR:-}" ]] || return 0
  [[ -n "$_pid" ]] || return 0
  _marker="$DESIGN_TMPDIR/.step3-wrapper-detached"
  _tmp="${_marker}.tmp.$$"
  {
    printf 'PID=%s\n' "$_pid"
    printf 'SIGNAL=%s\n' "$_signal"
    printf 'STDOUT_FILE=%s\n' "$_stdout_file"
    printf 'DETACHED_AT_EPOCH=%s\n' "$(date +%s)"
  } >"$_tmp" 2>/dev/null && mv -f "$_tmp" "$_marker" 2>/dev/null || rm -f "$_tmp" 2>/dev/null || true
}

_step3_review_marker_value() {
  local _key="$1" _marker="$DESIGN_TMPDIR/.step3-wrapper-detached" _line
  [ -f "$_marker" ] && [ ! -L "$_marker" ] || return 1
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    case "$_line" in
      "$_key="*) printf '%s\n' "${_line#*=}"; return 0 ;;
    esac
  done <"$_marker"
  return 1
}

_step3_review_result_env_present() {
  [ -f "$DESIGN_TMPDIR/.step3-review-result.env" ] && [ ! -L "$DESIGN_TMPDIR/.step3-review-result.env" ] || return 1
  command grep -Eq '^(STEP3_REVIEW_LOOP_STATUS=.+|LOOP_STATUS=zero-findings-degraded-panel)$' "$DESIGN_TMPDIR/.step3-review-result.env"
}

_step3_review_detached_stdout_file() {
  local _stdout_file="${1:-}" _fallback="$2" _empty_tmp=""
  if [ -n "$_stdout_file" ] && [ -f "$_stdout_file" ] && [ ! -L "$_stdout_file" ]; then
    printf '%s\n' "$_stdout_file"
    return 0
  fi
  _empty_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-step3-reattach-stdout.XXXXXX")" || {
    printf '%s\n' "$_fallback"
    return 0
  }
  printf '%s\n' "$_empty_tmp"
}

_step3_review_cleanup_detached_marker() {
  local _stdout_file="${1:-}" _base
  rm -f "$DESIGN_TMPDIR/.step3-wrapper-detached" "$DESIGN_TMPDIR/.step3-loop-identity.json" 2>/dev/null || true
  if [ -n "$_stdout_file" ] && [ -f "$_stdout_file" ] && [ ! -L "$_stdout_file" ]; then
    _base="$(basename "$_stdout_file")"
    case "$_base" in
      larch-step3-review-stdout.*|larch-step3-reattach-stdout.*) rm -f "$_stdout_file" 2>/dev/null || true ;;
    esac
  fi
}

_step3_review_reattach_detached_loop() {
  local _marker="$DESIGN_TMPDIR/.step3-wrapper-detached" _pid="" _stdout_file="" _normalize_stdout="" _rc=0 _await_rc=0
  [ -f "$_marker" ] && [ ! -L "$_marker" ] || return 1
  _pid="$(_step3_review_marker_value PID || true)"
  _stdout_file="$(_step3_review_marker_value STDOUT_FILE || true)"
  case "$_pid" in
    ''|*[!0-9]*) ;;
    *)
      python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review await-loop-identity \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --pid "$_pid" >/dev/null 2>&1 || _await_rc=$?
      ;;
  esac
  if [ "$_await_rc" -ne 0 ]; then
    _step3_review_cleanup_detached_marker "$_stdout_file"
    return 1
  fi
  if ! _step3_review_result_env_present; then
    _step3_review_cleanup_detached_marker "$_stdout_file"
    return 1
  fi
  _step3_review_kill_tmpdir_processes
  _normalize_stdout="$(_step3_review_detached_stdout_file "$_stdout_file" "$_plan_review_stdout_file")"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --stdout-file "$_normalize_stdout" \
    --loop-rc 0 || _rc=$?
  _step3_review_cleanup_detached_marker "$_stdout_file"
  _step3_review_cleanup_detached_marker "$_normalize_stdout"
  rm -f "$_plan_review_stdout_file" 2>/dev/null || true
  exit "$_rc"
}

_step3_review_cleanup() {
  local _rc=$?
  trap - EXIT TERM HUP INT
  _step3_review_guarantee_completed_sentinels  # #4489: sentinel before exit
  if [[ -n "${_loop_pid:-}" ]]; then
    if [[ -n "${_step3_review_external_signal:-}" ]]; then
      if [ "${_step3_review_loop_identity_ready:-false}" = true ]; then
        _step3_review_write_detached_marker "$_loop_pid" "$_step3_review_external_signal" "$_plan_review_stdout_file"
        disown -h "$_loop_pid" 2>/dev/null || true
        exit "$_rc"
      fi
    fi
    _step3_review_teardown_loop_group "$_loop_pid"
    _step3_review_kill_tmpdir_processes
    wait "$_loop_pid" 2>/dev/null || true
  fi
  exit "$_rc"
}

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
trap '_step3_review_signal_exit TERM 143' TERM
trap '_step3_review_signal_exit HUP 129' HUP
trap '_step3_review_signal_exit INT 130' INT
_step3_review_reattach_rc=0
if [ "$_step3_review_has_detached_marker" = true ]; then
  _step3_review_reattach_detached_loop || _step3_review_reattach_rc=$?
  if [ "$_step3_review_reattach_rc" -ne 0 ]; then
    exit "$_step3_review_reattach_rc"
  fi
fi
rm -f "$DESIGN_TMPDIR/.step3-wrapper-detached" 2>/dev/null || true
# Python owns the process-group setup.
# Bash owns wait, status capture, identity-validated teardown delegation, and fallback tmpdir cleanup.
# The dedicated loop stderr log remains the only stderr quarantine for the worker and children.
set +e
if [ -n "$STARTING_ROUND" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --starting-round "$STARTING_ROUND" \
    --new-process-group \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log" &
else
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --new-process-group \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log" &
fi
_loop_pid=$!
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review write-loop-identity \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --pid "$_loop_pid" \
  --expected-signature "plan-review run" >/dev/null 2>&1 || true
if [ -f "$DESIGN_TMPDIR/.step3-loop-identity.json" ] && [ ! -L "$DESIGN_TMPDIR/.step3-loop-identity.json" ]; then
  _step3_review_loop_identity_ready=true
fi
wait "$_loop_pid"
_plan_review_rc=$?
set -e
rm -f "$DESIGN_TMPDIR/.step3-loop-identity.json" 2>/dev/null || true
_loop_pid=""
_step3_review_kill_tmpdir_processes
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
_step3_normalize_rc=0
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --stdout-file "$_plan_review_stdout_file" \
  --loop-rc "$_plan_review_rc" || _step3_normalize_rc=$?
rm -f "$_plan_review_stdout_file"
exit "$_step3_normalize_rc"
