### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ship.py
- **Concern**: Empty-head_sha ship integration test must exercise real write_guideline_ship_outcome validation, not a write mock. Scenario: The plan mirrors test_open_pr_resume_guidelines_gate_write_failure_stalls_before_ensure_pr, which monkeypatches write_guideline_ship_outcome to raise OSError. Copying that pattern would green the test without running the new blank-head_sha guard in ship_guidelines.py.
- **Proposed resolution**: State explicitly: monkeypatch git.try_rev_parse (or equivalent) to return "" so compose_head_sha is blank, call the real write_guideline_ship_outcome, and assert Outcome.STALLED plus ensure_pr/flush_logs_pre not called. Do not mock write_guideline_ship_outcome for this case.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/issue/test_audit_runs.py
- **Concern**: Failure modes require both reachability call paths to be tested, but the test list only names guideline-scan regressions. Scenario: Failure modes say Step 8 reachability changes affect both the guideline scan and `_scan_required` step8 gating and call for focused tests per path. The Testing strategy lists guideline-scan and step9a1 chain regressions only. A missed `pr=` at `_scan_required` line 699 would not be caught by scan-only coverage.
- **Proposed resolution**: Add a direct `implement_step8_reachable(..., pr=...)` unit test or a `required-file-presence` regression with a `step8`-conditioned row that exercises the `_scan_required` call path with stale-bail plus manifest `pr_number` evidence.
