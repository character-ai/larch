#!/usr/bin/env bash
# test-implement-anti-halt.sh — Regression harness for /implement
# step-boundary anti-halt continuation reminders.
#
# Invoked via:  bash scripts/test-implement-anti-halt.sh
# Wired into:   make lint (via the test-implement-anti-halt Makefile target).

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

FAIL_COUNT=0
PASS_COUNT=0

check_contains() {
  local label="$1"
  local rel="$2"
  local needle="$3"
  local abs="$REPO_ROOT/$rel"

  if [[ ! -f "$abs" ]]; then
    echo "FAIL: $label — $rel does not exist" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  if grep -Fq -- "$needle" "$abs"; then
    echo "PASS: $label"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL: $label — missing literal: $needle" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "--- /implement step-boundary anti-halt coverage ---"

check_contains "Step 2 to Step 3 reminder" "skills/implement/SKILL.md" "Continue to Step 3 IMMEDIATELY"
check_contains "Step 4 to Step 5 reminder" "skills/implement/SKILL.md" "Continue to Step 5 IMMEDIATELY"
check_contains "Step 7a to Step 8 reminder" "skills/implement/SKILL.md" "Continue to Step 8 IMMEDIATELY"
check_contains "Step 12 to Step 14 reminder" "skills/implement/SKILL.md" "Continue to Step 14 IMMEDIATELY"
check_contains "Step 14 to Step 15 reminder" "skills/implement/SKILL.md" "Continue to Step 15."
check_contains "Step 15 to Step 16 reminder" "skills/implement/SKILL.md" "Continue to Step 16."
check_contains "Step 16 to Step 16a reminder" "skills/implement/SKILL.md" "Continue to Step 16a."
check_contains "Step 16a to Step 17 reminder" "skills/implement/SKILL.md" "Continue to Step 17."
check_contains "Step 17 to Step 18 reminder" "skills/implement/SKILL.md" "Continue to Step 18."
check_contains "Shared SSOT section" "skills/shared/subskill-invocation.md" "Step-boundary anti-halt"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
