### FINDING_12: [OUT_OF_SCOPE] Teardown liveness guard observation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Teardown deactivation does not check for same-run live in-budget bgjobs, which could remove statusline visibility while work continues. This overlaps the in-scope teardown concern but was explicitly marked out of scope by this reviewer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Missing ownership and interleaving tests
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-run-identity
- **Severity**: minor
- **Concern**: Tests do not cover deactivate ownership mismatches or deterministic activation/deactivation lock interleavings, leaving compare-and-clear race regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Registry clone identity falls back to ambient cwd
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `read_for` can derive clone identity from `Path.cwd()` when using the temporary-directory hash fallback, allowing registry lookup to bind to the wrong checkout when cwd differs from the consumer repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] SessionStart harness does not test source input
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The SessionStart harness omits source input, so session-reset behavior is not exercised through the hook path. This was identified as a pre-existing contract gap outside the changed diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Clear can reset foreground progress
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The `clear` path can wipe the current pointer during foreground work without a bgjob. This was noted as a previously accepted product tradeoff rather than a change-specific issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Run-aware writer tests are mock-based
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: New run-aware writer tests mock `append_breadcrumb_for_run` rather than exercising real progress-file integration, providing weaker coverage of the planned reproduction scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Review-core environment-resolution follow-up
- **Reviewer(s)**: dyn-dyn-run-identity
- **Severity**: minor
- **Concern**: Review-core `_progress_note` has the same environment-only run-ID resolution pattern and may fail to write breadcrumbs in bgjob children that do not export `LARCH_RUN_ID`. This was marked for follow-up by this reviewer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-identity: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Missing real progress-file integration tests
- **Reviewer(s)**: dyn-dyn-run-identity
- **Severity**: minor
- **Concern**: Run-aware writer tests do not exercise real progress-file integration, so regressions in persisted breadcrumb behavior could remain undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-identity: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Abandoned-check implementation location differs from the plan
- **Reviewer(s)**: dyn-dyn-run-identity
- **Severity**: minor
- **Concern**: The abandoned bgjob probe remains in `python/larch/state/_tokens.py` rather than the plan-referenced report-token location, and explicit custom-run-ID coverage was not added in this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-identity: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
