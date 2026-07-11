# Review Round 2

- Mode: `diff`
- 7 accepted, 3 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Fresh Step 8 path does not emit terminal re-author results
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: The fresh-attempt Step 8 loop lacks an `emit-reauthor` branch. A valid first-attempt `re-author-required` result can fall through to retry or fail-closed behavior, consuming attempt 2 and preventing reassessment routing. Add terminal-envelope coverage for fresh and rejoin paths, including no retry and no ship handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Add an emit-reauthor branch that emits the terminal envelope and exits 0.
  - From cursor-specialist-edge-cases: Add emit-reauthor arm to the fresh loop and harness coverage for first-start terminal emit
  - From codex-specialist-edge-cases: Add an `emit-reauthor` branch that emits the terminal envelope and exits; add fresh-path no-retry coverage.
  - From cursor-specialist-testing: Add emit-reauthor branch that emits terminal stdout and exits 0.
  - From dyn-dyn-gate-authority: Add an `emit-reauthor)` branch in the fresh loop that mirrors rejoin: call `emit_terminal_stdout` and `exit 0` with no retry, and add harness coverage for a first-run child that returns `ARCHITECTURAL_ASSESSMENT_STATUS=re-author-required`.


### FINDING_2: Unavailable persistence can overwrite a preserved invariant violation
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: `write_unavailable_note` can preserve an authored invariant-violation note, while `_persist_unavailable` still writes an unavailable outcome sidecar. The note and sidecar can then disagree, allowing `_already_handled` to treat the violation as handled and skip reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-gate-authority: When `write_unavailable_note` preserves a violation, skip the unavailable `_write_outcome` path entirely (same as `_preserved_invariant_violation`), or fold all preservation into `_preserved_invariant_violation` and remove the weaker metadata-only early return from `write_unavailable_note`.


### FINDING_3: Unavailable preservation lacks full identity and sidecar validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: Unavailable handling may preserve a stale or metadata-only violation based only on authored note state, note presence, and `ASSESSMENT_KIND=violation`. It does not require current consumability, valid outcome metadata, authored-outcome validity, or matching head/diff identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Require full current identity and sidecar validation before preserving violations; align tests with plan acceptance
  - From dyn-dyn-gate-authority: Remove standalone preservation from `write_unavailable_note`; require the same checks as `_preserved_invariant_violation` before any early return, and add tests for stale head, invalid sidecar, and metadata-only legacy notes that must not be preserved.


### FINDING_4: Re-author reason tokens are discarded before Step 8
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: Coordinator results serialize only `kind:re-author-required`; bounded reasons such as clean-claim mismatch, missing metadata, or invalid outcome metadata are discarded. Step 8 and rejoin envelopes therefore cannot distinguish the required reassessment cause for operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Thread bounded per-kind reasons through coordinator results, merge envelopes, terminal validation, and rejoin output.
  - From cursor-specialist-edge-cases: Emit bounded per-kind reason tokens in coordinator stdout and persist them in the Step 8 result env
  - From codex-specialist-edge-cases: Propagate a sanitized per-kind reason through coordinator output and the Step 8 terminal envelope.
  - From cursor-specialist-testing: Propagate bounded per-kind reasons through results stdout and Step 8 terminal KVs.
  - From codex-specialist-testing: Preserve a sanitized bounded per-kind reason in coordinator output and retain it in the Step 8 terminal envelope and rejoin output.
  - From dyn-dyn-gate-authority: Encode bounded per-kind reason tokens in coordinator results (for example `invariants:re-author-required:clean-mismatch`) and teach `step-8-assessment.sh` to persist and re-emit them in the terminal envelope.


### FINDING_5: Post-write consistency failures are misclassified as unavailable
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Post-write outcome consistency failures are caught by the generic persistence-error path and converted to unavailable, even when the authored note persists. These cases should produce a dedicated re-author-required result before unavailable persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Raise the dedicated re-author exception for post-write consistency failures and handle it before unavailable persistence.


### FINDING_10: Wrapper harness asserts obsolete failure-routing prose
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The architectural-guidelines wrapper harness still asserts obsolete Step 8 failure-routing prose and does not include the current re-author carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update literal to match current SKILL.md and add re-author terminal assertions.


### FINDING_13: Wrapper harness lacks invalid cross-vocabulary and clean-mismatch cases
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The wrapper harness does not exercise invalid cross-vocabulary and clean-claim mismatch shell cases without consumable artifacts, leaving those wrapper regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend harness with rc 7 cases for invalid cross-vocabulary and clean-claim mismatch without consumable artifacts.
