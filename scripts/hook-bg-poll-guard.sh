#!/usr/bin/env bash
# hook-bg-poll-guard.sh — PreToolUse hook: deny /design progress polling while an immediate-background wrapper is active.
# set -e intentionally omitted: hooks must fail open on malformed input or runtime errors.

set -uo pipefail

[ "${LARCH_BG_POLL_GUARD_DISABLE:-}" = "1" ] && exit 0
[ "${LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT:-}" = "1" ] && exit 0

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
case "$tool_name" in
  Read|Bash|Monitor|TaskOutput) ;;
  *) exit 0 ;;
esac

now=$(date +%s 2>/dev/null) || exit 0
case "$now" in ''|*[!0-9]*) exit 0 ;; esac

cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || exit 0

canonical_dir() {
  [ -n "$1" ] || return 1
  [ -d "$1" ] || return 1
  (cd "$1" 2>/dev/null && pwd -P)
}

cwd_canon=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
fi

is_allowed_marker_parent() {
  local dir="$1" home_sessions tmp_root
  [ -n "$dir" ] || return 1
  if [ -n "${HOME:-}" ]; then
    home_sessions="$(canonical_dir "$HOME/.cache/larch/sessions" 2>/dev/null || true)"
    if [ -n "$home_sessions" ]; then
      case "$dir" in "$home_sessions"/*) return 0 ;; esac
    fi
  fi
  tmp_root="$(canonical_dir "${TMPDIR:-/tmp}" 2>/dev/null || canonical_dir /tmp 2>/dev/null || true)"
  if [ -n "$tmp_root" ]; then
    case "$dir" in
      "$tmp_root"/claude-design-*|"$tmp_root"/claude-implement-*|"$tmp_root"/larch-*|"$tmp_root"/*/claude-design-*|"$tmp_root"/*/claude-implement-*|"$tmp_root"/*/larch-*) return 0 ;;
    esac
  fi
  case "$dir" in */.cache/larch/sessions/*) return 0 ;; esac
  return 1
}

marker_candidates() {
  if [ -n "${LARCH_BG_POLL_GUARD_MARKER:-}" ]; then
    printf '%s\n' "$LARCH_BG_POLL_GUARD_MARKER"
    return 0
  fi
  if [ -n "${HOME:-}" ] && [ -d "$HOME/.cache/larch/sessions" ]; then
    find "$HOME/.cache/larch/sessions" -maxdepth 2 -name .bg-wait-active -type f 2>/dev/null || true
  fi
  if [ -d "${TMPDIR:-/tmp}" ]; then
    # Scope to larch-/claude-design-/claude-implement-prefixed session dirs only; avoids
    # scanning all of the macOS per-user $TMPDIR (~77k+ dirs) which exceeds the 5-10s hook timeout.
    # Collect matched dirs and run ONE find over all of them (#5943): a find subprocess
    # per dir makes discovery cost O(N) in accumulated session-dir count, and per-spawn
    # overhead alone exceeded the 10s hook budget at ~2k dirs.
    _lmc_dirs=()
    for _lmc_d in "${TMPDIR:-/tmp}"/larch-* "${TMPDIR:-/tmp}"/claude-design-* "${TMPDIR:-/tmp}"/claude-implement-*; do
      [ -d "$_lmc_d" ] || continue
      _lmc_dirs+=("$_lmc_d")
    done
    if [ "${#_lmc_dirs[@]}" -gt 0 ]; then
      find "${_lmc_dirs[@]}" -maxdepth 2 -name .bg-wait-active -type f 2>/dev/null || true
    fi
  fi
}

marker_value() {
  local marker="$1" key="$2"
  awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/, ""); print; found=1; exit } END { exit found ? 0 : 1 }' "$marker" 2>/dev/null
}

# Returns 0 when two canonical clone paths denote the same repo tree: exact
# match or one path is a subdirectory of the other (#5927 subdirectory cwd).
clone_paths_same() {
  local marker_canon="$1" current_canon="$2"
  [ "$marker_canon" = "$current_canon" ] && return 0
  case "$current_canon" in
    "$marker_canon"/*) return 0 ;;
  esac
  case "$marker_canon" in
    "$current_canon"/*) return 0 ;;
  esac
  return 1
}

# Returns 0 only when the marker directory's recorded clone identity is known
# and canonically differs from the current session's cwd (#5927). Unknown
# identity on either side returns 1 (treated as same-clone / still blocks). The
# marker-local CLONE_PATH stamp wins when it is present and canonical; otherwise
# fall back to .larch-keepalive so older markers keep the pre-stamp behavior.
marker_foreign_clone() {
  local dir="$1" current_canon="$2" marker keepalive marker_clone marker_canon
  [ -n "$current_canon" ] || return 1
  marker="$dir/.bg-wait-active"
  if [ -f "$marker" ] && [ ! -L "$marker" ]; then
    marker_clone=$(marker_value "$marker" CLONE_PATH 2>/dev/null || true)
    if [ -n "$marker_clone" ]; then
      marker_canon=$(canonical_dir "$marker_clone" 2>/dev/null || true)
      if [ -n "$marker_canon" ]; then
        clone_paths_same "$marker_canon" "$current_canon" && return 1
        return 0
      fi
    fi
  fi
  keepalive="$dir/.larch-keepalive"
  [ -f "$keepalive" ] && [ ! -L "$keepalive" ] || return 1
  marker_clone=$(marker_value "$keepalive" CLONE_PATH) || return 1
  [ -n "$marker_clone" ] || return 1
  marker_canon=$(canonical_dir "$marker_clone" 2>/dev/null) || return 1
  clone_paths_same "$marker_canon" "$current_canon" && return 1
  return 0
}

marker_clone_identity_canon() {
  local dir="$1" marker keepalive marker_clone marker_canon
  marker="$dir/.bg-wait-active"
  if [ -f "$marker" ] && [ ! -L "$marker" ]; then
    marker_clone=$(marker_value "$marker" CLONE_PATH 2>/dev/null || true)
    if [ -n "$marker_clone" ]; then
      marker_canon=$(canonical_dir "$marker_clone" 2>/dev/null || true)
      if [ -n "$marker_canon" ]; then
        printf '%s' "$marker_canon"
        return 0
      fi
    fi
  fi
  keepalive="$dir/.larch-keepalive"
  [ -f "$keepalive" ] && [ ! -L "$keepalive" ] || return 1
  marker_clone=$(marker_value "$keepalive" CLONE_PATH) || return 1
  [ -n "$marker_clone" ] || return 1
  canonical_dir "$marker_clone" 2>/dev/null
}

marker_step_completed() {
  # Returns 0 when the immediate-background step named by the marker's STEP
  # value has already written its terminal completion sentinel. Used to release
  # the poll guard when a <task-notification> arrives in the same turn as the
  # launch ack and the bg process has not yet run its EXIT-trap marker cleanup
  # (#4431, #4450). Sentinel release is the intended fast path after a
  # notification; callers still need bounded foreground probes for transient
  # mismatches where the notification arrives before the sentinel is visible.
  # Covers design-step3-review, design-step4-tail, design-step5c,
  # design-step-final-summary, implement-step3-checks, implement-step5-review,
  # implement-step5-resume, implement-step5-self-review, implement-step6-checks,
  # implement-step7a, and implement-step8-ship.
  local dir="$1" step="$2" sentinel="" sidecar=""
  [ -n "$dir" ] || return 1
  case "$step" in
    design-step3-review)
      sentinel="$dir/.completed/step-3-terminal"
      sidecar="$dir/.step3-terminal-persisted-this-run"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ] && [ -f "$sidecar" ] && [ ! -L "$sidecar" ] && [ -r "$sidecar" ]
      ;;
    design-step4-tail)
      sentinel="$dir/.completed/step-4"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    design-step5c)
      sentinel="$dir/.completed/step-5c-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    design-step-final-summary)
      sentinel="$dir/.completed/step-final-summary"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step3-checks)
      sentinel="$dir/.completed/step-3-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step5-review)
      sentinel="$dir/.completed/step-5-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step5-resume)
      sentinel="$dir/.completed/step-5-resume-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step5-self-review)
      sentinel="$dir/.completed/step-5-self-review-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step6-checks)
      sentinel="$dir/.completed/step-6-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step7a)
      sentinel="$dir/.completed/step-7a-terminal"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    implement-step8-ship)
      sentinel="$dir/.step-8-ship-handoff.rc"
      [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
      ;;
    *) return 1 ;;
  esac
}

# #5478: per-sentinel consecutive foreground-probe clamp. The sanctioned recovery
# pattern is ONE foreground terminal-sentinel probe per real <task-notification>.
# Spurious empty-output notifications (#5240) can drive the orchestrator to probe on
# every turn, burning O(N) turns while the sentinel stays absent. The hook cannot see
# the notification output, so it counts consecutive foreground probes per sentinel
# while the sentinel is absent and denies once the count exceeds the threshold,
# forcing the orchestrator to yield until a real completion notification arrives.
# Denying a probe is safe: completion is detected by marker release once the sentinel
# is present (the live-marker scan releases the guard at marker_step_completed), not
# by the probe, so a clamped probe never blocks completion detection. The count is
# keyed per sentinel basename so Step 3 (step-3-terminal), Step 5c
# (step-5c-terminal), and implement Step 5 (step-5-terminal) waits in one tmpdir
# cannot contaminate each other, and it clears
# when the sentinel becomes present.
PROBE_CLAMP_THRESHOLD="${LARCH_BG_POLL_GUARD_PROBE_THRESHOLD:-2}"
case "$PROBE_CLAMP_THRESHOLD" in ''|*[!0-9]*) PROBE_CLAMP_THRESHOLD=2 ;; esac

TASK_OUTPUT_READ_THRESHOLD="${LARCH_BG_POLL_GUARD_TASK_OUTPUT_READ_THRESHOLD:-2}"
case "$TASK_OUTPUT_READ_THRESHOLD" in ''|*[!0-9]*) TASK_OUTPUT_READ_THRESHOLD=2 ;; esac

probe_counter_file() {
  printf '%s/bg-poll-guard-probe-denials.%s.count' "$1" "$2"
}

probe_counter_value() {
  local f="$1" v=0
  if [ -f "$f" ] && [ ! -L "$f" ]; then
    v=$(awk 'NR==1 { print; exit }' "$f" 2>/dev/null || printf '0')
    case "$v" in ''|*[!0-9]*) v=0 ;; esac
  fi
  printf '%s' "$v"
}

probe_counter_bump() {
  # Best-effort atomic increment; echoes the new (in-memory) value even if the write
  # fails so the clamp decision stays correct within this invocation. A failed write
  # means the next invocation re-reads the prior value (fail open: no clamp), matching
  # the hook's fail-open-on-telemetry-failure posture.
  local f="$1" new tmp
  new=$(( $(probe_counter_value "$f") + 1 ))
  tmp="$f.tmp.$$"
  if printf '%s\n' "$new" >"$tmp" 2>/dev/null; then
    mv -f "$tmp" "$f" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  else
    rm -f "$tmp" 2>/dev/null || true
  fi
  printf '%s' "$new"
}

reset_probe_counter_for_step() {
  # Clear a step's probe-clamp counter once its wait completes (sentinel present), so
  # a later wait reusing the tmpdir starts fresh.
  local dir="$1" step="$2" name=""
  case "$step" in
    design-step3-review) name="step-3-terminal" ;;
    design-step4-tail) name="step-4" ;;
    design-step5c) name="step-5c-terminal" ;;
    design-step-final-summary) name="step-final-summary" ;;
    implement-step3-checks) name="step-3-terminal" ;;
    implement-step5-review) name="step-5-terminal" ;;
    implement-step5-resume) name="step-5-resume-terminal" ;;
    implement-step5-self-review) name="step-5-self-review-terminal" ;;
    implement-step6-checks) name="step-6-terminal" ;;
    implement-step7a) name="step-7a-terminal" ;;
    implement-step8-ship) name="step-8-ship-handoff.rc" ;;
    *) return 0 ;;
  esac
  rm -f "$(probe_counter_file "$dir" "$name")" 2>/dev/null || true
}

reset_task_output_read_state() {
  local dir="$1"
  [ -n "$dir" ] || return 0
  rm -f "$dir"/bg-poll-guard-task-output-read.*.count 2>/dev/null || true
  if [ -e "$dir/no-progress-task-output-clamped" ] && [ ! -L "$dir/no-progress-task-output-clamped" ]; then
    rm -f \
      "$dir/no-progress-task-output-clamped" \
      "$dir/no-progress-circuit-breaker-armed" \
      "$dir/no-progress-stop-block-emitted" \
      "$dir/no-progress-turns.count" \
      2>/dev/null || true
  else
    rm -f "$dir/no-progress-task-output-clamped" 2>/dev/null || true
  fi
}

task_output_read_state_file() {
  printf '%s/bg-poll-guard-task-output-read.%s.count' "$1" "$2"
}

read_task_output_id() {
  local path="$1" token id
  token=$(printf '%s' "$path" | sed -nE 's#^(.*/)?tasks/([A-Za-z0-9._-]+)\.output$#\2#p')
  [ -n "$token" ] || return 1
  id="$token"
  printf '%s' "$id"
}

