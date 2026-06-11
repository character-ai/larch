#!/usr/bin/env bash
# Combined /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2154
set -euo pipefail
SESSION_ENV_PATH=""
CLAUDE_PID=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    *) printf '%s
' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DESIGN_TMPDIR=""
if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  # shellcheck source=/dev/null
  . "$SESSION_ENV_PATH"
fi
[ -n "${DESIGN_TMPDIR:-}" ] && rm -f "$DESIGN_TMPDIR/.pause-save-complete"
"$SCRIPT_DIR/design-step6-prelude.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
[ -n "${DESIGN_TMPDIR:-}" ] && [ -f "$DESIGN_TMPDIR/.pause-save-complete" ] && exit 0
"$SCRIPT_DIR/design-step6-cleanup.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
