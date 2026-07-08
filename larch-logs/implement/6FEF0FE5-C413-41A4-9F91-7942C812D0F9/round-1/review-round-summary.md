# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 8 live registry rows can be stale-unlinked
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Step 8 rejoin logic treats a registry row as stale unless both the child and daemon are live, so a child-live/daemon-dead or daemon-live/child-dead entry can be unlinked and a second ship driver started while the original work is still in flight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Treat any identity-valid live child or daemon as a rejoin and call bgjob wait; unlink only when both are dead and no result env exists.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Step 8 harness lacks route-exit matrix coverage
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The Step 8 wrapper harness never pins the route-exit allow/block matrix, so regressions around BGJOB_RC carve-outs, DEAD timeouts, orphaned runs, and missing sidecars could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add post-DONE stub tests for route-exit success with rc 3/6 and failure on DEAD timeout orphaned and missing sidecars.
  - From cursor-specialist-plan-fidelity-auto: Add route-exit allow/block matrix tests to test-step-8-ship.sh per plan (rc 3/6 allow; timeout/orphaned/missing/stale/DEAD block) or amend the plan if dispatch-only pins are authoritative.


### FINDING_6: Structure harness lacks the Step 8 route-exit prose pin
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The structure harness does not pin the prose assertion that route-exit is allowed without the BGJOB_RC=0 gate, so docs drift would not fail that check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Add require(skill, ...) pins for the Step 8 Do not require BGJOB_RC=0 / authoritative driver-rc prose.


### FINDING_8: Timeout/orphaned result envs are treated as resumable
- **Reviewer(s)**: dyn-dyn-bgjob-handoff
- **Severity**: major
- **Concern**: `step8_result_env_rejoinable()` will rejoin any result env that still matches the handoff rc, so terminal failures like `timeout` or `orphaned` can block legitimate retries by sending the wrapper back into `bgjob wait` instead of starting fresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-handoff: In step8_result_env_rejoinable(), reject rejoin when BGJOB_RC is timeout or orphaned (and optionally other non-resumable terminal tokens), so the launcher clears stale result env / handoff sidecars and starts a new ship driver; add a harness case that stubs a timeout result env plus matching sidecars and asserts the wrapper reaches bgjob start, not bgjob wait.


