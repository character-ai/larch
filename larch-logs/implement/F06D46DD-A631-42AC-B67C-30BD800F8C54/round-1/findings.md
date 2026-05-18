### FINDING_1: **Nit** `code-quality` `docs/run-logs.md:138`, `skills/implement/SKILL.md:1393` — These contracts still describe the finding body as redacted/verbatim prose, but this branch now emits redacted and HTML-escaped prose. Update the wording so downstream readers do not expect byte-verbatim finding bodies.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `docs/run-logs.md:138`, `skills/implement/SKILL.md:1393` — These contracts still describe the finding body as redacted/verbatim prose, but this branch now emits redacted and HTML-escaped prose. Update the wording so downstream readers do not expect byte-verbatim finding bodies.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `scripts/test-compose-review-findings.sh:72` — The new regression only proves `<` and `>` escaping, but the feature also requires escaping bare `&`, where sed replacement order is easy to regress. Add `A & B` or similar to the fixture and assert `A &amp; B` appears.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/test-compose-review-findings.sh:72` — The new regression only proves `<` and `>` escaping, but the feature also requires escaping bare `&`, where sed replacement order is easy to regress. Add `A & B` or similar to the fixture and assert `A &amp; B` appears.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: SECURITY.md:56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Security doc still describes only the redaction pipeline for compose output, not post-redaction HTML entity encoding of bodies. Operators reading SECURITY.md may assume placeholders remain literal `<REDACTED-TOKEN>` in `review-findings-full.md`. Add one clause noting HTML escaping of finding bodies after redaction (optional cross-link to compose-review-findings.md).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] security: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Reviewer substring in the markdown heading is still not HTML-escaped while finding bodies are. A committed rejected-finding header could still carry tag-like text in the reviewer segment and trigger the same class of markdownlint/XML warnings the body escape was meant to avoid. Apply the same entity escape to reviewer_redacted (and optionally centralize with escape_prompt_data) if headings must be equally safe for linters.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Reviewer field is not HTML-escaped; only the body is. A rare artifact with angle brackets in the `[… Review] …` reviewer label could still trigger XML-like lint warnings after this change. HTML-escape `reviewer_redacted` the same way as the body, or document and enforce that reviewer labels cannot contain `<`, `>`, or `&`.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-compose-review-findings.sh:72-85
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression omits ampersand escaping coverage despite triple-character contract. A maintainer could remove the `&` → `&amp;` sed expression; tests would still pass while docs claim `&` is escaped. Add a fixture line containing `&` and grep for `&amp;` in the composed markdown.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/compose-review-findings.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Documentation bullet in implementation plan asked for a single sentence noting HTML escaping; the edit expands the paragraph to several sentences. None; readers still learn the behavior; only traceability to the plan’s “one sentence” wording is loose. Tighten to one sentence as specified, or adjust the plan if the longer explanation is preferred.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Whole-body HTML escape changes how angle brackets render inside markdown code spans and other non-tag prose. A finding that cites `</foo>` in backticks becomes `&lt;/foo&gt;` in the output file, so humans no longer see the same glyph sequence as in the source artifact even though lint may pass. Add a contract-doc caveat about whole-body escaping and code-span readability, or narrow the escape strategy if preserving code-span literals matters.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/compose-review-findings.sh:65-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reviewer name in the section header is not HTML-escaped while the body is. A reviewer string containing XML-like angle brackets would still appear raw on the `### id: reviewer [phase/outcome]` line and could re-trigger markdownlint or agent-lint warnings despite bodies being safe. HTML-escape `reviewer_redacted` the same way as the body, or document and guarantee reviewer labels never contain `<`, `>`, or `&`.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-compose-review-findings.sh:72-85
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness assertion for ampersand-only escaping despite feature and code escaping & < >. A future mistaken change to escape_finding_body could remove or break & handling while XML-tag assertions still pass; CI would not catch bare & left unescaped in bodies. Add a fixture line with a literal ampersand and assert &amp; appears and the raw ampersand phrase does not.
- **Suggested revision**: Address the concern above.

