# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_12: `larch_log_flush_main` drops `_commit_run` stderr on non-zero exit
- **Reviewer(s)**: dyn-dyn-warning-contracts-output.txt
- **Severity**: important
- **Concern**: `larch_log_flush_main` now warns on `_commit_run` non-zero exit (`WARN: larch-log flush failed: rc={result.returncode}`) but never emits `result.stderr` (`python/run_logs.py:2301-2302`). Tree-publish refusals from `_replace_staged_tree_or_error` (e.g. symlink or non-directory `dest` at `1842-1855`) are returned only via `_copy_tree_to_repo` → `_commit_run` as `CommandResult.stderr` (`1972-1973`), not via direct `print()`. During flush, operators see an opaque `rc=1` while the refusal reason (`refusing to replace symlink destination: …`) is dropped, even though the branch adds new publish-failure paths that use that channel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-warning-contracts-output.txt: When `result.returncode != 0`, include `result.stderr.strip()` in the flush warning (or print `result.stderr` to stderr before returning `0`), and add a unit test mirroring `test_larch_log_flush_warns_when_stage_fails` that forces `_commit_run` to return `rc=1` with a populated stderr.


