#!/usr/bin/env bash
# Structural regression test for /implement SKILL.md + larch-log migration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/implement/references"
RESTORE_FINALIZE_SH="$REPO_ROOT/scripts/restore-finalize-state.sh"
LIB_FINALIZE_KEYS_SH="$REPO_ROOT/scripts/lib-finalize-state-keys.sh"
SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
LINT_FIX_LOOP_SH="$REPO_ROOT/scripts/lint-fix-loop.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -d "$REFS_DIR" ]] || fail "skills/implement/references missing"

for heading in "## Load-Bearing Invariants" "## NEVER List" "## Rebase Checkpoint Macro"; do
  count="$(grep -c "^$heading$" "$SKILL_MD" || true)"
  [[ "$count" == "1" ]] || fail "expected exactly one $heading heading, found $count"
done

for ref in summary-comment-template.md bump-verification.md codex-manifest-schema.md conflict-resolution.md pr-body-template.md rebase-rebump-subprocedure.md; do
  [[ -f "$REFS_DIR/$ref" ]] || fail "missing reference: $ref"
done

grep -Fq 'scripts/larch-log.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/larch-log.sh"
grep -Fq 'scripts/tracking-issue-summary.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/tracking-issue-summary.sh"
grep -Fq 'summary-comment-template.md' "$SKILL_MD" \
  || fail "SKILL.md must reference summary-comment-template.md"

if grep -Eiq '(^|[^[:alpha:]])user has( made| fixed)?([^[:alpha:]]|$)' \
    "$SKILL_MD" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.md" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"; then
  fail "orchestrator/review-fix docs must not attribute coder work as 'user has...'"
fi

old_surfaces=(anchor-section-markers.sh assemble-anchor.sh hydrate-anchor.sh refresh-anchor.sh upsert-anchor find-anchor ANCHOR_COMMENT_ID "\$IMPLEMENT_TMPDIR/anchor-sections")
for old in "${old_surfaces[@]}"; do
  if grep -Fq "$old" "$SKILL_MD"; then
    fail "SKILL.md still references removed anchor surface: $old"
  fi
done

grep -Fq 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" \
  || fail "focus-area enum missing"
grep 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" | grep -q 'security' \
  || fail "focus-area enum line must include security"

grep -Fq '### Larch-log batches' "$SKILL_MD" \
  || fail "SKILL.md must contain the Larch-log batches section heading"
grep -q 'Skip.*Normal mode.*post.*design.*sections' "$SKILL_MD" \
  || fail "quick mode must explicitly skip Normal mode before the Larch-log batches tail"

# shellcheck disable=SC2016
grep -qE 'NEVER write, recreate, or modify .\$IMPLEMENT_TMPDIR/finalize-state\.sh' "$SKILL_MD" \
  || fail "SKILL.md must contain NEVER bullet for finalize-state.sh write prohibition"

