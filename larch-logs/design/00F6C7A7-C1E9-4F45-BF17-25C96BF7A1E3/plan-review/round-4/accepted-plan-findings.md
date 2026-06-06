### FINDING_3: STALL_TRACKING optional on STATUS=bailed hard-bail skips stall report
- **Reviewer(s)**: Cursor-dyn-step2-bail-coverage
- **Severity**: important
- **Concern**: `STALL_TRACKING` is left optional on `STATUS=bailed` hard-bail. Scenario: dispatcher `STATUS=bailed` with `REASON=wrapper-validation-failure` sets `FINAL_BAIL_REASON`/`IMPLEMENT_BAIL_REASON` but the orchestrator omits `STALL_TRACKING`; Step 18a fast-paths with no stall detected and the stall report never shows the bail reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-step2-bail-coverage: Require unconditional STALL_TRACKING=true on the new STATUS=bailed bullet (match §2.1.5:616 and main-branch-post-dispatch:630), not if needed

