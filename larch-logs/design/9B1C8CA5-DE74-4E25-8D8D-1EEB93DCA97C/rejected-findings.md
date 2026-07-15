### [Plan Review] FINDING_1

### FINDING_1: Consumer monkeypatch bindings are not explicitly preserved
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Retargeted tests may patch consumer-module attributes that production code never binds, causing `monkeypatch.setattr` to fail or miss the actual call path after facade shrinkage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For each consumer listed above, add an explicit plan step: bind owner modules on the consumer (from larch.report import run_log_manifest, run_log_commit, run_log_flush, run_log_batch as applicable) and call only through those attributes (run_log_manifest.effective_run_id, run_log_flush.flush_logs_pre, run_log_batch.append_execution_issue). Align with G-Py-14 by keeping typed fakes on the patched consumer binding.


