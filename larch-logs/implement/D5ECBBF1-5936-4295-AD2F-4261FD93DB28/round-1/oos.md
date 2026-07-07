### FINDING_3: [OUT_OF_SCOPE] bg-wait writer parity lint becomes vacuous
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-proc
- **Severity**: minor
- **Concern**: The writer-parity lint stops enforcing CLONE_PATH once marker-write sites disappear, so future bgjob-only writers could omit CLONE_PATH until replacement coverage lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add replacement lint in #6516 or a sibling chunk
  - From cursor-specialist-testing: Accept per chunk-1 plan note or add bgjob-writer lint in a later chunk
  - From codex-specialist-testing: Accept per chunk-1 plan note or add bgjob-writer lint in a later chunk
  - From dyn-dyn-bgjob-proc: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] bgjob wait hook allowance remains implicit
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-proc
- **Severity**: minor
- **Concern**: The hook's bgjob wait allowance is only implicit, so broader deny-rule changes could block sanctioned wait loops without an explicit regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add explicit bgjob-wait allowlist and matching hook tests when deny rules next expand
  - From dyn-dyn-bgjob-proc: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] bgjob wait contract lacks rejoin rule
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-proc
- **Severity**: minor
- **Concern**: The `skills/shared/bgjob-wait.md` contract still does not normatively pin the live-registry rejoin rule, so sibling chunks can diverge on whether a second start is refused for an identity-valid long-lived step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document rejoin in bgjob-wait.md in a later chunk
  - From cursor-specialist-testing: Add a live-registry rejoin section to bgjob-wait.md in a follow-up if still required
  - From dyn-dyn-bgjob-proc: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

