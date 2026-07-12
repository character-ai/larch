### FINDING_3: [OUT_OF_SCOPE] Missing CI harness registration
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-ci-fixer.sh` is not registered in a `test-harnesses-*` shard, so default-branch CI will not run the expanded finalize-wrapper fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Missing timeout and orphaned crash tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No pytest covers `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` through `_validate_crash_identity` or `--finalize-crash`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Missing salvage-reship integration test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No `main()` test combines a prior foreign run-A ledger row with a salvage-reship persistence path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
