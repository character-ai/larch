#!/usr/bin/env bash
# step-architectural-guidelines-prepare.sh — thin wrapper for guidelines read plus diff materialization.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"

read_state_key() {
  local key=$1 default_value=$2 line state_file
  state_file="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
  if [ -f "$state_file" ]; then
    line=$(grep "^${key}=" "$state_file" 2>/dev/null | tail -n 1 || true)
    if [ -n "$line" ]; then
      printf '%s\n' "${line#*=}"
      return 0
    fi
  fi
  printf '%s\n' "$default_value"
}

read_session_key() {
  local key=$1 default_value=$2 line
  if [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
    line=$(grep "^${key}=" "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null | tail -n 1 || true)
    if [ -n "$line" ]; then
      printf '%s\n' "${line#*=}"
      return 0
    fi
  fi
  printf '%s\n' "$default_value"
}

FORKED_TARGET_RESOLVED="${forked_target:-$(read_state_key FORKED_TARGET "$(read_session_key FORKED_TARGET false)")}"
[ -n "$FORKED_TARGET_RESOLVED" ] || FORKED_TARGET_RESOLVED=false

exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines prepare \
  --forked-target "$FORKED_TARGET_RESOLVED" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  "$@"
