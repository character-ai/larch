## Goal
Implement issue #3981: [IMPLEMENTING] [OOS] Rich header tracks plan-review-slots only, not plan-voter-slots\n\n## Out-of-Scope Observation.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Pragmatic
**Phase**: design
**Vote tally**: rejected

## Description

Rich header tracks plan-review-slots only, not plan-voter-slots. Scenario: during the voting sub-phase the latest artifact is often `plan-voter-slots.ndjson.output-files` while the timing label stays `design Step 3 — plan review`. The report can show N/N reviewers returned and omit voter progress, matching the user's shallow hook snapshot.

**Severity**: latent
**Focus area**: correctness
**Location**: `python/progress_report.py` (`_render_design_plan_review`)

---
*This issue was automatically created by the larch `/design` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
