### [Plan Review] FINDING_5

### FINDING_5: Open-pr resume still writes checks phase before skip
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Resume gating skips checks/postbump blocks but not the earlier checks-phase state write and breadcrumb, so an open-pr handback can regress PHASE and mislead downstream readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Move _resume_plan before any phase-specific _write_ship_state/_breadcrumb, or guard those two lines so they run only when resume.start == fresh


### [Plan Review] FINDING_7

### FINDING_7: Open-pr resume still runs ensure_pr push path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Even after skipping checks/postbump, open-pr resume can re-enter full pr.ensure_pr behavior, including git push or force-push recovery, causing redundant push/CI churn for an already-open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: For open-pr with state PR_NUMBER, hydrate ctx from ResumePlan and jump to the CI loop (or add a resume-only ensure_pr path that reuses PR metadata without push); add a resume test asserting no git push argv in runner.calls

