# Review Round 1

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Unavailable notes are incorrectly treated as stale
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `NOTE_STATE_UNAVAILABLE` is treated as stale by `_note_fingerprint_stale`, so unavailable notes accepted by `note_consumable` at the matching HEAD are discarded before ship or compose classification. This forces reassessment instead of preserving the intended unavailable fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_2: Coverage advancement is not transactional
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-coverage-safety
- **Severity**: major
- **Concern**: `_advance_note_coverage` replaces the snapshot and metadata in separate operations. If metadata persistence fails after snapshot replacement, durable state contains a new snapshot paired with old HEAD, fingerprint, and identity metadata, violating the requirement that failed advancement leave state unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-coverage-safety: Address the concern above.


### FINDING_7: Durable violation state can be downgraded by unavailable refresh
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: An unavailable-note write or invariant unavailable result can overwrite or supersede a previously persisted authored violation. Downstream ship classification then emits dropped/unavailable instead of preserving the blocking violation. Existing tests cover isolated classifier precedence but not durable-note or ship-gate integration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Coverage advancement does not validate the stored base-to-HEAD snapshot
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Advancement trusts a self-consistent persisted snapshot and fingerprint without proving that they represent the actual `BASE_REF`-to-stored-`HEAD_SHA` diff. A stale but internally consistent artifact can therefore be promoted across docs-only or log-only commits and incorrectly reused for unassessed code changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: Coverage refresh can overwrite the authored identity
- **Reviewer(s)**: dyn-dyn-coverage-safety
- **Severity**: major
- **Concern**: For prior-format notes, `_advance_note_coverage` updates compatibility `DIFF_FINGERPRINT` before durable metadata generation, while that field is also the fallback for `AUTHORED_DIFF_FINGERPRINT`. The first safe HEAD advance can therefore rewrite the authored identity to the new covered fingerprint, violating the requirement that mechanical advancement preserve authorship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-coverage-safety: Address the concern above.


### FINDING_11: Compose integration lacks safe-advance reuse coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: No integration test proves that `prepare_compose_assessment` or `prepare_invariant_compose_assessment` returns `status=current` after safe incremental HEAD advancement. Step 8 could continue forcing reassessment even if `note_consumable` advances successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Incremental Git failure branches lack negative tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The fail-closed branches for nonzero Git exit status, malformed NUL output, and decode errors are not covered by regression tests, so those safety behaviors could regress without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
