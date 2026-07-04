### OOS_1: [OUT_OF_SCOPE] live vote parse-rate acceptance
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The live vote parse-rate acceptance is required by the plan, but the diff does not evidence it, so merge could proceed without confirming behavioral parity beyond unit grammar tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Run one live review/vote path and record parse success before merge.

### OOS_2: [OUT_OF_SCOPE] scout boundary assertions
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The dynamic specialist contract test no longer asserts the scout untrusted-boundary text, so later compression could remove the scout injection guard without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add an assert that scout_notes untrusted ignore-commands text remains present.

### OOS_3: [OUT_OF_SCOPE] specialist tagging anchor coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The specialist-tagging test only covers the generic diff mode, leaving the compressed description and classifier-tagging branches without anchor regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Parametrize mode and diff_mode for anchor and NO_ISSUES_FOUND checks

### OOS_4: [OUT_OF_SCOPE] plan-context frozen grammar coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The plan-context voter frozen-grammar path is still untested, so ballots with scope anchors could drift when that surface changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add plan-context voter render tests when that surface is next touched

### OOS_5: [OUT_OF_SCOPE] scaffold byte ceiling guard
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: There is no automated guard on scaffold_bytes reduction acceptance, so scaffold prose could grow again unless the cost check is rerun manually.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a ceiling ratchet on generated/no-agent scaffold rows if acceptance must stay mechanical

### OOS_6: [OUT_OF_SCOPE] line-range token mismatch
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: nit
- **Concern**: The dynamic specialist example still uses `<path>:<lines>` while static specialist tagging expects `<path>:<line-range>`, which can confuse the expected token form.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-contract: Address the concern above.

