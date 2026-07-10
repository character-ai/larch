### FINDING_9: [OUT_OF_SCOPE] pause deactivation ignores same-run live background jobs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Pause-save deactivates the run without checking for same-run live background jobs, potentially hiding in-flight progress while work continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_10: [OUT_OF_SCOPE] implement activation uses the ambient working directory
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Implement progress activation uses `Path.cwd()` instead of the trusted consumer repository root, so bootstrap invoked from another directory could activate progress for the wrong clone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_11: [OUT_OF_SCOPE] run-aware writer tests do not cover session-only identity and real writes
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Existing tests export `LARCH_RUN_ID`, mock breadcrumb writes, or both. They do not verify resolution when the run ID exists only in `session-env.sh` or exercise real progress-file writes and cross-run isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] SessionStart harness does not exercise the installed hook path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The SessionStart harness does not pass hook source JSON through the installed hook path, so startup-resume and clear-payload ordering and source-specific reset behavior are not tested end to end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] registry legacy fallback derives clone identity from ambient cwd
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The registry’s legacy `tmpdir`-hash fallback uses `Path.cwd()`, which can bind lookups to the wrong checkout when the current directory differs from the consumer repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
