### [Plan Review] FINDING_4

### FINDING_4: Clamp stale persisted caps in report and flush paths too
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The report/flush merge path can still carry `round_cap: 3` into persisted report artifacts and refresh batches. That leaves stale caps alive outside the planned read-time clamp behavior, so the shared normalization path still needs to be updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add firm updates for these paths. Clamp any stored int cap to min(stored, difficulty.tier_ceiling(panel_tier)) or reuse one central normalization helper, and update python/tests/report/test_progress_report.py and python/tests/report/test_run_log_flush.py to expect 2.
  - From Codex-Requirements: Add this report test to the firm test updates, expect cap 2, and clamp preserved round_cap values in the shared difficulty merge/write path.


