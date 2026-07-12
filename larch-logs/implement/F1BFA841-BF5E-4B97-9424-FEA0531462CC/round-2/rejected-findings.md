### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: Preflight does not assert issue-view repo forwarding
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The preflight success test does not verify that `--repo o/r` reaches the wrapper-backed issue view.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Assert _stub_issue_view captured argv includes --repo o/r when --repo is passed.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Resume matrix bypasses the production runner seam
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test_gate_resume_matrix` patches private `_gh_issue_view`, so wrapper argv or repo-forwarding regressions in `gate_main` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Replace `_gh_issue_view` patches with `admission.proc.run` stubs matching wrapper argv, consistent with `test_gate_gh_failure_does_not_echo_stderr`.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0
