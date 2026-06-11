#!/usr/bin/env bash
# step-18-finalize.sh — /implement closing marks, finalize-state restore, and teardown.

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

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
rehydrate_larch_triplet
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" token report --since-last-mark --terse > /dev/null || true
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing report --since-last-mark --terse > /dev/null || true
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" token mark "Step 18 — done" || true
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing mark "Step 18 — done" || true
_restore_finalize=false
if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
  if [ "${LARCH_SHIP_PR_IMPL:-python}" = "bash" ]; then
    _restore_finalize=true
  elif [ ! -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
    _restore_finalize=true
  else
    _ship_stall=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --key STALL_TRACKING --default "false")
    _ship_bail=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --key BAIL_NEEDS_USER_INPUT --default "false")
    _ship_step=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --key STALL_STEP --default "")
    _final_step=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/finalize-state.sh" --key STALL_STEP --default "")
    _ship_stall_truthy=false
    _ship_bail_truthy=false
    case "$_ship_stall" in 1|true|TRUE|True|yes|YES|Yes|on|ON|On) _ship_stall_truthy=true ;; esac
    case "$_ship_bail" in 1|true|TRUE|True|yes|YES|Yes|on|ON|On) _ship_bail_truthy=true ;; esac
    if [ "$_ship_stall_truthy" = true ] || [ "$_ship_bail_truthy" = true ] || { [ -n "$_ship_step" ] && [ "$_ship_step" != "$_final_step" ]; }; then
      _restore_finalize=true
    fi
  fi
fi
if [ "$_restore_finalize" = true ]; then
  if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session restore-finalize-state       --implement-tmpdir "$IMPLEMENT_TMPDIR"; then
    printf '%s
' "**⚠ Step 18: restore-finalize-state.sh failed; proceeding to teardown.**" >&2
  fi
fi
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session clear-implement-pointer --claude-pid "${LARCH_CLAUDE_PID:-$PPID}" 2>/dev/null || true
"$CLAUDE_PLUGIN_ROOT/scripts/implement-finalize.sh" teardown   --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh"   --implement-tmpdir "$IMPLEMENT_TMPDIR"
