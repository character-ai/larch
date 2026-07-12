### [Plan Review] FINDING_2

### FINDING_2: Step 5c child mode cannot publish adapter merge rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Child mode still uses `exec`, preventing post-Python publication of the Step 5c status envelope to the adapter merge environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace child `exec` with a normal Python invocation, then atomically publish `.design-step5c-status.env` (or equivalent rows) to the injected merge path before exiting; mirror the non-exec terminal-publish pattern planned for Step 3.


### [Plan Review] FINDING_3

### FINDING_3: Step 5c publish-env failure lacks a terminal status envelope
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The `_step5c_safe_publish_env` failure branch can return without authoritative status rows, leaving the adapter with incomplete publish and plan-write results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the planned `design_step5c.py` terminal-envelope work to cover this branch: write a complete refusal/failure status envelope (including `PUBLISH_RC`, `PLAN_WRITE_OK`, `PUBLISH_OK`, `CLEANUP_ELIGIBLE=false`) before returning.


### [Plan Review] FINDING_7

### FINDING_7: Step 3 re-entry depends on undocumented sentinel clearing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Re-entry correctness depends on `design-step3-entry-state.sh` clearing the prior result before `bgjob adapt`; removing wrapper-local deletion without documenting this dependency risks stale reattachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one line to `design-step3-review.md` and `test-design-structure.sh`: reentry must still run `design-step3-entry-state.sh` (or equivalent sentinel clearing) before `bgjob adapt` so a prior terminal result cannot satisfy a fresh re-run review.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-design-step3b-tail.sh:1
- **Concern**: [SCOPE-REDUCTION] The plan adds the dedicated Step 4 harness previously classified out of scope. Scenario: This expands the firm diff and Makefile surface beyond the issue’s required structure and fence-shape verification
- **Proposed resolution**: Remove the new harness and Makefile target; keep the required existing harness updates


