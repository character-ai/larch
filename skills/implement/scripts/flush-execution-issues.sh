#!/usr/bin/env bash
# flush-execution-issues.sh — append execution-issues.md to the run log.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec python3 "$PLUGIN_ROOT/python/cli.py" execution-issues flush "$@"
