#!/usr/bin/env bash
# write-final-report.sh — thin wrapper around python final-report writer.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"

exec python3 "$PLUGIN_ROOT/python/cli.py" final-report write "$@"
