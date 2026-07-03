#!/usr/bin/env bash
# step-5-review.sh — /implement Step 5 review loop launcher.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

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

rehydrate_plugin_root
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
printf '> **🔶 /implement 5: code review — review-and-fix step5 --mode loop, tier cap 2/2/3; escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; dynamic-archetypes cap=%s**\n' "$dynamic_archetypes_cap"

# Write bg-wait marker so hook-bg-poll-guard.sh can deny Monitor/TaskOutput/progress
# probes during the review wait. Fail-open: a write failure must not abort the review.
rm -f "$IMPLEMENT_TMPDIR/no-progress-turns.count" "$IMPLEMENT_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-5-terminal.count" "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" 2>/dev/null || true
_step5_cleanup() {
  mkdir -p "$IMPLEMENT_TMPDIR/.completed" 2>/dev/null || true
  printf '' >"$IMPLEMENT_TMPDIR/.completed/step-5-terminal" 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
}
trap _step5_cleanup EXIT
_step5_start=$(date +%s 2>/dev/null) || _step5_start=0
case "$_step5_start" in ''|*[!0-9]*) _step5_start=0 ;; esac
_step5_claude_pid="${LARCH_BG_POLL_GUARD_SESSION_PID:-${PPID:-}}"
_step5_clone_path=""
if [ -f "$IMPLEMENT_TMPDIR/.larch-keepalive" ] && [ ! -L "$IMPLEMENT_TMPDIR/.larch-keepalive" ]; then
  _step5_clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$IMPLEMENT_TMPDIR/.larch-keepalive" 2>/dev/null || true)
fi
printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step5-review\nTIMEOUT_S=21600\nCLONE_PATH=%s\n' \
  "$$" "$_step5_claude_pid" "$_step5_start" "$_step5_clone_path" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true

if [ -n "$difficulty_override" ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1 --difficulty "$difficulty_override"
else
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1
fi
