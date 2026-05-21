## Goal
Unify /implement review flow: drop --quick, --no-merge, /imaq, /imq; unify Step 5 to HARD panel, 5 rounds, dynamic-archetypes default=6

## Implementation Plan

Goal: Unify /implement review flow by removing --quick, --no-merge, and related infrastructure. All review runs use the unified HARD path (--panel hard, 5 rounds, dynamic-archetypes default=6).

### Files to modify

1. **scripts/run-step5-review.sh** (lines 145-157)
   - Unify SIMPLE and HARD cases: both use REVIEW_PANEL="hard" and ROUND_CAP="5"

2. **scripts/test-run-step5-review.sh**
   - SIMPLE workflow test: --panel simple → --panel hard
   - HARD workflow test: --round-cap 7 → --round-cap 5

3. **skills/implement/SKILL.md** (multiple sections)
   - argument-hint: remove [--quick]
   - Remove --quick flag section
   - Remove --no-merge flag section
   - --hard flag: remove quick_mode references
   - --inline flag: remove "No effect under --quick" sentence
   - --dynamic-archetypes: change default 4 → 6 (two references)
   - Step 1: Remove ### Quick mode section entirely
   - Step 1 Normal mode: Remove simplicity classification preamble
   - Step 1: Update both-externals-down references to Quick mode
   - Step 1: Remove --quick-mode from persist-implement-run-flags.sh call
   - Step 5 comment header: update dynamic-archetypes default=4 → 6
   - Step 5: Change "If quick_mode=false, print:" to unconditional print
   - Step 5: Update panel/round-cap description (unified to hard, 5 rounds)
   - Step 5: Replace two breadcrumbs with single unified breadcrumb
   - Step 5: Update dynamic_archetypes_cap default from 4 to 6
   - Step 7a: Remove quick_mode=true logic/references
   - Step 7a: Update CODE_FLOW_SKIP_REASON quick-mode reference
   - Larch-log batches: update quick/SIMPLE mode references

4. **skills/imaq/** - Delete entire directory
5. **skills/imq/** - Delete entire directory

6. **skills/fix-issue/SKILL.md**
   - Remove --quick flag section (the Removed deprecation block)

7. **.claude/skills/agnix-fix/SKILL.md**
   - Remove --quick from description and invocation args

8. **scripts/test-implement-structure.sh**
   - Remove: grep -q 'Skip.*Normal mode.*post.*design.*sections' assertion block

9. **skills/fix-issue/scripts/test-fix-issue-bail-detection.sh**
   - Remove assertion (a6) about --quick not being in invocation


## Test plan
- make lint (pre-commit + agent-lint)
- run: bash scripts/test-run-step5-review.sh (check assertions pass)
- run: bash scripts/test-implement-structure.sh (check assertions pass)
- run: bash skills/fix-issue/scripts/test-fix-issue-bail-detection.sh (check assertions pass)
