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


