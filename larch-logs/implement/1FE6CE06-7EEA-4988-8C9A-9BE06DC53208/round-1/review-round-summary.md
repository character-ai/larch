# Review Round 1

- Mode: `diff`
- 7 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Divergent embedded gh stubs can mask harness regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-log-publish.sh` and `scripts/test-design-multi-round-integration.sh` maintain separate `gh pr checks` stubs with different strictness, especially around `--json`, `--watch`, and `--fail-fast`, so one harness can pass while the other would catch an unsupported CLI shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.


### FINDING_12: Non-array gh JSON errors poll until timeout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Non-array JSON from `gh pr checks` is treated as “not registered,” causing auth/rate-limit/API-error responses to sleep and eventually surface as registration timeout rather than failing fast with a clear diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Stale-head coverage is not integrated with pause-reuse force-push flow
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: important
- **Concern**: Stale-head behavior is covered by stub knobs but not by the pause-reuse / force-push fixture, so regressions in the combined recovery path could escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.


### FINDING_15: Post-push registration `mktemp` failures break recovery envelope
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: If registration-phase `mktemp` fails after a successful push, the script emits `PUBLISH_OK=false` and exits `0` without `RECOVERY_BRANCH`, violating the documented post-push failure contract and hiding recovery information.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.


### FINDING_25: Publish tail drops PR and recovery envelope fields
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` parses and persists only part of the `design-log-publish.sh` envelope, omitting `PR_NUMBER`, `PR_URL`, and `RECOVERY_BRANCH`; this hides successful flush PR details in final summaries and hides recovery pointers on publish failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.


### FINDING_4: Never-registered probe expectation is hardcoded
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The never-registered test hardcodes `31` probes without tying it to the production `REG_TIMEOUT` / `REG_INTERVAL` formula, making future timeout changes non-obvious.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Pause recovery tests may not reach the intended merge-failure path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Several pause-recovery publish tests omit `TEST_CLONE_ROOT` / `TEST_MERGE_BRANCH`, so after headRefOid binding they can fail during registration instead of exercising `GH_STUB_MERGE_RC` merge-failure semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


