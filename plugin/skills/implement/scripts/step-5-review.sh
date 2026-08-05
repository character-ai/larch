#!/usr/bin/env bash
# step-5-review.sh — thin wrapper delegating to the Rust bgjob adapter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec python3 "$PLUGIN_ROOT/python/cli.py" implement step-5-review "$@"
