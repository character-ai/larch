# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Manifest and GLM pricing identity can diverge
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-glm-pricing
- **Severity**: major
- **Concern**: Final-summary GLM detection can resolve the main model from transcript or ambient configuration while token pricing uses the raw manifest model. When the manifest contains `"unknown"` or an absent value, costs may be calculated with Opus rates while the summary applies GLM plan pricing and an adjusted total. Use one manifest-authoritative pricing identity for both cost calculation and GLM formatting, and do not enable GLM formatting from transcript fallback when a manifest is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-glm-pricing: Address the concern above.


### FINDING_7: Non-GLM cost-summary formatting lacks exact-output regression coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Existing tests use substring assertions and do not fully protect byte-preserving non-GLM cost output, including non-GLM `[1m]` models. Whitespace, bullet ordering, or accidental GLM annotations and notes could change without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Manifest-driven write_final_report lacks GLM alias coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Manifest-driven final-report tests do not exercise `model_roster.main=glm-5.2[1m]` through `write_final_report`, so regressions in manifest identity propagation could omit GLM plan pricing or calculate the wrong adjusted total while lower-level alias tests continue to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: GLM zero-cost and unavailable-cost paths lack regression tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There are no dedicated tests covering a zero-cost GLM lane or a GLM lane marked `cost_unavailable`, leaving ordering regressions or mishandling of `$0.00` and `N/A` output undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
