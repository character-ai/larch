#!/usr/bin/env bash
# Regression harness for invoke-plan-validator.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/invoke-plan-validator.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-plan-validator-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

DESIGN_TMPDIR="$TMPROOT/design space"
mkdir -p "$DESIGN_TMPDIR"
PLAN_FILE="$DESIGN_TMPDIR/plan with spaces.txt"
printf '# Plan\n\ndiff_lines: 1\n' >"$PLAN_FILE"

export DESIGN_TMPDIR CLAUDE_PLUGIN_ROOT="$ROOT"
out=$("$SUBJECT" "$PLAN_FILE")
printf '%s\n' "$out" | grep -q '^STEP_STARTED=VALIDATE_PLAN_COMMANDS$' || fail "validator wrapper did not start action"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=VALIDATE_PLAN_COMMANDS$' || fail "validator wrapper did not complete action"

unset DESIGN_TMPDIR
set +e
"$SUBJECT" "$PLAN_FILE" >"$TMPROOT/missing-env.out" 2>"$TMPROOT/missing-env.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing DESIGN_TMPDIR should fail"
grep -Fq 'DESIGN_TMPDIR must be set' "$TMPROOT/missing-env.err" || fail "missing DESIGN_TMPDIR error not surfaced"

echo "PASS: test-invoke-plan-validator.sh"
