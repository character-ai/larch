#!/usr/bin/env bash
# oos-disposition-gate.sh — thin wrapper delegating to python/cli.py oos disposition-gate.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec python3 "$PLUGIN_ROOT/python/cli.py" oos disposition-gate "$@"
