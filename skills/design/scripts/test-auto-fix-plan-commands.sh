#!/usr/bin/env bash
# Compatibility harness for the Python auto-fix command tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

cd "$REPO_ROOT"
grep -Fq "env LARCH_QUIET_DISABLE=1 python3 \"\$CLAUDE_PLUGIN_ROOT/python/cli.py\" plan auto-fix-commands" "$REPO_ROOT/skills/design/scripts/design-step-validator-autofix.sh"
exec pytest -q python/test_plan_quality.py -k auto_fix
