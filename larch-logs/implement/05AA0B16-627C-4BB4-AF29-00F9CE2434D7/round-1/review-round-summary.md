# Review Round 1

- Mode: `diff`
- 10 accepted, 0 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Registry read rejects valid run IDs
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-edge-cases, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Registry writes accept the shared run-ID contract, including uppercase UUIDs, but `read_entry` still uses lowercase-only slug validation. Valid persisted jobs can therefore be unreadable to bgjob waiting, live-work detection, abandoned-job recovery, and statusline logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_2: New runs activate progress too late
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Design and implement startup still bundle reviewer probing into session setup and activate the new progress run only afterward. The previous run can remain visible throughout setup and probing, violating the required clear/setup/activate/probe ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_3: Step 0 abort leaves an active stale pointer
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Step 0 abort cleanup removes the temporary directory without deactivating the effective progress run. An aborted run can remain in `current`, leaving stale statusline breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_4: Teardown can clear progress while same-run work is live
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Implement teardown deactivates the run without checking for matching live, in-budget background jobs. This can hide recoverable work and suppress in-flight status while a same-run daemon is still active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_5: Cancellation terminal cleanup can bypass live-work protection
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Cancellation or failed-clarify terminal paths can deactivate an existing run after final-summary completion without checking whether matching background work remains live, leaving the run hidden while work continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_6: Run-aware review breadcrumbs depend on exported environment state
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: `review_core_body` resolves the owned run ID without a temporary-directory argument. When `LARCH_RUN_ID` exists only in persisted session environment, Step 5 review and CI breadcrumbs can silently stop being written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Plan-review breadcrumbs have the same tmpdir-resolution gap
- **Reviewer(s)**: dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Plan-review `_progress_note` calls `resolve_owned_run_id()` without the design temporary directory, so review-loop breadcrumbs can silently disappear when the child process has persisted but not exported `LARCH_RUN_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_8: Lifecycle deactivation uses the ambient working directory
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-edge-cases, dyn-dyn-run-identity
- **Severity**: major
- **Concern**: Design lifecycle deactivation paths use `Path.cwd()` rather than the trusted persisted consumer repository root. Invocations from plugin-cache or temporary-directory locations can target the wrong clone, leaving the real pointer active or clearing another clone’s pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-run-identity: Address the concern above.


### FINDING_10: Required progress and bgjob regression coverage is missing
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The test suite lacks plan-required coverage for atomic compare-and-clear behavior, activation/deactivation interleavings, matching versus unrelated bgjob liveness, malformed or custom run IDs, run-scoped statusline behavior, and cross-run isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Custom run-ID abandoned-job recovery is untested
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: There is no regression test proving that abandoned-job recovery reads registry entries keyed by a persisted custom `LARCH_RUN_ID`; a resolver regression could select the legacy tmpdir-hash entry and miss live work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
