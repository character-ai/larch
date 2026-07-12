# Review Round 2

- Mode: `diff`
- 8 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Unified Split-path wording is still bypassed by legacy prompts
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Step 5c still documents Decompose/Override/Cancel, and related flags documentation still describes preliminary partition prompts. This can introduce a second partition question and violate the unified one-question Split-path contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_2: Migration does not revalidate the complete live dependency graph before removal, sentinel creation, and close
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Fresh and resumed migrations can remove manifest-listed edges, write the sentinel, or close the original issue without comparing its complete current blocked_by/blocking graph against the persisted manifest. Dependencies added, removed, or swapped during migration may remain unmigrated. Re-read both full dependency sets before removals, before sentinel creation, and before close; fail closed on unmanifested drift while preserving verified partial-retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Migration and closure regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: High-risk paths remain insufficiently tested, including one-piece rejection, stale-sentinel rejection, partial-retry convergence, add-before-remove ordering, incomplete migration or failed postconditions refusing close, and intra-piece postcondition failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: Sprawl cancellation wording still references legacy Cancel semantics
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Step 1d wording references Cancel instead of the unified Other/chat exit, which may lead maintainers to implement incorrect sprawl exit semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_7: Duplicate declared dependencies are silently accepted
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Repeated blockers declared for one piece are silently deduplicated instead of rejected as invalid input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_8: Filed-piece validation does not enforce a unique contiguous mapping
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Filed-piece validation accepts duplicate issue numbers and non-contiguous piece mappings, allowing multiple declared pieces to collapse onto one GitHub issue and permitting closure without a one-to-one partition mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_9: Split-path documentation references removed panel-dispatch infrastructure
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The Split-path section still describes panel dispatch even though the current path is inline, creating maintainer confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_11: remove-blocked-by lacks lookup-failure regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Removal-path GraphQL lookup failures lack coverage symmetric with add-blocked-by, so exit codes or diagnostics could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
