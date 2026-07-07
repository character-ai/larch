#!/usr/bin/env bash
# hook-no-progress-guard.sh — Stop + UserPromptSubmit hook: universal no-progress circuit breaker.
#
# Stop event: counts this turn for every live bg-wait marker. When a marker's consecutive-turn
# count reaches LARCH_NO_PROGRESS_GUARD_THRESHOLD (default 3), arms a circuit-breaker flag in
# that marker directory and emits a one-shot Stop block. This catches prose-only no-progress
# turns that make no tool calls and are invisible to the PreToolUse probe-clamp in
# hook-bg-poll-guard.sh.
#
# UserPromptSubmit event: fallback path for an already armed circuit breaker. Auto-disarms when
# the bg task completes (marker gone or its terminal sentinel present), so a genuine completion
# notification is never blocked.
#
# set -e intentionally omitted: hooks must fail open on malformed input or runtime errors.

set -uo pipefail

[ "${LARCH_NO_PROGRESS_GUARD_DISABLE:-}" = "1" ] && exit 0

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

# Detect event type. Modern Claude Code payloads include event_type; fall back to key inspection.
event_type=$(printf '%s' "$INPUT" | jq -r '.event_type // ""' 2>/dev/null) || event_type=""
case "$event_type" in
  Stop|UserPromptSubmit) ;;
  "")
    if printf '%s' "$INPUT" | jq -e 'has("stop_hook_active")' >/dev/null 2>&1; then
      event_type="Stop"
    elif printf '%s' "$INPUT" | jq -e 'has("prompt")' >/dev/null 2>&1; then
      event_type="UserPromptSubmit"
    else
      exit 0
    fi
    ;;
  *) exit 0 ;;
esac

# Stop re-entry guard: skip when a Stop hook loop is already active.
if [ "$event_type" = "Stop" ]; then
  stop_hook_active=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // "false"' 2>/dev/null) || stop_hook_active=false
  [ "$stop_hook_active" = "true" ] && exit 0
fi

THRESHOLD="${LARCH_NO_PROGRESS_GUARD_THRESHOLD:-3}"
case "$THRESHOLD" in ''|*[!0-9]*) THRESHOLD=3 ;; esac

now=$(date +%s 2>/dev/null) || exit 0
case "$now" in ''|*[!0-9]*) exit 0 ;; esac

canonical_dir() {
  [ -n "$1" ] || return 1
  [ -d "$1" ] || return 1
  (cd "$1" 2>/dev/null && pwd -P)
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

# Same discovery logic as hook-bg-poll-guard.sh marker_candidates.
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

# Returns 0 when the step's terminal sentinel is present (task done, exit-trap pending).
# Mirrors hook-bg-poll-guard.sh marker_step_completed so a genuine completion notification
# is never blocked by the circuit breaker even if the marker has not yet been removed.
is_step_completed() {
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

reset_no_progress_state() {
  # Clear counter and armed flag once a wait completes or its marker is reaped, so a
  # later wait reusing the same tmpdir starts fresh (mirrors reset_probe_counter_for_step).
  local dir="$1"
  [ -n "$dir" ] || return 0
  rm -f \
    "$dir/no-progress-turns.count" \
    "$dir/no-progress-circuit-breaker-armed" \
    "$dir/no-progress-stop-block-emitted" \
    "$dir/no-progress-task-output-clamped" \
    2>/dev/null || true
}

# Sets LIVE_MARKER_DIR on success. Returns 0 when live, non-zero when not live.
LIVE_MARKER_DIR=""
is_marker_live() {
  local marker="$1" dir pid start timeout age limit grace step
  LIVE_MARKER_DIR=""
  if [ ! -f "$marker" ]; then
    dir=$(dirname "$marker") || return 1
    dir=$(canonical_dir "$dir" 2>/dev/null) || return 1
    reset_no_progress_state "$dir"
    return 1
  fi
  [ ! -L "$marker" ] || return 1
  dir=$(dirname "$marker") || return 1
  dir=$(canonical_dir "$dir" 2>/dev/null) || return 1
  # #5684: liveness is NOT scoped by CLAUDE_PID. In production the hook's PPID and input
  # never match the marker's stored CLAUDE_PID, so the old equality check skipped every
  # marker and this circuit breaker never armed. Session isolation comes from the
  # per-session tmpdir plus the kill -0 PID-liveness and age checks below.
  # Release guard when the step's terminal sentinel is already written.
  step=$(marker_value "$marker" STEP 2>/dev/null) || step=""
  if is_step_completed "$dir" "$step"; then
    reset_no_progress_state "$dir"
    return 1
  fi
  pid=$(marker_value "$marker" PID) || return 1
  start=$(marker_value "$marker" START_EPOCH) || return 1
  timeout=$(marker_value "$marker" TIMEOUT_S) || return 1
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  case "$start" in ''|*[!0-9]*) return 1 ;; esac
  case "$timeout" in ''|*[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null || { rm -f "$marker" 2>/dev/null || true; reset_no_progress_state "$dir"; return 1; }
  grace=60
  limit=$((timeout + grace))
  age=$((now - start))
  [ "$age" -ge 0 ] || return 1
  if [ "$age" -gt "$limit" ]; then
    rm -f "$marker" 2>/dev/null || true
    reset_no_progress_state "$dir"
    return 1
  fi
  LIVE_MARKER_DIR="$dir"
  return 0
}

# Best-effort atomic increment of no-progress-turns.count. Echoes the new count.
counter_bump() {
  local dir="$1" f old new tmp
  f="$dir/no-progress-turns.count"
  old=0
  if [ -f "$f" ] && [ ! -L "$f" ]; then
    old=$(awk 'NR==1 { print; exit }' "$f" 2>/dev/null || printf '0')
    case "$old" in ''|*[!0-9]*) old=0 ;; esac
  fi
  new=$((old + 1))
  tmp="$f.tmp.$$"
  if printf '%s\n' "$new" > "$tmp" 2>/dev/null; then
    mv -f "$tmp" "$f" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  else
    rm -f "$tmp" 2>/dev/null || true
  fi
  printf '%s' "$new"
}

counter_read() {
  local dir="$1" f v=0
  f="$dir/no-progress-turns.count"
  if [ -f "$f" ] && [ ! -L "$f" ]; then
    v=$(awk 'NR==1 { print; exit }' "$f" 2>/dev/null || printf '0')
    case "$v" in ''|*[!0-9]*) v=0 ;; esac
  fi
  printf '%s' "$v"
}

