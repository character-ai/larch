### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:781-791
- **Concern**: Unloadable fixture still expects snapshot-extract-failed after WI2 ls-tree/show restore. Scenario: After WI2 deleting SNAPSHOT_ROOT yields empty ls-tree enumeration which the loader maps to missing-restored-artifact (plan edge case line 55) not snapshot-extract-failed; flipping only line 790 polarity leaves a failing or wrong-signal test
- **Proposed resolution**: Rewrite the unloadable block to force ls-tree or git show failure (stub exit non-zero) for snapshot-extract-failed or retarget expectations to missing-restored-artifact and use a separate fixture for extract failures

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-pause-resume.sh:140
- **Concern**: Real-git export-ignore test has no stub-bypass contract. Scenario: Harness prepends STUB to PATH so a new real-git case still invokes the git stub and never exercises export-ignore; WI2 regression gap persists
- **Proposed resolution**: Specify running the reproduction in a subshell with stub-free PATH (keep gh stub if needed) and document that requirement in the test block

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:750-752
- **Concern**: Plan add missing-restored-artifact case overlaps existing late-step test. Scenario: Lines 750-752 already assert ERROR=missing-restored-artifact but not LOAD_OK=false or marker retention; a second block duplicates setup
- **Proposed resolution**: Extend 750-752 with LOAD_OK=false and marker-present assertions instead of adding a parallel case
