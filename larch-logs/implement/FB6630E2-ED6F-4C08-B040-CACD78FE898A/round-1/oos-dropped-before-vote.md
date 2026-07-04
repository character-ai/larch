### OOS_1: [OUT_OF_SCOPE] Missing regression pins for validator prose edge cases
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new prose-path edge cases are only partially pinned at unit level, so a future matcher edit could regress thin-narration rejection or the comma-qualified no-findings case without an obvious failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add assert research_eval.validate_research_output(..., "Reading files and preparing a response.\n", validation_mode=True) == 2 beside the new prose cases.
  - From cursor-specialist-testing: Add a negative case to test_validation_mode_sentinels_and_thresholds asserting No in-scope issues found, but ... returns 2 in validation_mode.
  - From cursor-specialist-testing: Add a direct thin narration assertion in test_validation_mode_sentinels_and_thresholds expecting return code 2.

### OOS_2: [OUT_OF_SCOPE] Mixed prose+TSV bodies still pass validation
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: TSV validation still runs before the prose no-findings matcher, so a body that combines prose no-findings with substantive TSV rows can still pass as valid. That leaves mixed/contradictory output under-specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reject when prose no-findings matches but substantive TSV rows are also present, or document TSV precedence explicitly.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Collector parity for prose no-findings is missing
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-validator-strictness
- **Severity**: latent
- **Concern**: The collector-side no-findings sentinel helper still does not recognize the prose empty shape, so prose-only empty reviews can still be recorded as NOT_SUBSTANTIVE even though validation-mode accepts them elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend _file_has_no_findings_sentinel or share the new helper for Claude recording parity.
  - From dyn-dyn-validator-strictness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Prompt surface still contradicts the prose empty shape
- **Reviewer(s)**: dyn-dyn-validator-strictness
- **Severity**: latent
- **Concern**: The specialist prompt surface still tells models to output exactly `NO_ISSUES_FOUND` for empty reviews, while the reviewer templates and validator now accept the prose empty form. That mismatch can still steer models toward shapes that the active validator does not treat consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-validator-strictness: Address the concern above.