task_output_file_signature() {
  local path="$1" size checksum class non_ws
  [ -f "$path" ] || return 1
  [ ! -L "$path" ] || return 1
  [ -r "$path" ] || return 1
  size=$(wc -c <"$path" 2>/dev/null | awk '{print $1}') || return 1
  case "$size" in ''|*[!0-9]*) return 1 ;; esac
  checksum=$(dd if="$path" bs=200 count=1 2>/dev/null | cksum 2>/dev/null | awk '{print $1}') || return 1
  case "$checksum" in ''|*[!0-9]*) return 1 ;; esac
  non_ws=$(LC_ALL=C tr -d '[:space:]' <"$path" 2>/dev/null | wc -c | awk '{print $1}') || return 1
  case "$non_ws" in ''|*[!0-9]*) return 1 ;; esac
  class=content
  [ "$non_ws" -eq 0 ] && class=whitespace
  printf '%s\t%s\t%s' "$class" "$size" "$checksum"
}

task_output_read_bump() {
  local dir="$1" task_id="$2" sig="$3" state_file old_class old_size old_checksum old_count
  local class size checksum count tmp
  IFS=$'\t' read -r class size checksum <<EOF_SIG
$sig
EOF_SIG
  [ -n "$class" ] || return 1
  state_file=$(task_output_read_state_file "$dir" "$task_id")
  old_class=""
  old_size=""
  old_checksum=""
  old_count=0
  if [ -f "$state_file" ] && [ ! -L "$state_file" ]; then
    IFS=$'\t' read -r old_class old_size old_checksum old_count <"$state_file" 2>/dev/null || true
    case "$old_count" in ''|*[!0-9]*) old_count=0 ;; esac
  fi
  if [ "$class" = "whitespace" ]; then
    count=$((old_count + 1))
  elif [ "$old_class" = "$class" ] && [ "$old_size" = "$size" ] && [ "$old_checksum" = "$checksum" ]; then
    count=$((old_count + 1))
  else
    count=1
  fi
  tmp="$state_file.tmp.$$"
  if printf '%s\t%s\t%s\t%s\n' "$class" "$size" "$checksum" "$count" >"$tmp" 2>/dev/null; then
    mv -f "$tmp" "$state_file" 2>/dev/null || { rm -f "$tmp" 2>/dev/null || true; return 1; }
  else
    rm -f "$tmp" 2>/dev/null || true
    return 1
  fi
  printf '%s\t%s' "$class" "$count"
}

