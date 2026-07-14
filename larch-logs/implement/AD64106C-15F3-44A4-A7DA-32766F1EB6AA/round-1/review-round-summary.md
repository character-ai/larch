# Review Round 1

- Mode: `diff`
- 3 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_3: Pending frontier exceeds 1000-SHA state limit
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A capped sweep with more than 1000 pending eligible SHAs cannot commit or resume its pending frontier because `write_sweep_state` rejects it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Missing prefetch sweep-flag isolation tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests do not verify that `prefetch` rejects `--sweep` and `--sweep-max`, leaving flag-isolation regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_5: Missing capped-resumption end-to-end coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests do not persist a real pending frontier through report state commit and verify that a subsequent prepare selects those SHAs before newer work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
