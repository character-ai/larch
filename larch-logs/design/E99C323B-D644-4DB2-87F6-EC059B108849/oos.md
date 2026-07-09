### OOS_1: Add a design log-publish commit regression beside implement flush tests
- **Description**: Add a design log-publish commit regression beside implement flush tests. Scenario: Implement-only coverage in `test_run_log_flush.py` misses the design pause/final publish path that calls `run-log commit` via `design_log_publish_flow.py`. Pause and final publish can diverge on reachability and waiver handling.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_log_publish_flow.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Add a silent-omission case for missing `review-findings-full.jsonl` when `code-review-tally.json` exists
- **Description**: Add a silent-omission case for missing `review-findings-full.jsonl` when `code-review-tally.json` exists. Scenario: #6027 is the second backing bug. The plan gates that file when code review ran, but mandated tests cover transcript omissions only, so a findings-batch regression could return without a recorded execution issue.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_log_flush.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Fix #6263 transcript capture ENOENT at `_rebase_under_tmpdir`, not only at commit
- **Description**: Fix #6263 transcript capture ENOENT at `_rebase_under_tmpdir`, not only at commit. Scenario: The commit gate blocks silent transcript loss but every run still pays capture failure until the batch path is fixed. Operators see failures instead of captured transcripts.
- **Reviewer**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_batch.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

