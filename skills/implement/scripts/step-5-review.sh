#!/usr/bin/env bash
# step-5-review.sh — /implement Step 5 review loop launcher.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

_loop_pid=""
_step5_stdout_file=""
_step5_loop_identity_ready=false
_step5_external_signal=""
_step5_external_signal_rc=0
_step5_detached_marker="$IMPLEMENT_TMPDIR/.step5-wrapper-detached"
_step5_reattach_active="$IMPLEMENT_TMPDIR/.step5-reattach-active"

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

read_run_flag_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/run-flags.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

_step5_signal_exit() {
  _step5_external_signal="${1:-signal}"
  _step5_external_signal_rc="${2:-143}"
  exit "$_step5_external_signal_rc"
}

_step5_write_detached_marker() {
  local _pid="${1:-}" _signal="${2:-}" _stdout_file="${3:-}" _detached_at_epoch="${4:-}" _tmp
  [ -n "$_pid" ] || return 1
  _tmp="${_step5_detached_marker}.tmp.$$"
  [ -n "$_detached_at_epoch" ] || _detached_at_epoch="$(date +%s)"
  if {
    printf 'PID=%s\n' "$_pid"
    printf 'SIGNAL=%s\n' "$_signal"
    printf 'STDOUT_FILE=%s\n' "$_stdout_file"
    printf 'DETACHED_AT_EPOCH=%s\n' "$_detached_at_epoch"
  } >"$_tmp" 2>/dev/null && mv -f "$_tmp" "$_step5_detached_marker" 2>/dev/null && [ -f "$_step5_detached_marker" ]; then
    return 0
  fi
  rm -f "$_tmp" "$_step5_detached_marker" 2>/dev/null || true
  return 1
}

_step5_marker_value() {
  local _key="$1" _line
  [ -f "$_step5_detached_marker" ] && [ ! -L "$_step5_detached_marker" ] || return 1
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      "$_key="*) printf '%s\n' "${_line#*=}"; return 0 ;;
    esac
  done <"$_step5_detached_marker"
  return 1
}

_step5_loop_identity_on_disk() {
  [ -f "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" ] && [ ! -L "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" ]
}

_step5_teardown_loop_group() {
  local _pid="${1:-}"
  [ -n "$_pid" ] || return 0
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix teardown-loop-identity \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --pid "$_pid" >/dev/null 2>&1 || true
}

_step5_kill_tmpdir_processes() {
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session kill-background-processes \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" >/dev/null 2>&1 || true
}

_step5_preidentity_kill_group() {
  local _pid="${1:-}" _line="" _pgid="" _cmd=""
  [ -n "$_pid" ] || return 0
  _line=$(ps -p "$_pid" -o pid= -o pgid= -o command= 2>/dev/null || true)
  [ -n "$_line" ] || return 0
  _pgid=$(printf '%s\n' "$_line" | awk '{print $2; exit}')
  _cmd=$(printf '%s\n' "$_line" | awk '{$1=""; $2=""; sub(/^[[:space:]]+/, ""); print; exit}')
  case "$_pgid" in ''|*[!0-9]*) return 0 ;; esac
  [ "$_pgid" = "$_pid" ] || return 0
  case "$_cmd" in *"review-and-fix"*"step5"*) kill -TERM "-$_pgid" 2>/dev/null || kill -TERM "$_pid" 2>/dev/null || true ;; esac
}

_step5_emit_wrapper_stall() {
  local _reason="${1:-reattach-failed}"
  printf 'STEP5_REVIEW_STATUS=stall\n'
  printf 'STALL_TRACKING=true\n'
  printf 'STALL_REASON=%s\n' "$_reason"
  printf 'ROUNDS_COMPLETED=0\n'
  printf 'FINAL_ROUND_NUM=0\n'
  printf 'FINAL_REVIEW_AND_FIX_STATUS=unknown\n'
  printf 'CODER_STATUS=\n'
  printf 'FILES_CHANGED_HINT=\n'
  printf 'EFFECTIVE_ROUND_CAP=2\n'
}

