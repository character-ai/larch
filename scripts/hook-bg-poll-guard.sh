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

marker_step_completed() {
  # Returns 0 when the immediate-background step named by the marker's STEP
  # value has already written its terminal completion sentinel. Used to release
  # the poll guard when a <task-notification> arrives in the same turn as the
  # launch ack and the bg process has not yet run its EXIT-trap marker cleanup
  # (#4431, #4450). Race-free: each step writes its sentinel before the task
  # process exits on terminal paths, and exits before the notification fires.
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
# keyed per sentinel basename so Step 3 (step-3-terminal) and Step 5c
# (step-5c-terminal) waits in one tmpdir cannot contaminate each other, and it clears
# when the sentinel becomes present.
PROBE_CLAMP_THRESHOLD="${LARCH_BG_POLL_GUARD_PROBE_THRESHOLD:-2}"
case "$PROBE_CLAMP_THRESHOLD" in ''|*[!0-9]*) PROBE_CLAMP_THRESHOLD=2 ;; esac

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

probe_sentinel_name() {
  # Extract the terminal sentinel basename from a command already matched as a
  # foreground probe. Returns non-zero when no known sentinel is present.
  local cmd="$1" normalized name
  normalized=$(printf '%s' "$cmd" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g')
  name=$(printf '%s' "$normalized" | sed -E 's#.*/\.completed/(step-3-terminal|step-4|step-5c-terminal|step-final-summary).*#\1#')
  case "$name" in
    step-3-terminal|step-4|step-5c-terminal|step-final-summary) printf '%s' "$name"; return 0 ;;
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
  if printf '%s' "$normalized" | grep -Eq '^IMPLEMENT_TMPDIR=[^;]+;'; then
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
  printf '%s' "$normalized" | grep -Eq "$test_re" || return 1
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
    json_deny_probe
  fi
  exit 0
}

json_deny_probe() {
  # #5610: emit deny JSON with a static printf string, not jq -cn ... || true. jq is still
  # required to parse the hook input up front, but a jq runtime failure at this final emit
  # point must not silently swallow the deny signal.
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Repeated foreground terminal-sentinel probes while the sentinel is still absent. These are spurious empty-output <task-notification> turns (#5240, #5478): end the turn without probing and wait for a <task-notification> with new non-empty content. The guard clears once the sentinel appears."}}'
}

json_deny_monitor() {
  # Deny Monitor and TaskOutput tool calls while any immediate-background wait is active.
  # Arming Monitor during a background wait is the primary amplifier of premature
  # notification storms (BC8DDA64: 7 Monitors armed, 40 "still waiting" turns). Static
  # printf — not jq — so a jq failure cannot swallow the deny.
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"An immediate-background wait is active. Do not arm Monitor or poll TaskOutput during a background wait; end the turn and wait for <task-notification>."}}'
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
    json_deny_probe
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
    return 1
  fi
  pid=$(marker_value "$marker" PID) || return 2
  start=$(marker_value "$marker" START_EPOCH) || return 2
  timeout=$(marker_value "$marker" TIMEOUT_S) || return 2
  case "$pid" in ''|*[!0-9]*) return 2 ;; esac
  case "$start" in ''|*[!0-9]*) return 2 ;; esac
  case "$timeout" in ''|*[!0-9]*) return 2 ;; esac
  kill -0 "$pid" 2>/dev/null || { rm -f "$marker" 2>/dev/null || true; reset_probe_counter_for_step "$dir" "$step"; return 1; }
  grace=60
  limit=$((timeout + grace))
  age=$((now - start))
  if [ "$age" -lt 0 ]; then
    return 2
  fi
  if [ "$age" -gt "$limit" ]; then
    rm -f "$marker" 2>/dev/null || true
    reset_probe_counter_for_step "$dir" "$step"
    return 1
  fi
  LIVE_MARKER_DIR="$dir"
  LIVE_MARKER_STEP="$step"
  return 0
}

