# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 8 route-exit matrix is still incomplete
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The Step 8 harness still misses the plan-required route-exit allow/block matrix cases, including BGJOB_STATUS=DEAD and missing-sidecar / rc 3 and 6 carve-outs, so regressions in route-exit or wait transitions can still slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Step 8 wrapper should fail closed when merge-result writes fail
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The child currently ignores persist_handoff/write_merge_result_env failures and exits 0, which can publish result env without STEP8_HANDOFF_* KVs and weaken stale-sidecar validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_3: Step 8 terminal results are being discarded on relaunch
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Terminal BGJOB_RC=timeout/orphaned result envs are discarded and replaced by a fresh launch, so evidence is lost and the wrapper can start another ship driver instead of routing failure or stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


