## Goal
Guard Step 5a against wrong-skill invocation via SKILL.md prose and CI assertions

## Implementation Plan

Goal: Guard against Step 5a wrong-skill invocation (larch:fix-issue instead of larch:implement).

### Files

1. skills/fix-issue/SKILL.md
   - Add NEVER #9 in Anti-patterns (after #8): "NEVER use larch:fix-issue as skill: field at Step 5a; MUST use larch:implement. Also: --inline MUST NOT appear in args: when hard_mode=false."
   - Update Step 5a "Invoke /implement via the Skill tool." sentence to mention larch:implement as the required skill: field name.

2. skills/fix-issue/scripts/test-fix-issue-bail-detection.sh
   - Add assert_not_contains helper function.
   - Add assertion (g): Step 5a block contains "larch:implement".
   - Add assertion (h): Step 5a block does NOT contain "larch:fix-issue".
   - Update header comment: 12 → 14 assertions.

3. skills/fix-issue/scripts/test-fix-issue-bail-detection.md
   - Update assertion count (12 → 14) and document (g) and (h).

### Constraint
The awk extraction window is "### 5a" → "<!-- step:6". "larch:fix-issue" must NOT appear in that window (so assertion (h) works); "larch:implement" MUST appear in it (so assertion (g) works). NEVER #9 references both but sits outside the window (in Anti-patterns).


## Test plan
Run: bash skills/fix-issue/scripts/test-fix-issue-bail-detection.sh
Expected: All 14 assertions passed.
