### FINDING_1: [OUT_OF_SCOPE] Missing focused issue-create wrapper tests
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `python/tests/issue/test_issue_create.py` does not directly test the new `gh.issue_view_field_read` / `gh.issue_close` wrapper seam, leaving repo forwarding and artifact-path regressions easier to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add focused stubs on the `gh` seam like the preflight/bootstrap tests, per the plan.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Unmigrated raw GitHub issue-view call sites
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Raw `gh issue view` call sites remain in sibling modules outside this migration, so they do not inherit the shared retry and error behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Track as a follow-up repoint sibling if full contract unification is the long-term goal.
  - From cursor-specialist-edge-cases: Track as follow-up migration; out of scope for this branch.
  - From cursor-specialist-testing: Handle in a later repoint issue


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Missing direct Step 0 wrapper-read test
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `design_step0._read_json_issue` lacks a direct test exercising `gh.issue_view_field_read` forwarding and clarification-label parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add one parametrized unit test on `_read_json_issue` with a fake `gh.issue_view_field_read`, similar to `test_reconcile_post_recovery_comment_uses_lifecycle_wrappers`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] No lint ratchet for raw issue commands
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: No committed mechanical guard prevents reintroducing raw `gh issue view|edit|close` argv outside `gh.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a scoped lint or structural test per plan acceptance grep.
  - From cursor-specialist-testing: Add optional lint ratchet in a separate change outside this feature scope


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
