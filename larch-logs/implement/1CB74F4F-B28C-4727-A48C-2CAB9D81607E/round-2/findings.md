### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/dispatch-code-voters.md:51
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Glossary line equates failed with missing/empty output only. Operators may infer Voter 1 cannot be failed when the vote file has bytes; non-zero exit still marks failed and now surfaces output bytes in the Warning. Clarify that failed semantics differ for Voter 1 (non-zero exit) vs waterfall slots (missing/empty final path).
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: scripts/dispatch-code-voters.md:51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The one-line gloss that `failed` means the output path is missing or empty is misleading for Voter 1 and sits next to text that now describes non-empty failed output. Readers may misinterpret `VOTER_*_STATUS=failed` after reading the new diagnostic paragraph. Qualify by slot (Voter 1 vs waterfall) or align the sentence with the actual status rules in dispatch-code-voters.sh.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh:349-360
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] append-tool-failure for voter1 is called with >/dev/null 2>&1 || true so failures are swallowed. Pre-existing; not changed by the new head -c block; can hide missing execution-issues entries. Follow-up: log or propagate append-tool-failure errors instead of discarding them.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-dispatch-code-voters.sh:7-9
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Section header comment for `happy` omits the new fail_nonempty / first-200-bytes execution-issues scenario. Maintainers may mis-place or under-shard harness coverage when using the comment as the authoritative section map. Update the `happy` line (or add a sub-bullet) to mention voter1 non-zero exit with non-empty output and the execution-issues snippet assertion.
- **Suggested revision**: Address the concern above.

### FINDING_5: security: scripts/dispatch-code-voters.sh:325-329
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Verbatim voter stdout (up to 200 bytes) is added to voter1-diag.txt and thus to the append-tool-failure payload that is redacted with pattern-only redact-secrets.sh. Narrative failures can include secrets or PII outside redact-secrets coverage; this excerpt source is plausibly richer than .diag alone, so logs may expose more sensitive material under the same partial-redaction model. Accept trade-off; document non-coverage near the new doc bullet; extend redact-secrets only for observed families.
- **Suggested revision**: Address the concern above.

