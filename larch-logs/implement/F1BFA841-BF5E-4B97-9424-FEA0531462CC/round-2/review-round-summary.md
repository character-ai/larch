# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_4: Missing direct Step 0 wrapper-read coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests continue to mock `_read_json_issue` wholesale and do not verify wrapper fields, optional `--repo` forwarding, label parsing, or non-zero failure propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add focused _read_json_issue tests for fields, optional repo forwarding, clarification-label parsing, and failure behavior.
  - From cursor-specialist-edge-cases: Add a unit test patching gh.issue_view_field_read/proc.run to verify canonical argv and that step0_route_main returns 1 on non-zero wrapper rc.
  - From codex-specialist-edge-cases: Add focused _read_json_issue tests with a stubbed wrapper.
  - From cursor-specialist-testing: Add focused tests patching design_step0.gh.issue_view_field_read or design_step0.proc.run that call _read_json_issue directly and verify canonical argv, label parsing, repo forwarding, and non-zero failure propagation.
  - From codex-specialist-testing: Add tests for wrapper arguments with and without repo, label parsing, and wrapper failure behavior.


### FINDING_5: Blocker fail-closed E2E test stubs the wrong seam
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: `test_gate_blocker_subprocess_failure_fails_closed_e2e` stubs `_run` for issue viewing even though production uses `proc.run`, allowing environmental issue-view failures to mask the blocker subprocess failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Stub proc.run or gh.issue_view_field_read for the view leg; keep _run for blocker CLI only; assert ADMISSION_ERROR from blocker failure after stubbed view success.
  - From cursor-specialist-testing: Stub admission.proc.run for the view leg (return success JSON), keep _run failing only for the blocker subprocess, and assert a blocker-specific error (not any ADMISSION_ERROR=).
