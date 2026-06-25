#!/usr/bin/env bash
# step-architectural-guidelines-read.sh — thin wrapper for architectural guidelines read.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"

# Clear stale Phase A artifacts before reading so the orchestrator never needs
# a bare rm loop over a variable path, which triggers Claude Code's safety check.
rm -f \
  "$IMPLEMENT_TMPDIR/architectural-guideline-warnings.md" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-warnings.meta.env" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.md" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.env" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-note.md" \
  "$IMPLEMENT_TMPDIR/architectural-guideline-note.meta.env"

python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines invalidate --implement-tmpdir "$IMPLEMENT_TMPDIR"
exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines read "$@"
