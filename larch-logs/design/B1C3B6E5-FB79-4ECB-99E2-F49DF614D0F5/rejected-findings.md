### [Plan Review] FINDING_5

### FINDING_5: Pin the skip-approve contract in the structural harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The structural harness needs to assert the `--skip-approve` audit contract in `skills/design/SKILL.md`, not only the `approval-gates.md` rewrite, or stale unconditional auto-approve prose can survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add structural checks that `skills/design/SKILL.md` requires audit completion, binds `strong_audit_dissent`, and forbids unconditional Gate C auto-approve after Presentation only.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_log_publish_flow.py:140-150
- **Concern**: [SCOPE-REDUCTION] Plan adds plan-before-review.txt but omits design-log publish exclusion. Scenario: The publisher copies every non-excluded top-level DESIGN_TMPDIR file into larch-logs/design/<RUN_ID>/ (see _publish_excluded and test_design_log_publish_flow.py kept list). plan-before-review.txt is only a Gate C comparison baseline; the issue asks to persist accepted-plan-findings-audit.md, not a superseded plan snapshot. Committed logs would carry stale pre-review plan text beside final plan.txt.
- **Proposed resolution**: Add ### UPDATED: python/larch/design/design_log_publish_flow.py: put plan-before-review.txt in _PUBLISH_EXCLUDE_TOPLEVEL_NAMES (same class as issue-body.txt). Extend python/tests/design/test_design_log_publish_flow.py excluded list. Note in plan-review.md or docs/run-logs.md that the snapshot is tmpdir-only.