probe_sentinel_name() {
  # Extract the terminal sentinel basename from a command already matched as a
  # foreground probe. Returns non-zero when no known sentinel is present.
  local cmd="$1" normalized name
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  name=$(printf '%s' "$normalized" | sed -E 's#.*/\.completed/(step-3-terminal|step-4|step-5c-terminal|step-5-terminal|step-final-summary).*#\1#')
  case "$name" in
    step-3-terminal|step-4|step-5c-terminal|step-5-terminal|step-final-summary) printf '%s' "$name"; return 0 ;;
  esac
  # shellcheck disable=SC2016 # Match literal $IMPLEMENT_TMPDIR in candidate Bash commands.
  if printf '%s' "$normalized" | grep -Eq '(\$IMPLEMENT_TMPDIR|\$\{IMPLEMENT_TMPDIR\})/\.step-8-ship-handoff\.rc'; then
    printf '%s' 'step-8-ship-handoff.rc'
    return 0
  fi
  return 1
}

probe_target_live_dir() {
  # Resolve the live tmpdir a foreground probe binds to, mirroring
  # bash_is_terminal_sentinel_foreground_probe: explicit DESIGN_TMPDIR match, else
  # the sole live dir when unset.
  local cmd="$1" normalized assigned_tmpdir assigned_canon dir live_dir_count=0 sole_dir=""
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  if printf '%s' "$normalized" | grep -Eq '^DESIGN_TMPDIR=[^;]+;'; then
    assigned_tmpdir=$(printf '%s' "$normalized" | sed -E 's/^DESIGN_TMPDIR=([^;]+);.*/\1/' | tr -d '"' | tr -d "'")
    assigned_canon=$(canonical_dir "$assigned_tmpdir" 2>/dev/null) || return 1
    while IFS= read -r dir || [ -n "$dir" ]; do
      [ -n "$dir" ] || continue
      if [ "$assigned_canon" = "$dir" ]; then
        printf '%s' "$dir"
        return 0
      fi
    done <"$live_dirs_file"
    return 1
  fi
  while IFS= read -r dir || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    live_dir_count=$((live_dir_count + 1))
    sole_dir="$dir"
  done <"$live_dirs_file"
  [ "$live_dir_count" -eq 1 ] || return 1
  printf '%s' "$sole_dir"
}

probe_target_live_dir_step8() {
  # Resolve the live tmpdir for the Step 8 handoff rc probe. An explicit
  # IMPLEMENT_TMPDIR=<abs>; prefix must match a live implement-step8-ship marker.
  # Without an assignment, bind to the sole live Step 8 marker even when other
  # live markers for different steps exist.
  local cmd="$1" normalized assigned_tmpdir assigned_canon dir step step8_count=0 sole_step8_dir=""
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  # shellcheck disable=SC2016 # Match the exact documented pointer-reader command.
  step8_pointer_prefix='IMPLEMENT_TMPDIR=$(awk '\''BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null);'
  if printf '%s' "$normalized" | grep -Fq "$step8_pointer_prefix"; then
    :
  elif printf '%s' "$normalized" | grep -Eq '^IMPLEMENT_TMPDIR=[^;]+;'; then
    assigned_tmpdir=$(printf '%s' "$normalized" | sed -E 's/^IMPLEMENT_TMPDIR=([^;]+);.*/\1/' | tr -d '"' | tr -d "'")
    assigned_canon=$(canonical_dir "$assigned_tmpdir" 2>/dev/null) || return 1
    while IFS='|' read -r dir step || [ -n "$dir" ]; do
      [ -n "$dir" ] || continue
      if [ "$step" = "implement-step8-ship" ] && [ "$assigned_canon" = "$dir" ]; then
        printf '%s' "$dir"
        return 0
      fi
    done <"$live_markers_file"
    return 1
  fi
  while IFS='|' read -r dir step || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    if [ "$step" = "implement-step8-ship" ]; then
      step8_count=$((step8_count + 1))
      sole_step8_dir="$dir"
    fi
  done <"$live_markers_file"
  [ "$step8_count" -eq 1 ] || return 1
  printf '%s' "$sole_step8_dir"
}

probe_target_live_dir_implement_step35() {
  # Resolve the live tmpdir for the narrow /implement Step 3/5 terminal-sentinel
  # probe. The probed sentinel basename selects the matching implement marker
  # step, so Step 3 probes never bind to Step 5 markers and vice versa.
  local cmd="$1" normalized assigned_tmpdir assigned_canon dir step name expected_step match_count=0 sole_match_dir=""
  name=$(probe_sentinel_name "$cmd") || return 1
  case "$name" in
    step-3-terminal) expected_step="implement-step3-checks" ;;
    step-5-terminal) expected_step="implement-step5-review" ;;
    *) return 1 ;;
  esac
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  if printf '%s' "$normalized" | grep -Eq '^IMPLEMENT_TMPDIR=[^;]+;'; then
    assigned_tmpdir=$(printf '%s' "$normalized" | sed -E 's/^IMPLEMENT_TMPDIR=([^;]+);.*/\1/' | tr -d '"' | tr -d "'")
    assigned_canon=$(canonical_dir "$assigned_tmpdir" 2>/dev/null) || return 1
    while IFS='|' read -r dir step || [ -n "$dir" ]; do
      [ -n "$dir" ] || continue
      if [ "$step" = "$expected_step" ] && [ "$assigned_canon" = "$dir" ]; then
        printf '%s' "$dir"
        return 0
      fi
    done <"$live_markers_file"
    return 1
  fi
  while IFS='|' read -r dir step || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    if [ "$step" = "$expected_step" ]; then
      match_count=$((match_count + 1))
      sole_match_dir="$dir"
    fi
  done <"$live_markers_file"
  [ "$match_count" -eq 1 ] || return 1
  printf '%s' "$sole_match_dir"
}

terminal_sentinel_allowed_for_live_step() {
  local dir="$1" name="$2" live_dir live_step expected=""
  while IFS='|' read -r live_dir live_step || [ -n "$live_dir" ]; do
    [ -n "$live_dir" ] || continue
    [ "$live_dir" = "$dir" ] || continue
    case "$live_step" in
      design-step3-review) expected="step-3-terminal" ;;
      design-step4-tail) expected="step-4" ;;
      design-step5c) expected="step-5c-terminal" ;;
      design-step-final-summary) expected="step-final-summary" ;;
      *) expected="" ;;
    esac
    [ "$name" = "$expected" ] && return 0
  done <"$live_markers_file"
  return 1
}

