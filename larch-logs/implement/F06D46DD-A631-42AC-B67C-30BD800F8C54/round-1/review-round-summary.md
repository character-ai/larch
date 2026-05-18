# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 1
- Exonerated findings: 1
- Neutral findings: 0

## Accepted Findings

### FINDING_10: risk-integration: scripts/test-compose-review-findings.sh:72-85
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness assertion for ampersand-only escaping despite feature and code escaping & < >. A future mistaken change to escape_finding_body could remove or break & handling while XML-tag assertions still pass; CI would not catch bare & left unescaped in bodies. Add a fixture line with a literal ampersand and assert &amp; appears and the raw ampersand phrase does not.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Nit** `code-quality` `scripts/test-compose-review-findings.sh:72` — The new regression only proves `<` and `>` escaping, but the feature also requires escaping bare `&`, where sed replacement order is easy to regress. Add `A & B` or similar to the fixture and assert `A &amp; B` appears.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/test-compose-review-findings.sh:72` — The new regression only proves `<` and `>` escaping, but the feature also requires escaping bare `&`, where sed replacement order is easy to regress. Add `A & B` or similar to the fixture and assert `A &amp; B` appears.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Reviewer field is not HTML-escaped; only the body is. A rare artifact with angle brackets in the `[… Review] …` reviewer label could still trigger XML-like lint warnings after this change. HTML-escape `reviewer_redacted` the same way as the body, or document and enforce that reviewer labels cannot contain `<`, `>`, or `&`.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/test-compose-review-findings.sh:72-85
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression omits ampersand escaping coverage despite triple-character contract. A maintainer could remove the `&` → `&amp;` sed expression; tests would still pass while docs claim `&` is escaped. Add a fixture line containing `&` and grep for `&amp;` in the composed markdown.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reviewer name in the section header is not HTML-escaped while the body is. A reviewer string containing XML-like angle brackets would still appear raw on the `### id: reviewer [phase/outcome]` line and could re-trigger markdownlint or agent-lint warnings despite bodies being safe. HTML-escape `reviewer_redacted` the same way as the body, or document and guarantee reviewer labels never contain `<`, `>`, or `&`.
- **Suggested revision**: Address the concern above.


