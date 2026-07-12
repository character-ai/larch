#!/usr/bin/env bash
# test-step-5-review.sh — thin wrappers and Python Step 5 adapter contract.
# shellcheck disable=SC2016 # Wrapper-shape assertions intentionally match literal variables.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
cd "$ROOT"

for wrapper in step-5-review.sh step-5-resume.sh step-6-entry.sh run-step-checks.sh; do
  path="skills/implement/scripts/$wrapper"
  grep -Fq 'set -euo pipefail' "$path"
  grep -Fq 'exec python3 "$PLUGIN_ROOT/python/cli.py" implement' "$path"
  if grep -Fq 'bgjob start' "$path"; then exit 1; fi
  if grep -Fq 'registry' "$path"; then exit 1; fi
done

PYTHONPATH=python python3 -m pytest -q python/tests/bgjob/test_bgjob_adapt.py
PYTHONPATH=python python3 -m pytest -q \
  python/tests/implement/test_implement_dispatch.py \
  -k 'bgjob_contract_unification'

echo 'PASS: Step 5 wrappers delegate lifecycle and publication to Python'