step18_order_status=0
awk '
  /<!-- step:18/ {
    in_step = 1
    next
  }
  in_step && /<!-- step:/ {
    in_step = 0
    in_bash = 0
  }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ {
    in_bash = 1
    next
  }
  in_step && in_bash && /^```[[:space:]]*$/ {
    in_bash = 0
    next
  }
  in_step && in_bash && restore_line == 0 && /\/scripts\/restore-finalize-state\.sh/ {
    restore_line = NR
  }
  in_step && in_bash && teardown_line == 0 && /\/scripts\/implement-finalize\.sh.*teardown/ {
    teardown_line = NR
  }
  END {
    if (restore_line == 0) exit 10
    if (teardown_line == 0) exit 11
    if (restore_line >= teardown_line) exit 12
  }
' "$SKILL_MD" || step18_order_status=$?
case "$step18_order_status" in
  0) ;;
  10) fail "restore-finalize-state.sh not found in Step 18 region" ;;
  11) fail "implement-finalize.sh teardown not found in Step 18 region" ;;
  12) fail "restore-finalize-state.sh must appear before implement-finalize.sh teardown in Step 18" ;;
  *) fail "unexpected Step 18 finalize-state order check failure: $step18_order_status" ;;
esac

[[ -f "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh missing"
[[ -x "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh must be executable"
[[ -f "$REPO_ROOT/scripts/restore-finalize-state.md" ]] || fail "scripts/restore-finalize-state.sh must have sibling restore-finalize-state.md"

[[ -f "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh missing"
[[ -x "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh must be executable"
[[ -f "$REPO_ROOT/scripts/lint-fix-loop.md" ]] || fail "scripts/lint-fix-loop.sh must have sibling lint-fix-loop.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-quiet\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-quiet.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-cursor-launcher-common\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-cursor-launcher-common.sh"
grep -Fq 'run-external-agent.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must dispatch through run-external-agent.sh"

step3_lint_status=0
awk '
  /<!-- step:3/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step3_lint_status=$?
[[ "$step3_lint_status" == "0" ]] || fail "Step 3 region must reference lint-fix-loop.sh"

step6_lint_status=0
awk '
  /<!-- step:6/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step6_lint_status=$?
[[ "$step6_lint_status" == "0" ]] || fail "Step 6 region must reference lint-fix-loop.sh"

step5_lint_status=0
awk '
  /<!-- step:5/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step5_lint_status=$?
[[ "$step5_lint_status" == "0" ]] || fail "Step 5 region must reference lint-fix-loop.sh"

if grep -Eiq 'diagnose([[:space:]]*,[[:space:]]*|[[:space:]]*\+[[:space:]]*)fix' "$SKILL_MD"; then
  fail "SKILL.md must not contain bare diagnose/fix relevant-checks loops without lint-fix-loop.sh routing"
fi

# Pin that ship-pr.sh run_checks_phase calls lint-fix-loop.sh internally, so the
# orchestrator never needs to fix PHASE=checks failures via main-agent Edit/Write.
grep -q 'lint-fix-loop\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must reference lint-fix-loop.sh (run_checks_phase call site)"
grep -q 'ship-pr-ci-initial' "$SHIP_PR_SH" \
  || fail "ship-pr.sh run_checks_phase must pass --site ship-pr-ci-initial to lint-fix-loop.sh"
grep -q 'ship-pr-ci-initial' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-initial"
grep -q 'ship-pr-ci-merge' "$SHIP_PR_SH" \
  || fail "ship-pr.sh CI failure recovery must pass --site ship-pr-ci-merge to lint-fix-loop.sh"
grep -q 'ship-pr-ci-merge' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-merge"

# Ensure SKILL.md Step 10/12 prose does not suggest main-agent Edit/Write for ship-pr CI fixes.
stall6_prose_status=0
awk '
  /STALL_STEP=6/ { window = 5 }
  window > 0 && /Edit.*Write|Write.*Edit|main.agent.*Edit|repair via main-agent/ { found = 1 }
  window > 0 { window-- }
  END { if (found) exit 1 }
' "$SKILL_MD" || stall6_prose_status=$?
[[ "$stall6_prose_status" == "0" ]] || fail "SKILL.md STALL_STEP=6 prose must not suggest main-agent Edit/Write for CI fixes"

[[ -f "$LIB_FINALIZE_KEYS_SH" ]] || fail "scripts/lib-finalize-state-keys.sh missing"
[[ -f "$REPO_ROOT/scripts/lib-finalize-state-keys.md" ]] || fail "scripts/lib-finalize-state-keys.sh must have sibling lib-finalize-state-keys.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$RESTORE_FINALIZE_SH" \
  || fail "restore-finalize-state.sh must source lib-finalize-state-keys.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must source lib-finalize-state-keys.sh"

# shellcheck disable=SC2016
grep -Fq 'When `hard_mode=true`, skip the plan-size evaluation and always persist `POST_PLAN_WORKFLOW_PATH=HARD`' "$SKILL_MD" \
  || fail "Post-plan router must guard hard_mode=true: always persist POST_PLAN_WORKFLOW_PATH=HARD"
# shellcheck disable=SC2016
grep -Fq 'When `hard_mode=false`, use plan size' "$SKILL_MD" \
  || fail "Post-plan router must gate plan-size heuristic under hard_mode=false"

COMMIT_IMPL_SH="$REPO_ROOT/skills/implement/scripts/commit-implementation.sh"
COMMIT_REVIEW_SH="$REPO_ROOT/skills/implement/scripts/commit-review-fixes.sh"
GEN_DIAGRAM_SH="$REPO_ROOT/skills/implement/scripts/generate-code-flow-diagram.sh"

[[ -f "$COMMIT_IMPL_SH" ]] || fail "skills/implement/scripts/commit-implementation.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 4 — commit implementation"' "$COMMIT_IMPL_SH" \
  || fail "commit-implementation.sh must contain Step 4 timing-ledger mark"

[[ -f "$COMMIT_REVIEW_SH" ]] || fail "skills/implement/scripts/commit-review-fixes.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7 — commit review fixes"' "$COMMIT_REVIEW_SH" \
  || fail "commit-review-fixes.sh must contain Step 7 timing-ledger mark"

[[ -f "$GEN_DIAGRAM_SH" ]] || fail "skills/implement/scripts/generate-code-flow-diagram.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7a — code flow diagram"' "$GEN_DIAGRAM_SH" \
  || fail "generate-code-flow-diagram.sh must contain Step 7a timing-ledger mark"

# Pin Exit 4 handling in SKILL.md: must direct orchestrator to "Continue to Step 16"
exit4_step16_status=0
awk '
  /\*\*Exit 4\*\*/ { window = 15 }
  window > 0 && /Continue to Step 16/ { found = 1 }
  window > 0 { window-- }
  END { if (!found) exit 1 }
' "$SKILL_MD" || exit4_step16_status=$?
[[ "$exit4_step16_status" == "0" ]] || fail "SKILL.md Exit 4 prose must direct orchestrator to 'Continue to Step 16'"

# Pin that ship-pr.sh STALL_STEP=12d branch emits the branch-local diagnostic.
stall12d_directive_status=0
awk '
  /policy_denied\|admin_failed\|error\)/ { in_branch = 1 }
  in_branch && /ORCHESTRATOR DIRECTIVE \(STALL_STEP=12d\)/ { found_banner = 1 }
  in_branch && /DO NOT improvise recovery\./ { found_directive = 1 }
  in_branch && /exit 4/ {
    if (found_banner && found_directive) {
      success = 1
      exit 0
    }
    exit 1
  }
  END { if (!success) exit 1 }
' "$SHIP_PR_SH" || stall12d_directive_status=$?
[[ "$stall12d_directive_status" == "0" ]] \
  || fail "ship-pr.sh must emit the ORCHESTRATOR DIRECTIVE (STALL_STEP=12d) DO NOT improvise diagnostic on the STALL_STEP=12d exit 4 path"

echo "All assertions passed."
