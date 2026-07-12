### FINDING_9: Step 3 runtime authority remains stale
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `plan-review-runtime.md` still describes wrapper-local lifecycle management and direct `bgjob start`, conflicting with the planned `bgjob adapt` ownership model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/plan-review-runtime.md` stating parent wrappers delegate to `bgjob adapt`, completed results reattach via adapt `DONE`, fresh launch clears `.completed/step-3` only through `--clear-on-fresh`, and orchestrator continuation still requires `bgjob wait` plus `bgjob/design-step3-review.result.env` parsing.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: `design-step-final-summary` remains on legacy `bgjob start` while Steps 3/4/5c move to `bgjob adapt`
- **Description**: `design-step-final-summary` remains on legacy `bgjob start` while Steps 3/4/5c move to `bgjob adapt`. Scenario: After this change, design will still carry one bespoke start/wait/merge-env lifecycle for final summary. That is extra surface area, but it is outside the stated three-script scope and non-goals.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:182
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

