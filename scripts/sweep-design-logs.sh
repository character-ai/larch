#!/usr/bin/env bash
# sweep-design-logs.sh — SessionStart hook: launches the design-log PR sweep as a
# detached background process so accumulated chore(larch-logs) PRs with green
# required CI checks are admin-merged without blocking session start.
# Always exits 0 (SessionStart is non-blocking by spec).

set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd -P)"
CLI="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_DIR/..}/python/cli.py"

# Skip silently when python3 or cli.py is unavailable.
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$CLI" ] || exit 0

# Redirect sweep output to a per-invocation log; ignore write failures.
SWEEP_LOG="${TMPDIR:-/tmp}/larch-sweep-design-logs-$$.log"
: >"$SWEEP_LOG" 2>/dev/null || SWEEP_LOG=/dev/null

# Launch the sweep as a detached subprocess so the hook exits immediately.
# Output is captured to the temp log for post-hoc debugging.
python3 "$CLI" ship design-log-sweep >"$SWEEP_LOG" 2>&1 &
disown "$!" 2>/dev/null || true

exit 0