_step5_write_terminal_sentinel() {
  mkdir -p "$IMPLEMENT_TMPDIR/.completed" 2>/dev/null || true
  : >"$IMPLEMENT_TMPDIR/.completed/step-5-terminal" 2>/dev/null || true
}

_step5_cleanup_stdout_if_temp() {
  local _path="${1:-}" _base
  [ -n "$_path" ] || return 0
  [ -f "$_path" ] && [ ! -L "$_path" ] || return 0
  _base="$(basename "$_path")"
  case "$_base" in
    larch-step5-review-stdout.*|larch-step5-reattach-stdout.*) rm -f "$_path" 2>/dev/null || true ;;
  esac
}

_step5_cleanup() {
  local _rc=$?
  trap - EXIT TERM HUP INT
  rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
  if [ -n "${_loop_pid:-}" ]; then
    if [ -n "${_step5_external_signal:-}" ]; then
      if [ "${_step5_loop_identity_ready:-false}" = true ] || _step5_loop_identity_on_disk; then
        if _step5_write_detached_marker "$_loop_pid" "$_step5_external_signal" "$_step5_stdout_file"; then
          rm -f "$_step5_reattach_active" 2>/dev/null || true
          disown -h "$_loop_pid" 2>/dev/null || true
          exit "$_rc"
        fi
      else
        _step5_preidentity_kill_group "$_loop_pid"
      fi
    fi
    _step5_teardown_loop_group "$_loop_pid"
    _step5_kill_tmpdir_processes
    wait "$_loop_pid" 2>/dev/null || true
  fi
  rm -f "$_step5_reattach_active" 2>/dev/null || true
  exit "$_rc"
}

_step5_bg_wait_marker_start() {
  local _start _claude_pid _clone_path
  rm -f "$IMPLEMENT_TMPDIR/no-progress-turns.count" "$IMPLEMENT_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-5-terminal.count" 2>/dev/null || true
  _start=$(date +%s 2>/dev/null) || _start=0
  case "$_start" in ''|*[!0-9]*) _start=0 ;; esac
  _claude_pid="${LARCH_BG_POLL_GUARD_SESSION_PID:-${PPID:-}}"
  _clone_path=""
  if [ -f "$IMPLEMENT_TMPDIR/.larch-keepalive" ] && [ ! -L "$IMPLEMENT_TMPDIR/.larch-keepalive" ]; then
    _clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$IMPLEMENT_TMPDIR/.larch-keepalive" 2>/dev/null || true)
  fi
  printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step5-review\nTIMEOUT_S=21600\nCLONE_PATH=%s\n' \
    "$$" "$_claude_pid" "$_start" "$_clone_path" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
}

_step5_normalize_and_finish() {
  local _stdout_file="$1" _loop_rc="$2" _rc=0
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix normalize-status \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --stdout-file "$_stdout_file" \
    --loop-rc "$_loop_rc" || _rc=$?
  if [ "$_rc" -eq 0 ]; then
    _step5_write_terminal_sentinel
    rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
  fi
  return "$_rc"
}

_step5_reattach_detached_loop() {
  local _pid _stdout_file _signal _detached_at_epoch="" _await_rc=0 _normalize_rc=0
  [ -f "$_step5_detached_marker" ] && [ ! -L "$_step5_detached_marker" ] || return 1
  _pid="$(_step5_marker_value PID || true)"
  _stdout_file="$(_step5_marker_value STDOUT_FILE || true)"
  _signal="$(_step5_marker_value SIGNAL || true)"
  _detached_at_epoch="$(_step5_marker_value DETACHED_AT_EPOCH || true)"
  case "$_pid" in
    ''|*[!0-9]*) rm -f "$_step5_detached_marker" "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" 2>/dev/null || true; return 1 ;;
  esac
  _loop_pid="$_pid"
  _step5_stdout_file="$_stdout_file"
  _step5_loop_identity_ready=true
  : >"$_step5_reattach_active" 2>/dev/null || true
  rm -f "$_step5_detached_marker" 2>/dev/null || true
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix await-loop-identity \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --pid "$_pid" \
    --reattach >/dev/null 2>&1 || _await_rc=$?
  if [ "$_await_rc" -ne 0 ]; then
    _step5_write_detached_marker "$_pid" "$_signal" "$_stdout_file" "$_detached_at_epoch" || true
    rm -f "$_step5_reattach_active" "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
    _loop_pid=""
    _step5_emit_wrapper_stall reattach-await-failed
    exit "$_await_rc"
  fi
  rm -f "$_step5_reattach_active" 2>/dev/null || true
  _step5_kill_tmpdir_processes
  _step5_normalize_and_finish "$_stdout_file" 0 || _normalize_rc=$?
  if [ "$_normalize_rc" -ne 0 ]; then
    _step5_write_detached_marker "$_pid" "$_signal" "$_stdout_file" "$_detached_at_epoch" || true
    rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
    _loop_pid=""
    exit "$_normalize_rc"
  fi
  rm -f "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" "$_step5_detached_marker" 2>/dev/null || true
  _step5_cleanup_stdout_if_temp "$_stdout_file"
  _loop_pid=""
  exit 0
}

