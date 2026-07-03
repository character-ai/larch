### OOS_1: [OUT_OF_SCOPE] Background-reference regex can over-span and misclassify unrelated paths
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The background-reference matcher can run from an earlier `see` to a later `only for background` on the same line, so an unrelated path can be labeled conditional when the convention is used outside a tightly bounded table-cell pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Legacy doc-only citations remain outside the background convention
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Existing `See … for …` references in `skills/implement/SKILL.md` still rely on the old wording, so they are outside this branch’s new background-reference rule and would need follow-on ledger cleanup if they are meant to participate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Tier-move exemption is asymmetric and can hide or leave growth ratchets active
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The eager→conditional allowance only softens review conditional growth when the combined eager+conditional totals stay flat or shrink, so unrelated conditional churn can mask growth, and the reverse conditional→eager move still leaves eager ratchets active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Dropped-file ratchet misses never-baselined unsupported citation patterns
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The dropped-file guard only compares the committed baseline union to the live scan, so citation forms that were never baselined still escape the ratchet; that is a model limitation rather than a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Eager→conditional test does not assert the promoted file lands in `conditional_files`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The regression test checks that lint exits cleanly, but it does not verify that `flags.md` is recorded in `conditional_files`, so a `force_conditional` wiring error could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

