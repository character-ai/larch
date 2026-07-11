# Review Round 2

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Unsafe predictable launch-envelope temporary path
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The wrapper validates the launch envelope but writes through a predictable temporary path that can be pre-created as a symlink, allowing writes outside `IMPLEMENT_TMPDIR`. Use a no-follow atomic helper or a securely created unique temporary file, and test the symlinked temporary-path case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_2: Unsafe invariant identity sidecar temporary path
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The identity sidecar is written without no-follow protection, so a pre-created symlink at `architectural-invariants.md.identity.env.tmp` can redirect the write before replacement. Render the KVs and use a no-follow atomic write; test the symlinked sidecar temporary path and ensure no consumable outputs are produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Finalize must validate the live checkout head
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Finalize does not validate `FINAL_HEAD` against the live checkout. If another process changes `HEAD` after the lane completes, finalize can emit a reship using stale result identity. Validate `FINAL_HEAD` syntax and require it to equal live `git rev-parse HEAD` before lineage append or result emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Replace the stale dormant-wrapper test
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The unchanged test asserts the retired dormant-wrapper contract, including wrapper-internal bgjob waiting and absent `SKILL.md` wiring. The active cutover removes internal waiting and adds `SKILL.md` wiring, so the targeted pytest run fails. Replace the dormant test with active Step 8 start/wait/finalize integration coverage, including dynamic steps, retries, exhaustion, scope and route selection, invariant recovery, lineage behavior, and transcript boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Add scope-aware failed-run identity tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Python tests do not cover required `CI_FAILURE_SCOPE` emission or conflicting run-ID handling. Add fixture tests for PR/main scope routing, malformed and missing IDs, and conflicting PR/main IDs, ensuring dispatch and wrapper selection fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Add invariant-evidence negative and alternate-input tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Invariant-evidence tests omit plan-listed `DETAIL_FILE`, durable-note-only, duplicate-handoff-KV, and control-character cases. Add the remaining negative and alternate-input tests from the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: Add invariant-primary lane coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Invariant-primary lane tests cover only one identity-mismatch path. Add tests confirming skip-CI-log behavior and successful handling of valid canonical evidence without `FAILED_RUN_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
