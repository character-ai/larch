# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Replace stale dormant-wrapper test with active cutover coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-lineage
- **Severity**: major
- **Concern**: The existing integration test asserts the retired dormant-wrapper contract: internal `bgjob wait` and no wiring from `SKILL.md`. The shipped cutover instead wires `step-8-ci-fixer.sh` and gives wait ownership to the orchestrator. Replace the stale test with active start/wait/finalize, dynamic `STEP`, retry identity, run selection, exhaustion, invariant recovery, and transcript-boundary coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-lineage: Add the planned fixtures (mocked `bgjob` merge env + `fixer-status.env` + lineage TSV) asserting distinct `STEP` slugs per retry, exactly one next-tier launch, and fail-closed behavior on stale launch/merge identity.


### FINDING_2: Bound the complete invariant-evidence payload
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The evidence materializer bounds the durable note and route detail independently, then adds headers and combines them. Valid near-limit inputs can therefore produce a final rendered evidence body larger than `CI_FIXER_INVARIANT_EVIDENCE_MAX_BYTES`, causing the lane to reject the artifact after materialization. Apply the size bound to the complete rendered body before atomic write and cover near-limit combined inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Validate child directories and canonical path containment
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Child artifact directories are created without symlink and canonical-containment validation. A pre-created `IMPLEMENT_TMPDIR/ci-fixer` symlink could redirect launch envelopes and lineage records outside the owned temporary directory. Reject unsafe child directories and validate handoff, bgjob, launch, lineage, and result paths before use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Emit the documented exhaustion reason
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: When all fixer tiers are exhausted, the wrapper emits `REASON=exhausted` instead of the documented `REASON=ci-fix-exhausted`, producing the wrong terminal result contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Update Step 8 fixer-policy documentation
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `docs/configuration-and-permissions.md` still describes the retired in-session Agent-tool CI-fixer loop and blocking-subprocess behavior. Document the bgjob waterfall, route-aware IDs and `CI_FAILURE_SCOPE`, orchestrator-owned waiting, invariant-primary evidence, `LARCH_CI_FIXER=0`, and `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: Add invariant-evidence rejection and no-partial-artifact tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Current invariant-evidence tests cover only a narrow happy path and stale `HEAD_SHA`. Plan-required rejection coverage is missing for malformed input, symlink paths, duplicate keys, oversized combined output, and no-partial-artifact behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Test CI failure scope and conflicting run IDs
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `CI_FAILURE_SCOPE` handoff and conflicting PR/main run-ID routing lack unit coverage. Wrong scope selection could cause the fixer to select the wrong `FAILED_RUN_ID`, while malformed or conflicting IDs should fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Add invariant-primary lane integration tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The invariant-primary lane mode lacks dedicated tests for skipping CI-log dependence, validating evidence, successful recovery, and raising `LaneClosedError` on invalid evidence or identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
