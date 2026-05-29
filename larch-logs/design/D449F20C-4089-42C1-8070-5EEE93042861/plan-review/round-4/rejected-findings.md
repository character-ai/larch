### [Plan Review] FINDING_4

### FINDING_4: Test Helper Duplicates Production Cursor Logic
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The planned integration test inlines Step 3 cursor arithmetic already implemented by `snapshot-plan-round.sh`, creating drift risk between the harness and production behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Call snapshot-plan-round.sh read-cursor / write-cursor in the case instead of inlining cursor arithmetic


### [Plan Review] FINDING_6

### FINDING_6: Passive-Summary Continue Wording Drifts Across Files
- **Reviewer(s)**: Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync
- **Severity**: latent
- **Concern**: The planned SKILL.md and approval-gates.md wording for passive-summary Continue is not identical, leaving ambiguity about Step 3.6, Step 3b, Gate C, and later re-run ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync: Use one shared sentence in both files, e.g. Passive-summary Continue routes through Step 3.6 before Step 3b, then Step 4 and Gate C; any Gate C re-run is a later fresh Step 3 entry.


### [Plan Review] FINDING_8

### FINDING_8: Tally-Only Statuses Missing Step 3.6 Routing
- **Reviewer(s)**: Cursor-dyn-status-matrix, Codex-dyn-status-matrix
- **Severity**: important
- **Concern**: The plan omits explicit Step 3.6 dispositions for `TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings` and `skipped-cap-reached`, leaving all-empty review output and cap-entry bypass routing incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-status-matrix, Codex-dyn-status-matrix: Add TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings to the zero-findings route-through text, and TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached to the cap-reached skip text.

