#!/usr/bin/env bash
# discover-md-set.sh — Thin shell wrapper around discover-md-set.py. The parser
# lives in Python because robust Markdown link extraction with fenced-block
# exclusion and path canonicalization is awkward in pure bash.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# Restore original stdout so the Python subprocess's contract output reaches the caller.
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3
exec python3 "$SCRIPT_DIR/discover-md-set.py" "$@"