bash_is_implement_terminal_sentinel_foreground_probe() {
  local cmd="$1" normalized dir probe_target_re test_re sentinel_name sentinel_abs
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  bash_is_control_loop "$normalized" && return 1
  printf '%s' "$normalized" | grep -Eq '(^|[^[:alnum:]_])sleep([^[:alnum:]_]|$)' && return 1
  case "$normalized" in *'&&'*|*'||'*|*tasks/*.output*|*.step-8-ship-handoff.*) return 1 ;; esac
  # shellcheck disable=SC2016 # Match literal $IMPLEMENT_TMPDIR in candidate Bash commands.
  probe_target_re='(\$IMPLEMENT_TMPDIR/\.completed/(step-3-terminal|step-5-terminal)|\$\{IMPLEMENT_TMPDIR\}/\.completed/(step-3-terminal|step-5-terminal))'
  test_re='^(IMPLEMENT_TMPDIR=[^;]+;[[:space:]]*)?test[[:space:]]+-f[[:space:]]+"?'"$probe_target_re"'"?$'
  printf '%s' "$normalized" | grep -Eq "$test_re" || return 1
  dir=$(probe_target_live_dir_implement_step35 "$normalized") || return 1
  sentinel_name=$(probe_sentinel_name "$normalized") || return 1
  sentinel_abs="$dir/.completed/$sentinel_name"
  if [ -L "$sentinel_abs" ]; then
    return 1
  fi
  return 0
}

bash_is_step8_handoff_foreground_probe() {
  local cmd="$1" normalized dir probe_target_re test_re
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  bash_is_control_loop "$normalized" && return 1
  printf '%s' "$normalized" | grep -Eq '(^|[^[:alnum:]_])sleep([^[:alnum:]_]|$)' && return 1
  case "$normalized" in *'&&'*|*'||'*|*tasks/*.output*|*.completed/*|*.step-8-ship-handoff.json*|*.step-8-ship-handoff.stdout-capture*) return 1 ;; esac
  # shellcheck disable=SC2016 # Match literal $IMPLEMENT_TMPDIR in the candidate Bash command.
  probe_target_re='(\$IMPLEMENT_TMPDIR/\.step-8-ship-handoff\.rc|\$\{IMPLEMENT_TMPDIR\}/\.step-8-ship-handoff\.rc)'
  test_re='^(IMPLEMENT_TMPDIR=[^;]+;[[:space:]]*)?test[[:space:]]+-f[[:space:]]+"?'"$probe_target_re"'"?$'
  # shellcheck disable=SC2016 # Match the exact documented pointer-reader command.
  pointer_test_prefix='IMPLEMENT_TMPDIR=$(awk '\''BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null);'
  if printf '%s' "$normalized" | grep -Eq "$test_re"; then
    :
  elif printf '%s' "$normalized" | grep -Fq "$pointer_test_prefix"; then
    pointer_tail=${normalized#"$pointer_test_prefix"}
    printf '%s' "$pointer_tail" | grep -Eq '^[[:space:]]*test[[:space:]]+-f[[:space:]]+"?'"$probe_target_re"'"?$' || return 1
  else
    return 1
  fi
  dir=$(probe_target_live_dir_step8 "$normalized") || return 1
  [ ! -L "$dir/.step-8-ship-handoff.rc" ] || return 1
  return 0
}

step8_handoff_probe_clamp() {
  # Entered only after bash_is_step8_handoff_foreground_probe matched. Step 8's
  # release sentinel lives at the tmpdir root, not under .completed/.
  local cmd="$1" name dir counter cnt sentinel_present=0 over_threshold=0
  name=$(probe_sentinel_name "$cmd") || exit 0
  [ "$name" = "step-8-ship-handoff.rc" ] || exit 0
  dir=$(probe_target_live_dir_step8 "$cmd") || exit 0
  if [ -f "$dir/.step-8-ship-handoff.rc" ] && [ ! -L "$dir/.step-8-ship-handoff.rc" ]; then
    rm -f "$(probe_counter_file "$dir" "$name")" 2>/dev/null || true
    sentinel_present=1
  else
    counter=$(probe_counter_file "$dir" "$name")
    cnt=$(probe_counter_bump "$counter")
    if [ "$cnt" -gt "$PROBE_CLAMP_THRESHOLD" ]; then
      over_threshold=1
    fi
  fi
  if [ "$sentinel_present" -eq 0 ] && [ "$over_threshold" -eq 1 ]; then
    json_deny_probe "$dir"
  fi
  exit 0
}

json_escape() {
  # Escape the limited local metadata embedded in hook deny JSON without depending on
  # jq at final emission time. Bash strings cannot contain NUL; other control chars
  # are collapsed to spaces before JSON quoting.
  printf '%s' "$1" | LC_ALL=C tr '\n\r\t' '   ' | sed 's/\\/\\\\/g; s/"/\\"/g'
}

resolve_hook_plugin_version() {
  local root plugin_json version script_dir
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    plugin_json="$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json"
    if [ -f "$plugin_json" ] && [ ! -L "$plugin_json" ]; then
      version=$(awk -F'"' '/"version"[[:space:]]*:/ { print $4; exit }' "$plugin_json" 2>/dev/null || true)
      if [ -n "$version" ]; then
        printf '%s' "$version"
        return 0
      fi
    fi
  fi
  script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P) || script_dir=""
  if [ -n "$script_dir" ]; then
    root=$(cd "$script_dir/.." 2>/dev/null && pwd -P) || root=""
    plugin_json="$root/.claude-plugin/plugin.json"
    if [ -f "$plugin_json" ] && [ ! -L "$plugin_json" ]; then
      version=$(awk -F'"' '/"version"[[:space:]]*:/ { print $4; exit }' "$plugin_json" 2>/dev/null || true)
      if [ -n "$version" ]; then
        printf '%s' "$version"
        return 0
      fi
    fi
  fi
  printf '%s' unknown
}

HOOK_PLUGIN_VERSION=$(resolve_hook_plugin_version)

deny_reason_with_marker() {
  local base="$1" dir="$2" marker step
  marker="$dir/.bg-wait-active"
  step=$(marker_value "$marker" STEP 2>/dev/null || printf '%s' unknown)
  printf '%s marker=%s STEP=%s hook_version=%s' "$base" "$marker" "$step" "$HOOK_PLUGIN_VERSION"
}

emit_deny_json() {
  local reason escaped
  reason="$1"
  escaped=$(json_escape "$reason")
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$escaped"
}

json_deny_probe() {
  local dir="$1" reason
  # #5610: emit deny JSON with a static printf string, not jq -cn ... || true. jq is still
  # required to parse the hook input up front, but a jq runtime failure at this final emit
  # point must not silently swallow the deny signal.
  reason=$(deny_reason_with_marker 'Repeated foreground terminal-sentinel probes while the sentinel is still absent. These are spurious empty-output <task-notification> turns (#5240, #5478): end the turn without probing and wait for a <task-notification> with new non-empty content. The guard clears once the sentinel appears.' "$dir")
  emit_deny_json "$reason"
}

json_deny_monitor() {
  local dir="$1" reason
  # Deny Monitor and TaskOutput tool calls while any immediate-background wait is active.
  # Arming Monitor during a background wait is the primary amplifier of premature
  # notification storms (BC8DDA64: 7 Monitors armed, 40 "still waiting" turns). Static
  # printf — not jq — so a jq failure cannot swallow the deny.
  reason=$(deny_reason_with_marker 'An immediate-background wait is active. Do not arm Monitor or poll TaskOutput during a background wait; end the turn and wait for <task-notification>.' "$dir")
  emit_deny_json "$reason"
}

json_deny_task_output_read() {
  local dir="$1" reason
  reason=$(deny_reason_with_marker 'The classification Read of tasks/*.output is unchanged or empty during a live /design or /implement background wait. End the turn now with no prose, no tools, and no retry until the next <task-notification>.' "$dir")
  emit_deny_json "$reason"
}

arm_no_progress_task_output_clamp() {
  local dir="$1"
  [ -n "$dir" ] || return 0
  : >"$dir/no-progress-task-output-clamped" 2>/dev/null || return 0
  : >"$dir/no-progress-circuit-breaker-armed" 2>/dev/null || true
  rm -f "$dir/no-progress-turns.count" 2>/dev/null || true
}

clear_no_progress_task_output_clamp() {
  local dir="$1"
  [ -n "$dir" ] || return 0
  if [ -e "$dir/no-progress-task-output-clamped" ] && [ ! -L "$dir/no-progress-task-output-clamped" ]; then
    rm -f \
      "$dir/no-progress-task-output-clamped" \
      "$dir/no-progress-circuit-breaker-armed" \
      "$dir/no-progress-stop-block-emitted" \
      "$dir/no-progress-turns.count" \
      2>/dev/null || true
  else
    rm -f "$dir/no-progress-task-output-clamped" 2>/dev/null || true
  fi
}

task_output_read_clamp() {
  local read_abs="$1" task_id="$2" dir step sig bump class count
  [ -n "$task_id" ] || return 1
  sig=$(task_output_file_signature "$read_abs") || return 1
  while IFS='|' read -r dir step || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    case "$step" in
      design-step*|implement-step*) ;;
      *) continue ;;
    esac
    bump=$(task_output_read_bump "$dir" "$task_id" "$sig") || return 1
    IFS=$'\t' read -r class count <<EOF_BUMP
$bump
EOF_BUMP
    case "$count" in ''|*[!0-9]*) return 1 ;; esac
    if [ "$count" -gt "$TASK_OUTPUT_READ_THRESHOLD" ]; then
      arm_no_progress_task_output_clamp "$dir"
      json_deny_task_output_read "$dir"
      exit 0
    fi
    clear_no_progress_task_output_clamp "$dir"
    return 0
  done <"$live_markers_file"
  return 1
}

terminal_sentinel_probe_clamp() {
  # Entered only after bash_is_terminal_sentinel_foreground_probe matched. Allows the
  # probe up to the threshold per absent sentinel, then denies until the sentinel
  # appears. Fails open (allow) when the sentinel name cannot be resolved. Always
  # exits the hook.
  local cmd="$1" name dir counter cnt sentinel_present=0 over_threshold=0
  name=$(probe_sentinel_name "$cmd") || exit 0
  dir=$(probe_target_live_dir "$cmd") || exit 0
  if [ -e "$dir/.completed/$name" ] && [ ! -L "$dir/.completed/$name" ]; then
    rm -f "$(probe_counter_file "$dir" "$name")" 2>/dev/null || true
    sentinel_present=1
  else
    counter=$(probe_counter_file "$dir" "$name")
    cnt=$(probe_counter_bump "$counter")
    if [ "$cnt" -gt "$PROBE_CLAMP_THRESHOLD" ]; then
      over_threshold=1
    fi
  fi
  if [ "$sentinel_present" -eq 0 ] && [ "$over_threshold" -eq 1 ]; then
    json_deny_probe "$dir"
  fi
  exit 0
}

implement_terminal_sentinel_probe_clamp() {
  # Entered only after bash_is_implement_terminal_sentinel_foreground_probe matched.
  # Reuses the per-sentinel clamp for the narrow Step 3/5 post-denial recovery path.
  local cmd="$1" name dir counter cnt sentinel_present=0 over_threshold=0
  name=$(probe_sentinel_name "$cmd") || exit 0
  dir=$(probe_target_live_dir_implement_step35 "$cmd") || exit 0
  if [ -f "$dir/.completed/$name" ] && [ ! -L "$dir/.completed/$name" ]; then
    rm -f "$(probe_counter_file "$dir" "$name")" 2>/dev/null || true
    sentinel_present=1
  else
    counter=$(probe_counter_file "$dir" "$name")
    cnt=$(probe_counter_bump "$counter")
    if [ "$cnt" -gt "$PROBE_CLAMP_THRESHOLD" ]; then
      over_threshold=1
    fi
  fi
  if [ "$sentinel_present" -eq 0 ] && [ "$over_threshold" -eq 1 ]; then
    json_deny_probe "$dir"
  fi
  exit 0
}

marker_is_live() {
  local marker="$1" dir pid start timeout age limit grace step
  [ -f "$marker" ] || return 1
  [ ! -L "$marker" ] || return 1
  dir=$(dirname "$marker") || return 2
  dir=$(canonical_dir "$dir" 2>/dev/null) || return 2
  is_allowed_marker_parent "$dir" || return 1
  # #5684: liveness is NOT scoped by CLAUDE_PID. In production the hook's PPID and
  # input never match the marker's stored CLAUDE_PID (hook input carries no claude_pid,
  # LARCH_BG_POLL_GUARD_SESSION_PID is unset outside tests), so the old equality check
  # rejected every marker and the guard never fired. Session isolation comes from the
  # per-session tmpdir under ~/.cache/larch/sessions/ plus the kill -0 PID-liveness and
  # age checks below. The marker's CLAUDE_PID field is retained as debug metadata only.
  step=$(marker_value "$marker" STEP 2>/dev/null) || step=""
  if marker_step_completed "$dir" "$step"; then
    reset_probe_counter_for_step "$dir" "$step"
    reset_task_output_read_state "$dir"
    return 1
  fi
  pid=$(marker_value "$marker" PID) || return 2
  start=$(marker_value "$marker" START_EPOCH) || return 2
  timeout=$(marker_value "$marker" TIMEOUT_S) || return 2
  case "$pid" in ''|*[!0-9]*) return 2 ;; esac
  case "$start" in ''|*[!0-9]*) return 2 ;; esac
  case "$timeout" in ''|*[!0-9]*) return 2 ;; esac
  kill -0 "$pid" 2>/dev/null || { rm -f "$marker" 2>/dev/null || true; reset_probe_counter_for_step "$dir" "$step"; reset_task_output_read_state "$dir"; return 1; }
  grace=60
  limit=$((timeout + grace))
  age=$((now - start))
  if [ "$age" -lt 0 ]; then
    return 2
  fi
  if [ "$age" -gt "$limit" ]; then
    rm -f "$marker" 2>/dev/null || true
    reset_probe_counter_for_step "$dir" "$step"
    reset_task_output_read_state "$dir"
    return 1
  fi
  LIVE_MARKER_DIR="$dir"
  LIVE_MARKER_STEP="$step"
  return 0
}

json_deny() {
  local dir="$1" reason
  # #5610: emit deny JSON with a static printf string, not jq -cn ... || true, so a jq
  # runtime failure at the final emit point cannot silently swallow the deny signal. jq is
  # still required to parse the hook input up front (the hook fails open when jq is absent).
  reason=$(deny_reason_with_marker 'An immediate-background wait is active. End the turn and wait for <task-notification>; do not poll progress artifacts.' "$dir")
  emit_deny_json "$reason"
}

increment_denial_count() {
  local dir="$1" count_file old tmp
  count_file="$dir/bg-poll-guard-denials.count"
  old=0
  if [ -f "$count_file" ] && [ ! -L "$count_file" ]; then
    old=$(awk 'NR==1 { print; exit }' "$count_file" 2>/dev/null || printf '0')
    case "$old" in ''|*[!0-9]*) old=0 ;; esac
  fi
  tmp="$count_file.tmp.$$"
  printf '%s\n' $((old + 1)) >"$tmp" 2>/dev/null || { rm -f "$tmp" 2>/dev/null || true; return 1; }
  mv -f "$tmp" "$count_file" 2>/dev/null || { rm -f "$tmp" 2>/dev/null || true; return 1; }
  return 0
}

deny_if_needed() {
  local dir="$1"
  json_deny "$dir"
  increment_denial_count "$dir" || true
  exit 0
}

path_under_dir() {
  local path="$1" dir="$2"
  [ -n "$path" ] || return 1
  while [[ "$path" == *//* ]]; do path=${path//\/\//\/}; done
  while [[ "$dir" == *//* ]]; do dir=${dir//\/\//\/}; done
  case "$path" in
    "$dir"|"$dir"/*) return 0 ;;
  esac
  case "$dir" in
    /private/*)
      local dir_unprivate="${dir#/private}"
      case "$path" in "$dir_unprivate"|"$dir_unprivate"/*) return 0 ;; esac
      ;;
  esac
  return 1
}

path_same_dir_alias() {
  local path="$1" dir="$2"
  [ -n "$path" ] || return 1
  [ -n "$dir" ] || return 1
  while [[ "$path" == *//* ]]; do path=${path//\/\//\/}; done
  while [[ "$dir" == *//* ]]; do dir=${dir//\/\//\/}; done
  [ "$path" = "$dir" ] && return 0
  case "$dir" in
    /private/*) [ "$path" = "${dir#/private}" ] && return 0 ;;
    *) [ "$path" = "/private$dir" ] && return 0 ;;
  esac
  return 1
}

path_is_known_result() {
  case "$(basename "$1" 2>/dev/null)" in
    .step3-review-result.env|.design-publish-result.env|final-summary.md) return 0 ;;
  esac
  return 1
}

path_is_bg_wait_marker() {
  case "$(basename "$1" 2>/dev/null)" in
    .bg-wait-active) return 0 ;;
  esac
  return 1
}

_PROBE_VERB_RE='(ls|cat|wc|stat|find|head|tail|test|grep|rg|ripgrep|awk|sed|python3?|jq|dd|cmp)'

bash_trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

bash_first_sync_segment() {
  local cmd="$1" rest ch in_s in_d seg
  in_s=0
  in_d=0
  seg=""
  rest="$cmd"
  while [ -n "$rest" ]; do
    ch=${rest:0:1}
    case "$ch" in
      \') [ "$in_d" -eq 0 ] && in_s=$((1 - in_s)) ;;
      \") [ "$in_s" -eq 0 ] && in_d=$((1 - in_d)) ;;
    esac
    if [ "$in_s" -eq 0 ] && [ "$in_d" -eq 0 ]; then
      case "$rest" in
        '&&'*|'||'*|';'*)
          bash_trim "$seg"
          return 0
          ;;
      esac
    fi
    seg="$seg$ch"
    rest="${rest:1}"
  done
  bash_trim "$seg"
}

bash_segment_is_wrapper_routed() {
  local seg="$1"
  case "$seg" in
    *design-run-*.sh*design-step3-review.sh*|*design-run-*.sh*design-step5c.sh*|*design-run-*.sh*design-step-final-summary.sh*) return 0 ;;
  esac
  return 1
}

bash_is_strict_wrapper_only() {
  local cmd="$1" first rest
  first=$(bash_first_sync_segment "$cmd")
  bash_segment_is_wrapper_routed "$first" || return 1
  rest="$cmd"
  rest="${rest#"$first"}"
  rest="${rest#"${rest%%[![:space:]]*}"}"
  case "$rest" in
    '') return 0 ;;
    '&&'*|'||'*|';'*) return 1 ;;
    *) return 1 ;;
  esac
}

bash_is_step3_recovery_waiter() {
  local cmd="$1" normalized
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  case "$normalized" in
    *.step3-review-result.env*|*'&&'*|*'||'*) return 1 ;;
  esac
  if bash_has_probe_verb "$normalized"; then
    return 1
  fi
  # #4725: this matcher now drives a DENY at the call site (it previously allowed
  # the waiter). The bare background sleep-loop waiter amplifies premature
  # notifications, so it is blocked; the orchestrator must use the foreground,
  # non-sleeping terminal-sentinel probe instead.
  # #4489: still match an optional leading `DESIGN_TMPDIR=<abs>;` assignment. Bash
  # tool calls do not persist $DESIGN_TMPDIR; the bare `until` form also matches
  # when the variable is already exported. The `&&`/`||` and probe-verb guards
  # above keep compound or probing tails from matching this exact-waiter shape;
  # those route through the generic deny loop below instead.
  # shellcheck disable=SC2016 # Match literal $DESIGN_TMPDIR in the candidate Bash command.
  printf '%s' "$normalized" | grep -Eq '^(DESIGN_TMPDIR=[^;]+;[[:space:]]*)?until[[:space:]]+\[[[:space:]]+-f[[:space:]]+"?(\$DESIGN_TMPDIR/\.completed/step-3-terminal|\$\{DESIGN_TMPDIR\}/\.completed/step-3-terminal)"?[[:space:]]+\];[[:space:]]+do[[:space:]]+sleep[[:space:]]+[0-9]+[[:space:]]*;[[:space:]]+done$'
}

bash_is_terminal_sentinel_foreground_probe() {
  local cmd="$1" normalized sentinel_path sentinel_name sentinel_abs target_dir
  local probe_target_re test_re bracket_re
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  bash_is_control_loop "$normalized" && return 1
  printf '%s' "$normalized" | grep -Eq '(^|[^[:alnum:]_])sleep([^[:alnum:]_]|$)' && return 1
  case "$normalized" in
    *.step3-review-result.env*|*.design-publish-result.env*|*final-summary.md*|*plan-review/*|*tasks/*.output*) return 1 ;;
    *.completed/step-3\"*|*.completed/step-3\'*|*.completed/step-3[[:space:]]*|*.completed/step-3.5\"*|*.completed/step-3.5\'*|*.completed/step-3.5[[:space:]]*|*.completed/step-5c\"*|*.completed/step-5c\'*|*.completed/step-5c[[:space:]]*) return 1 ;;
  esac
  # shellcheck disable=SC2016 # Match literal $DESIGN_TMPDIR in the candidate Bash command.
  probe_target_re='(\$DESIGN_TMPDIR/\.completed/(step-3-terminal|step-4|step-5c-terminal|step-final-summary)|\$\{DESIGN_TMPDIR\}/\.completed/(step-3-terminal|step-4|step-5c-terminal|step-final-summary))'
  test_re='^(DESIGN_TMPDIR=[^;]+;[[:space:]]*)?test[[:space:]]+-f[[:space:]]+"?'"$probe_target_re"'"?( && echo DONE \|\| echo WAIT)?$'
  bracket_re='^(DESIGN_TMPDIR=[^;]+;[[:space:]]*)?(\[\[|\[)[[:space:]]+-f[[:space:]]+"?'"$probe_target_re"'"?[[:space:]]+(\]\]|\])( && echo DONE \|\| echo WAIT)?$'
  if printf '%s' "$normalized" | grep -Eq "$test_re"; then
    :
  elif printf '%s' "$normalized" | grep -Eq "$bracket_re"; then
    :
  else
    return 1
  fi
  target_dir=$(probe_target_live_dir "$normalized") || return 1
  # shellcheck disable=SC2016 # Match literal $DESIGN_TMPDIR in the candidate Bash command.
  sentinel_path=$(printf '%s' "$normalized" | sed -E 's/.*(\$DESIGN_TMPDIR|\$\{DESIGN_TMPDIR\})\/\.completed\/(step-3-terminal|step-4|step-5c-terminal|step-final-summary).*/\2/')
  sentinel_name="$sentinel_path"
  [ -n "$sentinel_name" ] || return 1
  terminal_sentinel_allowed_for_live_step "$target_dir" "$sentinel_name" || return 1
  sentinel_abs="$target_dir/.completed/$sentinel_name"
  if [ -L "$sentinel_abs" ]; then
    return 1
  fi
  return 0
}

