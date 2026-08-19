#!/usr/bin/env bash
# test-step-8-oos-checkpoint.sh — offline harness for the Step 8 OOS checkpoint wrapper.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-oos-checkpoint.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then pass "$l"; else fail "$l (missing: $n)"; fi; }
assert_not_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then fail "$l (unexpected: $n)"; else pass "$l"; fi; }

helper_text=$(cat "$HELPER")
assert_contains 'scripts/larch.sh' "$helper_text" 'static: enters through verified bootstrap'
assert_contains 'implement step-8-oos-checkpoint "$@"' "$helper_text" 'static: delegates to Rust checkpoint router'
assert_not_contains 'python/cli.py' "$helper_text" 'static: Python checkpoint owner is retired'
assert_not_contains 'oos disposition-checkpoint' "$helper_text" 'static: no direct disposition-checkpoint call'

if [ "$FAIL" -eq 0 ]; then
  printf 'PASS: test-step-8-oos-checkpoint.sh (%d assertions)\n' "$PASS"
  exit 0
fi
printf 'FAIL: test-step-8-oos-checkpoint.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
