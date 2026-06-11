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
"$SCRIPT_DIR/design-step3-entry-state.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
"$SCRIPT_DIR/design-step3-entry-preview.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
