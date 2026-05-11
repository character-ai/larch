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

# Step 2→3: pin the post-implementation-completion boundary specifically
# ("Continue to Step 3 IMMEDIATELY" also appears at the Q/A re-dispatch
# site on line 949 — use the unique reason clause to pin the right site).
check_contains "Step 2 to Step 3 reminder (impl completion)" "skills/implement/SKILL.md" "Implementation is not the end of the run — checks"
check_contains "Step 4 to Step 5 reminder" "skills/implement/SKILL.md" "Continue to Step 5 IMMEDIATELY"
check_contains "Step 7a to Step 8 reminder" "skills/implement/SKILL.md" "Continue to Step 8 IMMEDIATELY"
# Step 12d→14: pin the bail-path boundary specifically
# ("Continue to Step 14 IMMEDIATELY" also appears at the 12b merged! and
# 12a already_merged paths — use the unique reason clause to pin the bail site).
check_contains "Step 12d to Step 14 reminder (bail path)" "skills/implement/SKILL.md" "Step 12d bail is not terminal"
check_contains "Step 14 to Step 15 reminder" "skills/implement/SKILL.md" "Continue to Step 15."
check_contains "Step 15 to Step 16 reminder" "skills/implement/SKILL.md" "Continue to Step 16."
check_contains "Step 16 to Step 17 reminder" "skills/implement/SKILL.md" "Continue to Step 17."
check_contains "Step 17 to Step 18 reminder" "skills/implement/SKILL.md" "Continue to Step 18."
check_contains "Shared SSOT section" "skills/shared/subskill-invocation.md" "Step-boundary anti-halt"
# Post-/design and post-/review boundary silent-halt directives (issue #1814):
# pins that these two boundaries explicitly say "do NOT end the turn" and not
# just "do NOT write a summary" (the same gap 9d639da fixed at Step 8).
check_contains "Post-/design boundary — silent halt covered" "skills/implement/SKILL.md" \
  "boundary wrapper + anchor-section fragment writes + Step 1.r rebase checkpoint + Step 2 breadcrumb in order — do NOT end the turn"
check_contains "Post-/review boundary — silent halt covered" "skills/implement/SKILL.md" \
  "Cross-Skill Health Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn"

echo ""
echo "--- /design step-boundary anti-halt coverage ---"
check_contains "/design Step 2b to Step 3 reminder" "skills/design/SKILL.md" "implementation plan is an intermediate design artifact"
check_contains "/design Step 3b to Step 4 reminder" "skills/design/SKILL.md" "Continue to Step 4 IMMEDIATELY"
check_contains "/design Step 4 to Step 5 reminder" "skills/design/SKILL.md" "Continue to Step 5 IMMEDIATELY"

echo ""
echo "--- /fix-issue step-boundary anti-halt coverage ---"
check_contains "/fix-issue Step 6 to Step 8 reminder" "skills/fix-issue/SKILL.md" "Continue to Step 8 IMMEDIATELY"
# Post-/implement boundary in /fix-issue (issue #1846 — same gap PR #1817 fixed for
# post-/design and post-/review in /implement): pin that the directive explicitly says
# "do NOT end the turn" and not just "do NOT write a summary" (covers silent halts).
# Uses the "status recap" phrase (unique to fix-issue context) to distinguish this
# directive from implement's post-/design and post-/review directives.
check_contains "Post-/implement boundary in /fix-issue — silent halt covered" "skills/fix-issue/SKILL.md" \
  "do NOT end the turn (neither silently nor after text output), and do NOT write a summary, status recap"

echo ""
echo "--- /review step-boundary anti-halt coverage ---"
check_contains "/review Step 3f to Step 4 reminder" "skills/review/SKILL.md" "non-substantial re-review convergence line is not terminal"
check_contains "/review Step 4c to Step 4d reminder" "skills/review/SKILL.md" "Continue to Step 4d IMMEDIATELY"
check_contains "/review Step 4d to Step 5 reminder" "skills/review/SKILL.md" "review-result footer is not terminal"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
