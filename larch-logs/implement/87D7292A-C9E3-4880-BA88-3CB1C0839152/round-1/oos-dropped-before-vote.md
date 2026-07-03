### OOS_1: [OUT_OF_SCOPE] Triage/default fallback remains unchanged
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The default `"not yet triaged"` fallback and related triage-path behavior remain unchanged; the cited test still only exercises the `CONFIRMED_FIXED` case, and the truncation overlay remains independent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Explicit terminal set for the mechanical verdict gate
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The mechanical-verdict gate uses `!= "NEEDS_DEEP"` instead of an explicit terminal set, so a future non-terminal token could be misclassified if the manifest expands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Prefer `if bundle.mechanical_verdict in ("NOT_FIXED", "WONTFIX"):` or a named `TERMINAL_MECHANICAL_VERDICTS` constant.
  - From cursor-specialist-edge-cases: Use explicit terminal set NOT_FIXED WONTFIX or MECHANICAL_VERDICTS minus NEEDS_DEEP

### OOS_3: [OUT_OF_SCOPE] Deep-verdict follow-up coverage only exercises `CONFIRMED_FIXED`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new deep-verdict test covers `CONFIRMED_FIXED` surfacing, but not other terminal deep verdicts on `NEEDS_DEEP` bundles, so follow-up filing and report surfacing for `NOT_FIXED`/`INCOMPLETE`/`REGRESSED` remain unexercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optional sibling test asserting follow-up body includes `#N: NOT_FIXED` when mechanical is `NEEDS_DEEP` and deep is `NOT_FIXED`.
  - From cursor-specialist-edge-cases: Add sibling test asserting terminal deep verdict in report and follow-up-issue.md

### OOS_4: [OUT_OF_SCOPE] New test misses `report.md` persistence assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new test does not assert `report.md` persistence, which is a consistency-only gap because `render_report` always writes the file.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Final-verdict ladder lacks direct branch tests
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_final_verdict` priority ordering is only covered indirectly, so regressions would still need full `render_report` fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optional focused _final_verdict unit tests per branch

### OOS_6: [OUT_OF_SCOPE] Triage verdict can surface when `deep_verdict` is absent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: A bundle with mechanical `NEEDS_DEEP`, a ledger triage verdict, and no `deep_verdict` would show the triage verdict instead of the mechanical status, although current routing makes that path unlikely.
- **Suggested revisions (informational for voters; coder decides)**:

