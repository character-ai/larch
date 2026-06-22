#!/usr/bin/env bash
# step-architectural-guidelines-write-staged.sh — thin wrapper for staged guideline assessment writes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines write-staged-assessment "$@"
