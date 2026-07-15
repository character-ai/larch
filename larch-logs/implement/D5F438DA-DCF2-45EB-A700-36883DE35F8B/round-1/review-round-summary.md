# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Shard guard misses transitive pytest execution
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The shard guard classifies recipe text without traversing prerequisite or `$(MAKE)` delegation paths, allowing Bash-shard targets to execute pytest indirectly and duplicate Python test coverage. Add prerequisite-graph traversal and self-tests for indirect delegation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Final-report lint exclusion uses the wrong path
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The agent-lint exclusion names `python/test_final_report.py`, while the behavioral authority is `python/tests/report/test_final_report.py`, making the exclusion ineffective.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: Branch-protection documentation omits the aggregate gate
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Branch-protection guidance requires matrix legs instead of the stable `test-harnesses-gate` aggregate gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Auto-reporting documentation has incorrect shard mappings
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The auto-reporting harness section assigns targets to incorrect or nonexistent shards and misclassifies a pytest-only target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_10: Manifest-listed Bash harnesses may be omitted from CI
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Bash harnesses listed in `scripts/residual-bash-paths.txt` are not represented in the Makefile shard inventory, so `make test-harnesses` may silently omit regression harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_11: Documentation has stale shard assignments
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Multiple linting-documentation rows reference obsolete shard numbers, nonexistent targets, or pytest-only targets as harness prerequisites, conflicting with the five-shard Makefile inventory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
