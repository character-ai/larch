Reviewing the cited test file to normalize the three findings accurately.
### FINDING_1: Unloadable fixture expects wrong error after snapshot delete
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: important
- **Concern**: The unloadable-snapshot block at lines 781–791 still asserts `ERROR=snapshot-extract-failed` after WI2 deletes `SNAPSHOT_ROOT` and relies on ls-tree/show restore. In that scenario, empty ls-tree enumeration maps to `missing-restored-artifact` (plan edge case line 55), not `snapshot-extract-failed`. Flipping only line 790 polarity would leave a failing test or assert the wrong failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-line-accuracy: Rewrite the unloadable block to force ls-tree or git show failure (stub exit non-zero) for snapshot-extract-failed or retarget expectations to missing-restored-artifact and use a separate fixture for extract failures

### FINDING_2: Real-git export-ignore test lacks stub-bypass contract
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: important
- **Concern**: A planned real-git export-ignore reproduction has no stub-bypass contract. The harness prepends `STUB` to `PATH` at line 140, so a new real-git case would still invoke the git stub and never exercise export-ignore behavior; the WI2 regression gap would persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-line-accuracy: Specify running the reproduction in a subshell with stub-free PATH (keep gh stub if needed) and document that requirement in the test block

### FINDING_3: Planned missing-restored-artifact case duplicates late-step test
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: nit
- **Concern**: A planned `missing-restored-artifact` case overlaps the existing late-step test at lines 750–752. That block already asserts `ERROR=missing-restored-artifact` but not `LOAD_OK=false` or marker retention; adding a second parallel block would duplicate setup without new coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-line-accuracy: Extend 750-752 with LOAD_OK=false and marker-present assertions instead of adding a parallel case
