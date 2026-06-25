#!/usr/bin/env bash
# step-architectural-guidelines-read.sh — thin wrapper for architectural guidelines read.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"

python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines invalidate --implement-tmpdir "$IMPLEMENT_TMPDIR"
exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines read "$@"