# #5610 pattern: emit block JSON via printf (not jq -cn) so a jq failure cannot swallow the signal.
# count and threshold are validated digit-only strings safe for printf %s interpolation.
json_block_prompt() {
  local count="$1" threshold="$2" dir="$3"
  printf '{"decision":"block","reason":"No-progress circuit breaker: %s consecutive turns detected under an active background-wait marker without real progress (threshold: %s turns). Marker: %s/.bg-wait-active. The harness may be delivering spurious notifications (#5639). To continue: (1) check whether the background task completed, (2) clear the stale marker files %s/no-progress-circuit-breaker-armed, %s/no-progress-turns.count, and %s/no-progress-stop-block-emitted if the task is gone, or (3) set LARCH_NO_PROGRESS_GUARD_THRESHOLD to a higher value before retrying."}\n' \
    "$count" "$threshold" "$dir" "$dir" "$dir" "$dir"
}

json_block_task_output_clamp() {
  local dir="$1"
  printf '{"decision":"block","reason":"No-progress circuit breaker: hook-bg-poll-guard.sh already clamped an unchanged or empty /design or /implement tasks/*.output classification Read under this active background-wait marker. Marker: %s/.bg-wait-active. End this task-notification turn without tools or prose until a later notification has new non-empty task output or the terminal sentinel is present. Recovery sidecars: %s/no-progress-task-output-clamped, %s/no-progress-circuit-breaker-armed, %s/no-progress-stop-block-emitted."}\n' \
    "$dir" "$dir" "$dir" "$dir"
}

task_output_clamp_armed() {
  local dir="$1" flag
  flag="$dir/no-progress-task-output-clamped"
  [ -f "$flag" ] && [ ! -L "$flag" ]
}

if [ "$event_type" = "Stop" ]; then
  # Count this turn only for live bg-wait markers owned by this repo clone. The
  # UserPromptSubmit block below is already clone-scoped (#5927); scoping the
  # counter the same way makes "N consecutive turns" mean N turns in the owning
  # clone, not N Stop events summed across every concurrent clone. Otherwise an
  # unrelated clone's slow-but-live wait arms this marker's breaker from other
  # sessions' turn activity, and the owning clone then blocks its own next prompt
  # (#5927 follow-up). marker_foreign_clone skips only when the marker's clone
  # identity is known and differs, so a marker with no/unparsable .larch-keepalive
  # still counts and the owning session's breaker is never weakened.
  cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
  cwd_canon=""
  [ -n "$cwd" ] && cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
  while IFS= read -r marker || [ -n "$marker" ]; do
    [ -n "$marker" ] || continue
    is_marker_live "$marker" || continue
    dir="$LIVE_MARKER_DIR"
    marker_foreign_clone "$dir" "$cwd_canon" && continue
    if task_output_clamp_armed "$dir"; then
      touch "$dir/no-progress-circuit-breaker-armed" 2>/dev/null || true
      : >"$dir/no-progress-stop-block-emitted" 2>/dev/null || true
      rm -f "$dir/no-progress-turns.count" 2>/dev/null || true
      json_block_task_output_clamp "$dir"
      exit 0
    fi
    cnt=$(counter_bump "$dir")
    if [ "$cnt" -ge "$THRESHOLD" ]; then
      touch "$dir/no-progress-circuit-breaker-armed" 2>/dev/null || true
      if [ ! -f "$dir/no-progress-stop-block-emitted" ] && [ ! -L "$dir/no-progress-stop-block-emitted" ]; then
        if : >"$dir/no-progress-stop-block-emitted" 2>/dev/null; then
          json_block_prompt "$cnt" "$THRESHOLD" "$dir"
          rm -f "$dir/no-progress-turns.count" 2>/dev/null || true
          exit 0
        fi
      fi
    fi
  done <<EOF_MARKERS
$(marker_candidates)
EOF_MARKERS
  exit 0
fi

if [ "$event_type" = "UserPromptSubmit" ]; then
  cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
  cwd_canon=""
  [ -n "$cwd" ] && cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
  # Block the new turn if any live marker has an armed circuit breaker and the
  # marker cannot be proven to belong to a different repo clone (#5927).
  while IFS= read -r marker || [ -n "$marker" ]; do
    [ -n "$marker" ] || continue
    is_marker_live "$marker" || continue
    dir="$LIVE_MARKER_DIR"
    if [ -f "$dir/no-progress-circuit-breaker-armed" ] && [ ! -L "$dir/no-progress-circuit-breaker-armed" ]; then
      marker_foreign_clone "$dir" "$cwd_canon" && continue
      count=$(counter_read "$dir")
      json_block_prompt "$count" "$THRESHOLD" "$dir"
      exit 0
    fi
  done <<EOF_MARKERS
$(marker_candidates)
EOF_MARKERS
  exit 0
fi

exit 0
