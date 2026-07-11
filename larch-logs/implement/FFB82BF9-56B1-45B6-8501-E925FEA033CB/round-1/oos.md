### FINDING_1: Filing mode can advance the scan marker before issue creation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: The default-mode marker write and commit fences are unconditional or insufficiently guarded. In `--file` mode, the orchestrator can commit the scan marker before dry-run and issue creation succeed, leaving proposals unfiled and state advanced. Filing mode must explicitly skip the default marker block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_15: [OUT_OF_SCOPE] Failure prose can misreport successful marker commits
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Pre-existing unconditional failure prose follows the marker commit block, so a successful commit may still be narrated as if the marker was not committed. Failure reporting should be scoped to the `COMMIT_RC != 0` branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Retry documentation does not use a durable batch path
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The `/issue` invocation uses a `RUN_DIR` batch path rather than the durable retry copy. A new session may not locate the batch unless the full report is regenerated. Explicit retry and resume flows need documentation or durable-path wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Structural grep harness cannot validate runtime behavior
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: The grep-only harness cannot detect runtime partitioning, parser, deduplication, redaction, retry, or marker-order mistakes. Executable harness or runtime tests would be a separate enhancement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Child `/issue` invocation may lack operator-mode threading
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The child `/issue` invocation does not pass the documented `--operator-invoked` flag at the parent skill boundary. Filing could therefore be refused if the issue sub-skill does not infer operator mode. This follows a pre-existing `/bug` pattern and is not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