json_deny() {
  # #5610: emit deny JSON with a static printf string, not jq -cn ... || true, so a jq
  # runtime failure at the final emit point cannot silently swallow the deny signal. jq is
  # still required to parse the hook input up front (the hook fails open when jq is absent).
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"An immediate-background wait is active. End the turn and wait for <task-notification>; do not poll progress artifacts."}}'
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
  json_deny
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

path_is_task_output() {
  case "$1" in
    tasks/*.output|*/tasks/*.output) return 0 ;;
  esac
  return 1
}

path_is_known_result() {
  case "$(basename "$1" 2>/dev/null)" in
    .step3-review-result.env|.design-publish-result.env|final-summary.md) return 0 ;;
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
    *step-3-terminal*|*step-4*|*step-5c-terminal*|*step-final-summary*|*step3-terminal-persisted-this-run*|*step-8-ship-handoff.rc*) ;;
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
  # identifier). Treat the reference as plausibly targeting dir only when
  # there is real correlation: the call's own cwd already is dir, or dir's
  # embedded repo-clone tag (bash_marker_clone_tag) matches the tag derived
  # from cwd's basename the same way _make_session_tmpdir names a session's
  # own tmpdir. Heuristic, not a guarantee: two distinct repo clones sharing
  # a basename still collide, the same known limitation #5684 already
  # accepts for directory-based session isolation elsewhere in this file.
  local dir="$1" cwd_canon="$2" marker_tag cwd_tag
  [ -n "$dir" ] || return 1
  if [ -n "$cwd_canon" ] && [ "$cwd_canon" = "$dir" ]; then
    return 0
  fi
  [ -n "$cwd_canon" ] || return 1
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
  # correlates to this dir. *"$dir"* and the tasks/output-file pattern stay
  # unconditional: they are already dir-specific.
  local cmd="$1" dir="$2" cwd_canon="$3"
  local design_tmpdir_ref="\$DESIGN_TMPDIR"
  local design_tmpdir_braced="\${DESIGN_TMPDIR}"
  local session_tmpdir_ref="\$SESSION_TMPDIR"
  local session_tmpdir_braced="\${SESSION_TMPDIR}"
  local implement_tmpdir_ref="\$IMPLEMENT_TMPDIR"
  local implement_tmpdir_braced="\${IMPLEMENT_TMPDIR}"
  case "$cmd" in
    *"$dir"*|*tasks/*.output*) return 0 ;;
  esac
  case "$cmd" in
    *"$design_tmpdir_ref"*|*"$design_tmpdir_braced"*|*"$session_tmpdir_ref"*|*"$session_tmpdir_braced"*|*"$implement_tmpdir_ref"*|*"$implement_tmpdir_braced"*)
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

cwd_canon=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
fi

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
      json_deny_monitor
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
  while IFS= read -r dir || [ -n "$dir" ]; do
    [ -n "$dir" ] || continue
    # #5925 follow-up: path_is_task_output matches the tasks/*.output read-path pattern
    # regardless of which live marker $dir this loop iteration holds, so it previously
    # denied a session's read of its OWN just-completed bg task output whenever ANY clone
    # (including a foreign one) had a live marker — the model then misread the deny as its
    # own wait still running and stalled. Gate it on clone correlation like the Bash paths.
    # path_under_dir (task output is never under the marker tmpdir) and the known-result
    # branch already require the read to bind to this session, so only path_is_task_output
    # needs the plausibility gate.
    if path_under_dir "$read_abs" "$dir" || { path_is_task_output "$read_path" && bash_probe_target_dir_plausible "$dir" "$cwd_canon"; } || { path_is_known_result "$read_path" && { path_under_dir "$read_abs" "$dir" || [ "$cwd_canon" = "$dir" ]; }; }; then
      deny_if_needed "$dir"
    fi
  done <"$live_dirs_file"
  exit 0
fi

cmd=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -n "$cmd" ] || exit 0
bash_is_strict_wrapper_only "$cmd" && exit 0
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
