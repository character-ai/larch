#!/usr/bin/env bash
# test-step-8-ci-fixer.sh — thin wrapper and typed adapter boundaries.
# shellcheck disable=SC2016 # Wrapper-shape assertions intentionally match literal variables.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
cd "$ROOT"
WRAPPER="skills/implement/scripts/step-8-ci-fixer.sh"

grep -Fq 'set -euo pipefail' "$WRAPPER"
grep -Fq 'exec python3 "$PLUGIN_ROOT/python/cli.py" implement step-8-ci-fixer "$@"' "$WRAPPER"
if grep -Fq 'bgjob start' "$WRAPPER"; then exit 1; fi
if grep -Fq 'python3 - ' "$WRAPPER"; then exit 1; fi

PYTHONPATH=python python3 -m pytest -q python/tests/implement/test_ci_fixer_adapter.py

echo 'PASS: Step 8 CI fixer delegates start and finalize boundaries to Python'
