### FINDING_11: correctness: scripts/test-compose-review-findings.sh:336-383
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New regression block omits invalid-token bold-markdown heading A refactor could drop or bypass bold-branch whitelist logic while colon-only cases still pass, letting non-tag tokens leak again undetected Add one OOS fixture with title shaped like **not-a-focus-tag** — … and assert empty category
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/compose-review-findings.sh:63-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Five-tag whitelist runs for all emit_record paths via extract_category on every prose body Free-form accepted/plan titles like Architecture boundary or Runtime bug (harness fixtures) used to populate category and now always serialize as empty unless they equal a focus-area tag, which can break downstream consumers expecting the old best-effort label outside OOS Scope validation to code-review out_of_scope only or document breaking change and assert category in baseline harness
- **Suggested revision**: Address the concern above.


