### FINDING_2: Distill log must not tail-truncate failures
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The distill-log path appears to rely on tail-only CI log collection, which can omit failures from multi-job runs and leave the fixer with incomplete evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement distill_log_main against gh run view --log-failed with per-job section parsing head/tail caps and shard dedupe; forbid delegating to collect_failed_logs or other repo-wide tail truncation helpers


### FINDING_6: Stale CI_AGENTIC_FIX_MAX_CYCLES assertions after config cleanup
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The config cleanup will break existing tests unless the stale CI_AGENTIC_FIX_MAX_CYCLES assertions and monkeypatches are removed or rewritten alongside the symbol deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: The plan removes `CI_AGENTIC_FIX_MAX_CYCLES`, but this test still asserts it, and `python/tests/implement/test_ci_monitor.py:3325-3334` still monkeypatches it. The suite will go red as soon as config.py drops the symbol. Replace those checks with the new `CI_FIXER_*` constants or delete the affected tests in the same change set.


