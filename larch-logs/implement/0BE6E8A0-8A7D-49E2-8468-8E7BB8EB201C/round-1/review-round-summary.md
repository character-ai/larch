# Review Round 1

- Mode: `diff`
- 8 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: stale result files can make retries look DONE
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: `wait` trusts any pre-existing result env, and `start` does not clear stale result state, so a retried step can read an old `BGJOB_RC=0` and complete before the new daemon runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: On start remove stale result env; in wait require result newer than registry START_EPOCH or refuse start when live registry exists
  - From codex-specialist-testing: unlink the prior result env at launch or namespace the result by run identity, and add a stale-file regression test


### FINDING_5: migration test coverage and harness wiring are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing, cursor-specialist-testing
- **Severity**: major
- **Concern**: The migration lacks plan-pinned unit/CLI harness coverage and Makefile wiring, so regressions in wait/daemon behavior and the consumer suites can slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add plan-listed wait/daemon tests and scripts/test-bgjob.sh
  - From codex-specialist-testing: Add test_wait.py cases, scripts/test-bgjob.sh, and Makefile harness wiring per the plan testing strategy.
  - From cursor-specialist-testing: Update the listed suites and add bgjob abandoned-checks cases before or with call-site migration.
  - From cursor-specialist-testing: Register test-hook-deny-run-in-background and test-bgjob in Makefile shards; expand hook tests per plan.
  - From cursor-specialist-testing: Rebind finalize-step5.md and final-summary-emit.md with matching lifecycle tests.


### FINDING_10: `start` can report STARTED before the registry is visible
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-bgjob-lifecycle
- **Severity**: major
- **Concern**: `start` can announce STARTED before the registry row is visible, so an immediate `wait` can misread the launch as DEAD or missing-registry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Write the registry before notifying the parent, or add a short registry creation grace in wait.
  - From cursor-specialist-edge-cases: Write registry before STARTED or return WAIT until registry exists
  - From codex-specialist-edge-cases: Write the registry before signaling STARTED, or add a registry-ready handshake.
  - From codex-specialist-testing: write the registry before returning STARTED or wait for it to exist, and add an immediate-wait regression test
  - From dyn-dyn-bgjob-lifecycle: Publish the registry before returning `STARTED` (or block `start` until the row exists), and treat “registry absent but job plausibly starting” as `WAIT` for a bounded grace period instead of `DEAD`.


### FINDING_11: owner identity capture is optional, so orphan containment can degrade
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-lifecycle
- **Severity**: major
- **Concern**: If owner identity is not captured, orphan containment degrades to budget timeout only, so a killed orchestrator session can leave daemons running until timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Require or derive an owner identity at start and fail closed if it cannot be captured.
  - From cursor-specialist-edge-cases: Default owner to start caller PID
  - From dyn-dyn-bgjob-lifecycle: Treat a missing owner as a start-time error for long steps, or default owner to the `bgjob start` parent PID with full identity capture and fail closed when capture fails.


### FINDING_12: merged result envs can override authoritative `BGJOB_RC`
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Merged result envs can overwrite daemon-authored `BGJOB_RC`, so a failure can be rewritten as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Reject reserved keys from merged rows or write daemon-owned keys last with duplicate protection.
  - From cursor-specialist-edge-cases: Strip reserved keys from merge or use first-wins for BGJOB_RC
  - From codex-specialist-edge-cases: Reject reserved bgjob keys from merged rows or write authoritative bgjob keys last.


### FINDING_13: identity capture can fail after `STARTED`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Identity capture can fail after `STARTED` has already been emitted, leaving a possible live child without a reliable registry/result handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Validate identity before pipe/STARTED or fail start with result env


### FINDING_19: sentinel writes can target arbitrary paths
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Sentinel writes are not constrained to owned roots and can be redirected outside the session tmpdir via TOCTOU or symlink tricks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Constrain sentinels to owned roots and use no-follow atomic writes with containment checks at write time.


### FINDING_20: cwd drift can break `run_id` lookup
- **Reviewer(s)**: dyn-dyn-bgjob-lifecycle
- **Severity**: major
- **Concern**: Deriving `run_id` from cwd makes start/wait pairs unstable if the working directory changes between calls, producing a false missing-registry result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lifecycle: Derive `run_id` only from `tmpdir` (and step), or require and document an explicit `--run-id` on every start/wait pair and have wrappers pass a stable value from session env.


