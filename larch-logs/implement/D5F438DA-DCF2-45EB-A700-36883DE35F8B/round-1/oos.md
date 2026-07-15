### FINDING_3: [OUT_OF_SCOPE] Other agent-lint exclusions may be stale
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Additional `python/test_*.py` exclusion paths appear stale relative to the current `python/tests` layout. Audit them in a follow-up migration pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Pytest detection is limited to literal recipe text
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Pytest detection can miss Bash wrappers or delegation paths that do not contain the literal `pytest` in the shard recipe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Manifest reconciliation is not reflected in the plan heading
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The plan names `scripts/residual-bash-paths.txt`, but the branch does not touch it; reviewers observed no functional manifest drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Documentation retains retired shard rows
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Existing documentation still references retired `test-harnesses-8/9/11` shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Orphan self-test coverage changed wording
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The self-test now checks “non-leaf in shards” rather than the legacy orphan wording, leaving the orphan reporting path without dedicated coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
