#!/usr/bin/env bash
# Combined /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2154
set -euo pipefail
SESSION_ENV_PATH=""
CLAUDE_PID=""
REENTRY=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --reentry) REENTRY=true; shift ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  # shellcheck source=/dev/null
  . "$SESSION_ENV_PATH"
fi
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 3 entry: DESIGN_TMPDIR required" >&2
  exit 1
fi
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
if [ "$REENTRY" = true ]; then
  : > "$DESIGN_TMPDIR/.step3-reentry"
fi
rm -f "$DESIGN_TMPDIR/.pause-save-complete"
"$SCRIPT_DIR/design-step3-entry-state.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
[ -f "$DESIGN_TMPDIR/.pause-save-complete" ] && exit 0
"$SCRIPT_DIR/design-step3-entry-preview.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
