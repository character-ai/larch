#!/usr/bin/env bash
# sessionstart-statusline.sh — SessionStart hook for larch progress statusline install.
# Always fail silent: statusline installation must not block Claude startup.

set -uo pipefail

INPUT=$(cat 2>/dev/null || true)
[ "${LARCH_STATUSLINE_DISABLE:-}" = "1" ] && exit 0
SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd -P 2>/dev/null)" || exit 0
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P 2>/dev/null)}" || exit 0
CLI="$PLUGIN_ROOT/python/cli.py"

command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$CLI" ] || exit 0

printf '%s' "$INPUT" | python3 "$CLI" progress session-reset >/dev/null 2>&1 || true
printf '%s' "$INPUT" | python3 "$CLI" progress install-statusline --plugin-root "$PLUGIN_ROOT" >/dev/null 2>&1 || true
exit 0
