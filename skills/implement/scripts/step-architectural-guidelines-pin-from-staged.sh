#!/usr/bin/env bash
# step-architectural-guidelines-pin-from-staged.sh — thin wrapper for durable guideline note pinning.

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

BASE_REF="$(read_state_key BASE_REF "")"

exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines pin-note-from-staged \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --head-sha "$(git rev-parse HEAD)" \
  --base-ref "${BASE_REF:-}"
