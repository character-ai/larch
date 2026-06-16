# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Missing main()-level orchestration integration tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-rebalance-safety-output.txt
- **Severity**: important
- **Concern**: Plan-required monkeypatched `main()` integration tests for pre-write gate ordering, partition failure without assignments write, assignments-write failure rollback, and verification dispatch (`--kind python` / `--kind all`) are largely absent from `python/test_rebalance_script.py`. A regression that writes before gates pass, skips rollback, or omits `_trigger_verification_runs` could ship with no failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add monkeypatched integration tests from the plan: pre-write abort before write_shards/_write_assignments_json partition-failure skips assignments writer assignments-write failure reverts Makefile _trigger_verification_runs after PR for python/all harness verification failure still exits 0
  - From dyn-rebalance-safety-output.txt: **Suggested fix:** Add monkeypatched `main()` integration tests that assert call order and filesystem bytes for the partition-failure, assignments-write-failure, dirty-artifact, and verification-dispatch paths described in the plan.


### FINDING_7: Artifact cleanliness gate ignores git status failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_assert_artifact_paths_clean` in `.claude/skills/rebalance-tests/scripts/rebalance.py` ignores `git status --porcelain` failures. If `git status` returns rc=128 with empty stdout (e.g. index lock), the script treats the path as clean and can overwrite dirty Makefile or shard-assignment edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check result.returncode and raise ShipError with stderr before considering stdout cleanliness.


### FINDING_8: _revert_written_paths ignores git rollback command failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-rebalance-safety-output.txt
- **Severity**: important
- **Concern**: `_revert_written_paths` in `.claude/skills/rebalance-tests/scripts/rebalance.py` discards return codes from `git restore --staged` and `git checkout --`. A failed rollback (e.g. after a hook failure leaves paths staged) can exit through the normal `ShipError` path while leaving kind-selected artifacts dirty or staged, breaking the script’s safety promise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check each rollback command return code, stop on failure, and surface a ShipError naming the path and failed git command.
  - From dyn-rebalance-safety-output.txt: **Suggested fix:** Check each git helper’s `returncode` (or call a shared `_ensure_success` wrapper), raise `ShipError` naming the path and stderr on failure, and only print the final error after rollback is confirmed or a second loud “rollback failed” message is emitted.


