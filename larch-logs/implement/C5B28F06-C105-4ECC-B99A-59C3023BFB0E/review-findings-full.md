### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/test-cache-key-runtime-audit.sh:80-94`, `scripts/test-cache-key-runtime-audit.sh:179-188` — The new mutation fixtures model the second attachment as a later linear child of the first assistant, so `prefix_records()` sees it as an appended stable-prefix record, not a mutation at an established prefix position. Concrete failing scenario: the tool-result fixture produces records `[sys1, usr1/result-A]` then `[sys1, usr1/result-A, usr2/result-B]`, and `classify_change()` returns `EXPECTED-GROWTH`, while the harness asserts `BASELINE,CACHE-INVALIDATING`; the image fixture has the same shape. Suggested fix: make the “mutation” fixtures branch from the same parent position, like the existing `write_cache_invalidating_fixture()` does, or change these two assertions to `EXPECTED-GROWTH` and add separate branched attachment-mutation cases.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-cache-key-runtime-audit.sh:80-94`, `scripts/test-cache-key-runtime-audit.sh:179-188` — The new mutation fixtures model the second attachment as a later linear child of the first assistant, so `prefix_records()` sees it as an appended stable-prefix record, not a mutation at an established prefix position. Concrete failing scenario: the tool-result fixture produces records `[sys1, usr1/result-A]` then `[sys1, usr1/result-A, usr2/result-B]`, and `classify_change()` returns `EXPECTED-GROWTH`, while the harness asserts `BASELINE,CACHE-INVALIDATING`; the image fixture has the same shape. Suggested fix: make the “mutation” fixtures branch from the same parent position, like the existing `write_cache_invalidating_fixture()` does, or change these two assertions to `EXPECTED-GROWTH` and add separate branched attachment-mutation cases.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: scripts/test-cache-key-runtime-audit.sh:99-195

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] write_attachment_stable_fixture omits planned second identical tool_result turn Plan §4 requires two turns with same tool_result content for EXPECTED-GROWTH; fixture uses plain-text usr2 so coverage and pass message imply a scenario the plan did not describe Use two tool_result user turns with identical JSON per plan, or revise plan and comments to match the implemented user:initial extension case
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## security: scripts/cache-key-runtime-audit.py:103-129 scripts/cache-key-runtime-audit.py:333-341

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Full tool_result JSON in prefix digest and diffs Audit output or saved reports may embed secrets from tool outputs Document sensitivity add redaction or gate verbose serialization
- **Suggested revision**: Address the concern above.

