# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_10: implement commit error-path contracts not covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Implement commit error-path contracts from deleted `test-commit-implementation.sh` are not covered. Git commit failure may stop emitting `COMMITTED=false`/`ERROR=`, and `--stage-all` now gets argparse's generic error instead of the Step 5 redirect hint operators relied on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest for failed git-commit.sh, missing `--message` (with hint), and `--stage-all` (exit 2, `COMMITTED=false`, review-and-fix hint).


### FINDING_14: test-implement-structure.sh require() points at nonexistent path
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The structure harness calls `require('python/cli.py implement commit', ...)`, but `require()` treats its first argument as a filesystem path and calls `Path(path).read_text()`. `make test-implement-structure` and the `test-harnesses-12` shard will fail with `FileNotFoundError` because no file named `python/cli.py implement commit` exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Point the assertion at the real migrated implementation file, for example `python/implement_dispatch.py`, and keep the needle `LARCH_TIMING_LEDGER` there.


### FINDING_6: Malformed-manifest recovery matrix (M2/M16/M18/M19) not ported to pytest
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted shell harness coverage for malformed-manifest recovery (including M16 `PRELAUNCH_INDEX_NONEMPTY` blocking recovery) was not fully ported to pytest while the large shell harness was removed. Regressions in prelaunch staged-index gating, empty post-launch delta bail, baseline write-once across resume, or `schema_version != 1` hard-bail could allow wrong recovery or commits via the recovery path without CI catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add pytest coverage that stages a file before external dispatch, triggers malformed-manifest recovery, and asserts bail without `RECOVERY_FROM`.
  - From cursor-specialist-testing-output.txt: Add pytest cases for prelaunch staged index blocking recovery, empty post-launch delta staying bailed, baseline write-once across resume, and `schema_version != 1` hard-bail without `RECOVERY_FROM`.


### FINDING_7: Additional high-risk step2 dispatch transitions (M17, retry, OOS e2e) not ported
- **Reviewer(s)**: dyn-dispatch-parity-output.txt
- **Severity**: important
- **Concern**: Beyond the recovery matrix gaps, the pytest replacement does not pin several high-risk dispatcher transitions the retired harness enforced: M17 (rename/copy porcelain rows recover destination path only via `compute_recovery_paths` / `_parse_porcelain_z`), launcher single-retry on clean post-failure state (`python/implement_dispatch.py:903-916`), and end-to-end `manifest-oos-materialization-failed` through `step2_dispatch_main` with `LARCH_TEST_MATERIALIZE_FORCE_FAIL` (only `_materialize_oos` is unit-tested). Regressions in recovery path selection, retry semantics, or OOS fail-closed behavior can ship despite green pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-parity-output.txt: Port M16/M17 and the retry/OOS-fail-closed cases from the deleted harness into `python/test_implement_dispatch.py` as focused `step2_dispatch_main` / `compute_recovery_paths` tests that assert exact `STATUS`/`REASON`/recovery-triplet envelopes.


### FINDING_9: run-dispatch wrapper coverage essentially one test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After deleting `test-run-step2-dispatch.sh`, implement `run-dispatch` wrapper coverage is essentially one cursor-drift test. Argv validation or `--answers` passthrough regressions in `run_dispatch_main` would not fail CI despite plan acceptance requiring run-dispatch routing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port the deleted wrapper harness: missing tmpdir/session-env/plan/feature, invalid `CURSOR_PRESENT`, bad `--answers` path, and answers forwarded into child step2-dispatch argv.


