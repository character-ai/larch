#!/usr/bin/env bash
# test-implement-anti-halt.sh — Regression harness for /implement
# step-boundary anti-halt continuation reminders.
#
# Invoked via:  bash scripts/test-implement-anti-halt.sh
# Wired into:   make lint (via the test-implement-anti-halt Makefile target).

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
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

first_line_number() {
  local needle="$1"
  local rel="$2"
  local abs="$REPO_ROOT/$rel"
  grep -nF -- "$needle" "$abs" | head -1 | cut -d: -f1 || true
}

check_order() {
  local label="$1"
  local rel="$2"
  local before="$3"
  local after="$4"
  local before_line after_line

  before_line=$(first_line_number "$before" "$rel")
  after_line=$(first_line_number "$after" "$rel")
  if [[ -n "$before_line" && -n "$after_line" && "$before_line" -lt "$after_line" ]]; then
    echo "PASS: $label"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL: $label — before=$before_line after=$after_line" >&2
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
check_contains "Step 7a forbids code-flow body chat" "skills/implement/SKILL.md" "NEVER print code-flow diagram bodies to chat"
check_contains "Step 7a forbids failure-log run-log copy" "skills/implement/SKILL.md" "NEVER copy diagram failure captures into committed implement run logs"
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
check_contains "Post-preflight boundary — silent halt covered" "skills/implement/SKILL.md" \
  "do NOT end the turn on the audit-pass envelope"
check_contains "Post-/review boundary — silent halt covered" "skills/implement/SKILL.md" \
  "Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn"
check_contains "Assessment fix ladder bars ci-fixer" "skills/implement/SKILL.md" \
  "The ci-fixer subagent never fixes architectural violations or deviations; the coder does, then the main agent."
check_contains "Assessment invariant hard stop has no waiver" "skills/implement/SKILL.md" \
  "there is no waiver and the run must not create or merge the PR"
check_contains "Assessment fixes never routed to ci-fixer" "skills/implement/SKILL.md" \
  "Never route invariant or guideline fixes to the ci-fixer subagent."
check_contains "Assessment tier-1 coder spawn carries plan, note, and evidence paths" "skills/implement/SKILL.md" \
  'carrying paths to the plan (`$IMPLEMENT_TMPDIR/plan.txt`), the assessor note (`$IMPLEMENT_TMPDIR/assessment-note-<kind>.md`), and the materialized evidence'
check_contains "Recovery blocks reporting until reconciliation" "skills/implement/SKILL.md" \
  'do not start Steps 16, 16a, 17, or 18 until `ship reconcile-manual-merge` returns verified `RECONCILE_STATUS=ok`, including the bail-overlay post-read'
check_contains "Manual recovery clears in-memory stall" "skills/implement/SKILL.md" \
  'set in-memory `STALL_TRACKING=false` and pass `--stall-tracking-memory false`'
check_contains "Deferred emit survives next turn" "skills/implement/SKILL.md" \
  "the in-context cached-body obligation survives into the next turn"

echo ""
echo "--- /design step-boundary anti-halt coverage ---"
check_contains "/design Step 2b to Step 3 reminder" "skills/design/SKILL.md" "implementation plan is an intermediate design artifact"
check_contains "/design Step 3b to Step 4 reminder" "skills/design/SKILL.md" "Continue to Step 4 IMMEDIATELY"
check_contains "/design Step 4 to Step 5 reminder" "skills/design/SKILL.md" "Continue to Step 5 IMMEDIATELY"
check_contains "/design Step 5b.5 to Step 5c reminder" "skills/design/SKILL.md" "Continue to Step 5c IMMEDIATELY"

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
check_contains "Post-/review boundary — Stop hook calls Python resolver CLI" \
  "skills/implement/scripts/hook-stop-fail-close.sh" \
  "session resolve-implement-tmpdir"
check_order "Post-/review boundary — Stop hook pre-check before Python resolver" \
  "skills/implement/scripts/hook-stop-fail-close.sh" \
  "for dir in \"\$root\"/claude-implement-*; do" \
  "session resolve-implement-tmpdir --cwd \"\$HOOK_CWD\""
check_contains "Post-/review boundary — Stop hook resolver capture fail-open" \
  "skills/implement/scripts/hook-stop-fail-close.sh" \
  "IMPLEMENT_TMPDIR=\$(python3 \"\$PLUGIN_ROOT/python/cli.py\" session resolve-implement-tmpdir --cwd \"\$HOOK_CWD\" 2>/dev/null) || IMPLEMENT_TMPDIR=\"\""
check_contains "Post-/review boundary — review-boundary-passed sentinel write in SKILL.md" \
  "skills/implement/SKILL.md" \
  ".review-boundary-passed"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
