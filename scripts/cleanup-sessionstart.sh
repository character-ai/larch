#!/usr/bin/env bash
# cleanup-sessionstart.sh — SessionStart hook: launches the larch temp cleanup as
# a detached background process so age-based larch-* sweeps run automatically
# without blocking session start. Always exits 0 (SessionStart is non-blocking).

set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd -P)"
CLI="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_DIR/..}/python/cli.py"

# Skip silently when python3 or cli.py is unavailable.
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$CLI" ] || exit 0

# Redirect cleanup output to a per-invocation log; ignore write failures.
CLEANUP_LOG="${TMPDIR:-/tmp}/larch-cleanup-sessionstart-$$.log"
: >"$CLEANUP_LOG" 2>/dev/null || CLEANUP_LOG=/dev/null

# Launch cleanup as a detached subprocess so the hook exits immediately.
# Output is captured to the temp log for post-hoc debugging.
env -u LARCH_TEST_TMP_ROOT python3 "$CLI" cleanup run >"$CLEANUP_LOG" 2>&1 &
disown "$!" 2>/dev/null || true

exit 0
