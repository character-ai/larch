# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: missing run_ship-level re-entry coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The pre-PR stall recovery path is only covered by helper-level tests. There is no `run_ship()` integration test proving the de-terminalized context is in place before the first `flush_logs_pre()`, so regressions in placement, context reassignment, or the pre-terminal guard could still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_5: legacy pre-terminal direct-commit path lacks coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The direct-commit block test only covers `REFRESH_SKIP_PRETERMINAL_OUTCOME`, not the older `commit-failed` plus pre-terminal compatibility path that is still accepted. A later cleanup could break older logs or monkeypatched tests that emit the legacy reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


