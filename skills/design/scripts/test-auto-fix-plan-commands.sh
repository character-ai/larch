#!/usr/bin/env bash
# Compatibility harness for the Python auto-fix command tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

cd "$REPO_ROOT"
grep -Fq "auto_fix_plan_commands_main" "$REPO_ROOT/python/larch/design/plan_quality.py"
grep -Fq "validator_autofix_main" "$REPO_ROOT/python/larch/design/plan_quality.py"
exec pytest -q python/test_plan_quality.py -k auto_fix