bash_attempts_terminal_sentinel_mutation() {
  local cmd="$1"
  case "$cmd" in
    *step-3-terminal*|*step-4*|*step-5c-terminal*|*step-5-terminal*|*step-final-summary*|*step3-terminal-persisted-this-run*|*step-8-ship-handoff.rc*) ;;
    *) return 1 ;;
  esac
  printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_])(touch|mkdir|cp|mv|ln|tee|install)([^[:alnum:]_]|$)|:[[:space:]]*>|(^|[^[:alnum:]_])echo[^|]*>|(^|[^[:alnum:]_])printf[^|]*>|>[[:space:]]' && return 0
  return 1
}

bash_has_probe_verb() {
  printf '%s' "$1" | grep -Eq "(^|[^[:alnum:]_])${_PROBE_VERB_RE}([^[:alnum:]_]|$)"
}

bash_has_bracket_file_test() {
  printf '%s' "$1" | tr '\n' ' ' | grep -Eq '(^|[;&|[:space:]])(\[\[|\[)[[:space:]]+!?[[:space:]]*-f[[:space:]]+'
}

bash_split_shell_command() {
  python3 - "$1" <<'PY'
import shlex
import sys

try:
    tokens = shlex.split(sys.argv[1], posix=True, comments=True)
except ValueError:
    raise SystemExit(1)

for token in tokens:
    print(token)
PY
}

