#!/usr/bin/env bash
# step-architectural-guidelines-materialize.sh — thin wrapper for guidelines diff materialization.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines materialize-diff --forked-target "${forked_target:-false}" "$@"
