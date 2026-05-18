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
# Post-/bump-version boundary halt directives (issue #1850 — same halt pattern as the
# post-/design and post-/review boundaries): Step 8 direct path uses the unique
# "halt in disguise … skips sub-steps 3/3b" clause; rebase-rebump sub-procedure uses
# the "in the tool result is NOT a run-completion signal" clause.
check_contains "Post-/bump-version boundary — Step 8 direct halt covered" "skills/implement/SKILL.md" \
  "before that Bash call is a halt in disguise that skips sub-steps 3/3b"
check_contains "Post-/bump-version boundary — rebase-rebump path halt covered" "skills/implement/references/rebase-rebump-subprocedure.md" \
  "in the tool result is NOT a run-completion signal"
# Post-/bump-version boundary mechanical backstops (issue #2338): PostToolUse hook
# parallel to hook-post-design.sh that injects a continuation directive when
# .bump-version-armed is present without postbump-state.sh.
check_contains "Post-/bump-version boundary — PostToolUse hook script exists" \
  "skills/implement/scripts/hook-post-bump-version.sh" \
  ".bump-version-armed"
check_contains "Post-/bump-version boundary — PostToolUse hook registered in hooks.json" \
  "hooks/hooks.json" \
  "hook-post-bump-version.sh"
check_contains "Post-/bump-version boundary — NEVER #15 in SKILL.md" \
  "skills/implement/SKILL.md" \
  "NEVER end the turn after \`/bump-version\`'s Skill tool return inside the Rebase + Re-bump Sub-procedure"
check_contains "Post-/bump-version boundary — rebase-rebump path references PostToolUse hook" \
  "skills/implement/references/rebase-rebump-subprocedure.md" \
  "hook-post-bump-version.sh"
# Post-/design and post-/review boundary silent-halt directives (issue #1814):
# pins that these two boundaries explicitly say "do NOT end the turn" and not
# just "do NOT write a summary" (the same gap 9d639da fixed at Step 8).
check_contains "Post-/design boundary — silent halt covered" "skills/implement/SKILL.md" \
  "boundary wrapper + larch-log batch writes + Step 1.r rebase checkpoint + Step 2 breadcrumb in order — do NOT end the turn"
check_contains "Post-/review boundary — silent halt covered" "skills/implement/SKILL.md" \
  "Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn"

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
echo "--- /implement post-/review Stop hook coverage (issue #1862) ---"
# Mechanical enforcement for post-/review boundary (analogous to the post-/design
# Stop hook guard): hook-stop-fail-close.sh blocks session stop while
# review-round-summary.md exists without .review-boundary-passed, and SKILL.md Step 6
# writes .review-boundary-passed to release the guard once the boundary is cleared.
check_contains "Post-/review boundary — Stop hook reads review-round-summary.md sentinel" \
  "skills/implement/scripts/hook-stop-fail-close.sh" \
  "review-round-summary.md"
check_contains "Post-/review boundary — review-boundary-passed sentinel write in SKILL.md" \
  "skills/implement/SKILL.md" \
  ".review-boundary-passed"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