bash_is_marker_only_diagnosis() {
  local cmd="$1" normalized verb token non_option_count=0 marker_count=0 marker_token="" joined
  local -a tokens=()
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  case "$normalized" in
    *.bg-wait-active*) ;;
    *) return 1 ;;
  esac
  tokens_text=$(bash_split_shell_command "$normalized") || return 1
  while IFS= read -r token || [ -n "$token" ]; do
    tokens+=("$token")
  done <<EOF_TOKENS
$tokens_text
EOF_TOKENS
  [ "${#tokens[@]}" -gt 0 ] || return 1
  # Reject on the comment-stripped, dequoted token text: a disallowed
  # reference inside a trailing shell comment is inert in real bash and
  # must not trigger a false deny.
  joined="${tokens[*]}"
  case "$joined" in
    *tasks/*.output*|*.completed/*|*.step3-review-result.env*|*.design-publish-result.env*|*final-summary.md*|*plan-review/*|*.step-8-ship-handoff.*) return 1 ;;
    *';'*|*'&&'*|*'||'*|*'|'*|*'`'*) return 1 ;;
  esac
  printf '%s' "$joined" | grep -Fq "\$(" && return 1
  printf '%s' "$joined" | grep -Eq '(^|[^[:alnum:]_])(touch|mkdir|cp|mv|ln|tee|install|rm|truncate)([^[:alnum:]_]|$)|:[[:space:]]*>|(^|[^[:alnum:]_])echo[^|]*>|(^|[^[:alnum:]_])printf[^|]*>|>[[:space:]]' && return 1
  verb="${tokens[0]}"
  case "$verb" in
    cat|stat|ls|wc|head|sed|awk) ;;
    *) return 1 ;;
  esac
  for token in "${tokens[@]:1}"; do
    case "$token" in
      -*) continue ;;
    esac
    non_option_count=$((non_option_count + 1))
    case "$(basename "$token" 2>/dev/null)" in
      .bg-wait-active)
        marker_count=$((marker_count + 1))
        marker_token="$token"
        ;;
      *)
        case "$verb" in
          cat|stat|ls|wc|head) return 1 ;;
        esac
        ;;
    esac
  done
  case "$verb" in
    cat|stat|ls|wc|head)
      [ "$non_option_count" -eq 1 ] || return 1
      ;;
    sed|awk)
      [ "$non_option_count" -eq 2 ] || return 1
      ;;
  esac
  [ "$marker_count" -eq 1 ] || return 1
  [ -n "$marker_token" ] || return 1
  while IFS= read -r live_dir || [ -n "$live_dir" ]; do
    [ -n "$live_dir" ] || continue
    if path_under_dir "$marker_token" "$live_dir" && path_is_bg_wait_marker "$marker_token"; then
      return 0
    fi
  done <"$live_dirs_file"
  return 1
}


bash_bare_live_dir_only() {
  local cmd="$1" normalized tokens_text token live_dir
  local -a tokens=()
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  normalized=$(bash_trim "$normalized")
  [ -n "$normalized" ] || return 1
  tokens_text=$(bash_split_shell_command "$normalized") || return 1
  while IFS= read -r token || [ -n "$token" ]; do
    tokens+=("$token")
  done <<EOF_TOKENS
$tokens_text
EOF_TOKENS
  [ "${#tokens[@]}" -eq 1 ] || return 1
  token="${tokens[0]}"
  case "$token" in
    /*) ;;
    *) return 1 ;;
  esac
  while IFS= read -r live_dir || [ -n "$live_dir" ]; do
    [ -n "$live_dir" ] || continue
    if path_same_dir_alias "$token" "$live_dir"; then
      printf '%s' "$live_dir"
      return 0
    fi
  done <"$live_dirs_file"
  return 1
}


bash_clone_tag_from_basename() {
  # Mirrors _make_session_tmpdir()'s clone_tag derivation in
  # python/larch/state/session_env.py: replace any byte outside
  # [A-Za-z0-9_-] with `_`, keep at most the first 32 characters, and fall
  # back to `_` when the sanitized result is empty.
  local name="$1" tag
  tag=$(printf '%s' "$name" | sed -E 's/[^A-Za-z0-9_-]/_/g')
  tag="${tag:0:32}"
  printf '%s' "${tag:-_}"
}

bash_marker_clone_tag() {
  # Extracts the clone-tag segment from a live marker directory's basename,
  # e.g. claude-implement-larch2-forj_flt -> larch2. The tag itself may
  # contain hyphens (the sanitizer allows them through), so this strips the
  # known literal skill prefix from the front and the fixed 8-character
  # mkdtemp random suffix from the back, rather than splitting on "-".
  local base="$1" rest
  case "$base" in
    claude-implement-*) rest="${base#claude-implement-}" ;;
    claude-design-*) rest="${base#claude-design-}" ;;
    *) return 1 ;;
  esac
  case "$rest" in
    ?*-????????) printf '%s' "${rest%-????????}"; return 0 ;;
  esac
  return 1
}

bash_probe_target_dir_plausible() {
  # #5925: a bare, unexpanded $DESIGN_TMPDIR/$IMPLEMENT_TMPDIR/$SESSION_TMPDIR
  # reference in a command's literal text is not, by itself, evidence the
  # command targets this specific dir. At actual runtime that reference
  # expands to whichever session's own env var happens to be set, which the
  # hook cannot observe directly (#5684: hook input carries no session
  # identifier). Prefer the marker's .larch-keepalive CLONE_PATH identity;
  # when it is unavailable, fall back to the older cwd-basename/session-tag
  # heuristic. The keepalive path handles repo subdirectory cwds without the
  # same-basename collision accepted by the fallback heuristic.
  local dir="$1" cwd_canon="$2" marker_tag cwd_tag marker_canon
  [ -n "$dir" ] || return 1
  if [ -n "$cwd_canon" ] && [ "$cwd_canon" = "$dir" ]; then
    return 0
  fi
  [ -n "$cwd_canon" ] || return 1
  if marker_canon=$(marker_clone_identity_canon "$dir" 2>/dev/null); then
    clone_paths_same "$marker_canon" "$cwd_canon" && return 0
    return 1
  fi
  marker_tag=$(bash_marker_clone_tag "$(basename "$dir")") || return 1
  cwd_tag=$(bash_clone_tag_from_basename "$(basename "$cwd_canon")")
  [ -n "$cwd_tag" ] && [ "$cwd_tag" = "$marker_tag" ]
}


bash_has_probe_target() {
  # #5925: the six generic tmpdir-variable-name alternatives below used to
  # match unconditionally, so ANY live marker anywhere on the machine (e.g.
  # an unrelated /design session in a different repo clone) satisfied this
  # check for every command merely mentioning "$IMPLEMENT_TMPDIR" or
  # "$DESIGN_TMPDIR" literally, which is how virtually every /implement and
  # /design Bash fence is written. They now require
  # bash_probe_target_dir_plausible evidence that the reference actually
  # correlates to this dir. *"$dir"* stays unconditional because it is already
  # dir-specific; tasks/*.output is also clone-gated because it is not tied to
  # the marker tmpdir path text.
  local cmd="$1" dir="$2" cwd_canon="$3"
  local design_tmpdir_ref="\$DESIGN_TMPDIR"
  local design_tmpdir_braced="\${DESIGN_TMPDIR}"
  local session_tmpdir_ref="\$SESSION_TMPDIR"
  local session_tmpdir_braced="\${SESSION_TMPDIR}"
  local implement_tmpdir_ref="\$IMPLEMENT_TMPDIR"
  local implement_tmpdir_braced="\${IMPLEMENT_TMPDIR}"
  case "$cmd" in
    *"$dir"*) return 0 ;;
  esac
  case "$dir" in
    /private/*)
      case "$cmd" in *"${dir#/private}"*) return 0 ;; esac
      ;;
    *)
      case "$cmd" in *"/private$dir"*) return 0 ;; esac
      ;;
  esac
  case "$cmd" in
    *tasks/*.output*|*"$design_tmpdir_ref"*|*"$design_tmpdir_braced"*|*"$session_tmpdir_ref"*|*"$session_tmpdir_braced"*|*"$implement_tmpdir_ref"*|*"$implement_tmpdir_braced"*)
      bash_probe_target_dir_plausible "$dir" "$cwd_canon" && return 0
      ;;
  esac
  if [ -n "$cwd_canon" ] && [ "$cwd_canon" = "$dir" ]; then
    case "$cmd" in
      *.step3-review-result.env*|*.design-publish-result.env*|*final-summary.md*|*plan-review/*|**-output.txt*|*tasks/*.output*|*.step-8-ship-handoff.rc*) return 0 ;;
    esac
  fi
  return 1
}

bash_is_sleep_probe() {
  local cmd="$1"
  printf '%s' "$cmd" | tr '\n' ' ' | grep -Eq "sleep[[:space:]]+[0-9]+[^&;|]*&&[^\\n]*${_PROBE_VERB_RE}"
}

bash_is_watcher_loop() {
  local cmd="$1"
  printf '%s' "$cmd" | tr '\n' ' ' | grep -Eq "(while|until|for)[[:space:]].*sleep[[:space:]]+[0-9]+.*${_PROBE_VERB_RE}"
}

bash_is_control_loop() {
  local cmd="$1"
  printf '%s' "$cmd" | tr '\n' ' ' | grep -Eq "(^|[^[:alnum:]_])(while|until|for)([^[:alnum:]_]|$)"
}

bash_is_filetest_sleep_loop() {
  local cmd="$1"
  printf '%s' "$cmd" | tr '\n' ' ' | grep -Eq '(while|until)[[:space:]].*(\[|\[\[).*(sleep|;).*sleep[[:space:]]+[0-9]+|(while|until)[[:space:]].*sleep[[:space:]]+[0-9]+.*(\[|\[\[)'
}

live_dirs_file=$(mktemp "${TMPDIR:-/tmp}/larch-bg-poll-live.XXXXXX") || exit 0
live_markers_file=$(mktemp "${TMPDIR:-/tmp}/larch-bg-poll-live-steps.XXXXXX") || { rm -f "$live_dirs_file" 2>/dev/null || true; exit 0; }
trap 'rm -f "$live_dirs_file" "$live_markers_file"' EXIT

while IFS= read -r marker || [ -n "$marker" ]; do
  [ -n "$marker" ] || continue
  LIVE_MARKER_DIR=""
  LIVE_MARKER_STEP=""
  marker_is_live "$marker"
  marker_rc=$?
  case "$marker_rc" in
    0)
      if marker_foreign_clone "$LIVE_MARKER_DIR" "$cwd_canon"; then
        continue
      fi
      printf '%s\n' "$LIVE_MARKER_DIR" >>"$live_dirs_file"
      printf '%s|%s\n' "$LIVE_MARKER_DIR" "$LIVE_MARKER_STEP" >>"$live_markers_file"
      ;;
    1|2) ;;
    *) exit 0 ;;
  esac
done <<EOF_MARKERS
$(marker_candidates)
EOF_MARKERS

[ -s "$live_dirs_file" ] || exit 0

# Monitor and TaskOutput are denied only while an immediate-background wait owned by THIS
# repo clone is live. #5925 follow-up: the deny was previously unconditional on any live
# marker anywhere on the machine, so a foreign clone's live marker denied this session's
# Monitor/TaskOutput calls (cross-clone false positive, same class as #5925/#5927). It also
# stalled a session that read its own just-completed bg task output while another clone had
# a live wait. bash_probe_target_dir_plausible gates on cwd<->marker clone-tag correlation,
# mirroring the Bash-probe paths below; when cwd cannot be correlated the call is allowed
# rather than falsely blocking an unrelated clone. Arming Monitor to watch a bg fence is the
# primary amplifier of premature-notification storms; TaskOutput polling during a wait
# creates the same re-engagement loop, so the in-clone case still denies.
case "$tool_name" in
  Monitor|TaskOutput)
    while IFS= read -r dir || [ -n "$dir" ]; do
      [ -n "$dir" ] || continue
      bash_probe_target_dir_plausible "$dir" "$cwd_canon" || continue
      json_deny_monitor "$dir"
      increment_denial_count "$dir" || true
      exit 0
    done <"$live_dirs_file"
    exit 0
    ;;
esac

if [ "$tool_name" = "Read" ]; then
  read_path=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
  [ -n "$read_path" ] || exit 0
  case "$read_path" in
    /*) read_abs="$read_path" ;;
    *)
      if [ -n "$cwd_canon" ]; then read_abs="$cwd_canon/$read_path"; else read_abs="$read_path"; fi
      ;;
  esac
  if path_is_bg_wait_marker "$read_abs"; then
    exit 0
  fi
  if task_id=$(read_task_output_id "$read_abs" 2>/dev/null); then
    task_output_read_clamp "$read_abs" "$task_id" || true
  fi
  while IFS= read -r dir || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    # Allow Read of tasks/*.output while a live same-clone wait marker exists.
    # The task-output file is the write-once classification artifact used after
    # a <task-notification>; Bash probes and TaskOutput remain denied elsewhere.
    if path_under_dir "$read_abs" "$dir" || { path_is_known_result "$read_path" && { path_under_dir "$read_abs" "$dir" || [ "$cwd_canon" = "$dir" ]; }; }; then
      deny_if_needed "$dir"
    fi
  done <"$live_dirs_file"
  exit 0
fi

cmd=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -n "$cmd" ] || exit 0
bash_is_strict_wrapper_only "$cmd" && exit 0
bash_is_marker_only_diagnosis "$cmd" && exit 0
if bare_live_dir=$(bash_bare_live_dir_only "$cmd"); then
  deny_if_needed "$bare_live_dir"
fi
# #4725: the background sleep-loop Step 3 recovery waiter is itself a zero-output
# background task, so it fires its own premature <task-notification> within
# seconds and breeds a re-engagement loop. Deny it (it used to be allowed here),
# forcing the foreground, non-sleeping terminal-sentinel probe path that stays
# allowed just below. deny_if_needed exits 0 after the first live marker dir.
if bash_is_step3_recovery_waiter "$cmd"; then
  while IFS= read -r dir || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    deny_if_needed "$dir"
  done <"$live_dirs_file"
fi
if bash_is_terminal_sentinel_foreground_probe "$cmd"; then
  terminal_sentinel_probe_clamp "$cmd"
fi
if bash_is_implement_terminal_sentinel_foreground_probe "$cmd"; then
  implement_terminal_sentinel_probe_clamp "$cmd"
fi
if bash_is_step8_handoff_foreground_probe "$cmd"; then
  step8_handoff_probe_clamp "$cmd"
fi
while IFS= read -r dir || [ -n "$dir" ]; do
  [ -n "$dir" ] || continue
  if bash_has_probe_verb "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_has_bracket_file_test "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_is_sleep_probe "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_is_watcher_loop "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_is_control_loop "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_is_filetest_sleep_loop "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
  if bash_attempts_terminal_sentinel_mutation "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"; then
    deny_if_needed "$dir"
  fi
done <"$live_dirs_file"

exit 0
