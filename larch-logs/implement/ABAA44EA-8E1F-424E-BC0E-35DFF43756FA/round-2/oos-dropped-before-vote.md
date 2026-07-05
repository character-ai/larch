### OOS_1: [OUT_OF_SCOPE] in-progress conflict handoff leaves PHASE stale
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-ship-rebase
- **Severity**: latent
- **Concern**: The in-progress conflict branch patches resume metadata, but it can leave `PHASE` inconsistent with the conflict handoff state. If the state file is reused or only partially initialized, resume readers may not see the same `rebase` state that the conflict-fix path expects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] missing regression coverage for phase14 plus in-progress rebase
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ship-rebase
- **Severity**: nit
- **Concern**: The existing tests cover phase14 skipping and in-progress conflict routing separately, but not their overlap. That leaves the guard-order regression unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] write-failure exit path lacks regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-ship-rebase
- **Severity**: nit
- **Concern**: The pre-fix conflict-handoff write-failure path still lacks a regression test, so a write error could regress to the wrong exit behavior or emit `NEXT_ACTION` despite the failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] structure harness does not pin pre-fix-rebase ordering
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The structure harness does not pin the pre-fix-rebase ordering before `ship-pr-ci-fix.md`, so a prose regression could slip through even if the runtime path stays correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] blank RUN_ID state is not covered
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: A future change could let `ship pre-fix-rebase` continue with an empty `RUN_ID`, which would violate the fail-closed contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.