trap _step5_cleanup EXIT
trap '_step5_signal_exit TERM 143' TERM
trap '_step5_signal_exit HUP 129' HUP
trap '_step5_signal_exit INT 130' INT

rehydrate_plugin_root
_step5_bg_wait_marker_start

if [ -f "$_step5_detached_marker" ] && [ ! -L "$_step5_detached_marker" ]; then
  _step5_reattach_detached_loop || true
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true
dynamic_archetypes_cap=""
if [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  dynamic_archetypes_cap=$(awk 'BEGIN{p="LARCH_DYNAMIC_ARCHETYPES_MAX="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
if [ -z "$dynamic_archetypes_cap" ] && [ -n "${LARCH_DYNAMIC_ARCHETYPES_MAX:-}" ]; then
  dynamic_archetypes_cap="$LARCH_DYNAMIC_ARCHETYPES_MAX"
fi
[ -n "$dynamic_archetypes_cap" ] || dynamic_archetypes_cap=1
case "$dynamic_archetypes_cap" in [0-1]) ;; *) printf 'ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: %s
' "$dynamic_archetypes_cap" >&2; exit 2 ;; esac
export LARCH_DYNAMIC_ARCHETYPES_MAX="$dynamic_archetypes_cap"
difficulty_override=$(read_run_flag_key DIFFICULTY_OVERRIDE "")
case "$difficulty_override" in ""|TRIVIAL|MODERATE|HARD) ;; *) difficulty_override="" ;; esac
printf '> **🔶 /implement 5: code review — review-and-fix step5 --mode loop, fixed tier cap 2; escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; dynamic-archetypes cap=%s**\n' "$dynamic_archetypes_cap"

rm -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" 2>/dev/null || true
_step5_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step5-review-stdout.XXXXXX")" || {
  _step5_emit_wrapper_stall stdout-capture-failed
  exit 1
}

set +e
if [ -n "$difficulty_override" ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1 --difficulty "$difficulty_override" \
    --new-process-group --orphan-timeout-s 7200 \
    >"$_step5_stdout_file" 2>"$IMPLEMENT_TMPDIR/review-and-fix-step5-loop.stderr" &
else
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1 \
    --new-process-group --orphan-timeout-s 7200 \
    >"$_step5_stdout_file" 2>"$IMPLEMENT_TMPDIR/review-and-fix-step5-loop.stderr" &
fi
_loop_pid=$!
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix write-loop-identity \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --pid "$_loop_pid" \
  --expected-signature "review-and-fix step5" >/dev/null 2>&1 || true
if [ -f "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" ] && [ ! -L "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" ]; then
  _step5_loop_identity_ready=true
fi
wait "$_loop_pid"
_step5_loop_rc=$?
set -e
_loop_pid=""
rm -f "$IMPLEMENT_TMPDIR/.step5-loop-identity.json" 2>/dev/null || true
_step5_kill_tmpdir_processes
_step5_normalize_rc=0
_step5_normalize_and_finish "$_step5_stdout_file" "$_step5_loop_rc" || _step5_normalize_rc=$?
_step5_cleanup_stdout_if_temp "$_step5_stdout_file"
exit "$_step5_normalize_rc"
