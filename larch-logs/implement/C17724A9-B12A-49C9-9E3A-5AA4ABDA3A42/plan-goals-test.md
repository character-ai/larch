## Goal
Guard post-plan router to never set POST_PLAN_WORKFLOW_PATH=SIMPLE when hard_mode=true

## Implementation Plan

**Objective**: Guard the post-plan router so it never sets POST_PLAN_WORKFLOW_PATH=SIMPLE when hard_mode=true.

**File**: skills/implement/SKILL.md — "Post-plan router" section (~line 989)

**Change**: Add a hard_mode short-circuit before the plan-size evaluation. Match the style of the existing guard at line 911 ("When hard_mode=true, ...").

New text to prepend to the plan-size evaluation paragraph:
  "When `hard_mode=true`, skip the plan-size evaluation and always persist `POST_PLAN_WORKFLOW_PATH=HARD`."

No other files need changes.

**Testing**: Run /relevant-checks (pre-commit + agent-lint). Verify the guard is present via read of the modified section.

**Diff estimate**: ~1 line added.

## Test plan
(no test plan section in plan-file)
