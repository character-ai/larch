### FINDING_13: risk-integration: scripts/dispatch-code-voters.md:41-51
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Glossary says failed means missing/empty while new prose documents non-empty failed voter output. Operators misinterpret VOTER_1_STATUS=failed when a non-empty file exists and bytes were logged. Qualify failed semantics per slot or align glossary with dispatch-code-voters.sh rules.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: CHANGELOG.md:50-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Release notes for 29.8.43 omit the dispatch-order behavior change. Consumers relying on CHANGELOG for operational semantics may miss the new Cursor-first fallback story. Document Cursor-first external coder dispatch with Codex fallback in the Changed section.
- **Suggested revision**: Address the concern above.


