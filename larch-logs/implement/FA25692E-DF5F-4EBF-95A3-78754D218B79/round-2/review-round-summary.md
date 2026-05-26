# Review Round 2

- Mode: `diff`
- 3 accepted, 23 rejected (5 exonerated)

## Accepted Findings

### FINDING_14: risk-integration: scripts/test-launch-codex-ci.sh:106-194
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Runtime tests do not assert --json in codex argv. Removing --json from launch-codex-ci.sh while stubs still emit JSONL would pass CI but break real Codex runs (fail-closed, no cost). Record stub argv and assert --json is present, matching test-codex-implementer.sh.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/parse-codex-usage.md:34-48 vs scripts/parse-codex-usage.sh:35-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sibling doc omits top-level and .msg top-level token field probes that the jq program implements. Contributors extending schema support may update jq only and miss doc/fixture expectations; Codex 0.125 smoke shape is undocumented. Document the third usage-detection branch and top-level field coalesce paths in parse-codex-usage.md.
- **Suggested revision**: Address the concern above.


### FINDING_20: security: scripts/lib-quiet.sh:151-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] 1KiB cut applies to full breadcrumb line including text= A long API key in breadcrumb text= can leave a recoverable prefix in committed larch-logs breadcrumbs Truncate/drop only the text payload; add regression test
- **Suggested revision**: Address the concern above.


