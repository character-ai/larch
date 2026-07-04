### OOS_1: [OUT_OF_SCOPE] cover invalid root and since-tag failures
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Invalid `--root` and unresolved `--since-tag` error paths lack coverage, so exit-2 and stderr-contract regressions could slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] decide how to handle float-valued JSON rows
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Float-valued `closure_estimated_tokens` rows are silently skipped during lenient parse, which can hide targets and skew later per-target deltas when historical JSON is malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] clear stale last_values when targets disappear
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ledger-history
- **Severity**: important
- **Concern**: When a target is missing from a revision, its prior value stays in `last_values`, so a later reappearance can attribute multiple commits of change to one delta and produce a spurious raise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ledger-history: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] reject non-array JSON baselines
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Non-array top-level JSON payloads are not covered, so malformed baseline input rejection could regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] add a Makefile target for ledger tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no dedicated Makefile harness for this ledger slice, so local invocation is less discoverable than the other lint suites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] automate the live round-XI smoke
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The real-repo round-XI history path is still only exercised manually, so CI does not guard that smoke scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] add direct rev_parse_verify coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `rev_parse_verify` has no direct unit test, so its failure behavior is only indirectly protected by higher-level tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] cover production-shaped PR subjects
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: nit
- **Concern**: The fixture uses simplified issue-subject shapes, so suffix parsing on production-shaped `Fixes #...` subjects is not exercised and PR-column regressions on real history could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] detect duplicate skill keys
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: latent
- **Concern**: Duplicate `skill` keys are silently last-wins during parsing, so corrupted history can hide the true per-merge delta for that commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] make NUL-delimited subject parsing collision-proof
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: latent
- **Concern**: `log_path_commits` relies on splitting subjects on `\x00`, so a NUL embedded in a subject would corrupt SHA/subject pairing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.

