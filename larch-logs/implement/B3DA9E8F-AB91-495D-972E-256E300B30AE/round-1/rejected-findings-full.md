### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/launch-claude-review.sh:101-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Launcher does not pre-check the 20-file context cap before calling the subprocess. Operators passing many --context-files plus implicit flags get a subprocess error instead of an early launcher exit 2 with a stable message. Count ctx_args before launch and exit 2 when >20, or document subprocess-only enforcement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: risk-integration: scripts/test-launch-claude-review.sh:1-23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Global LARCH_TEST_CLAUDE_STDIN_LOG changes stub behavior for all legacy cases. Platform-specific tee/stdin issues could break unrelated harness assertions. Limit stdin logging to new test blocks only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: risk-integration: skills/design/scripts/validate-plan-commands.sh:74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] PERL_BADLANG=0 lacks a dedicated regression test. Locale-related --help capture flake could return without launcher changes. Add locale-focused probe test if this has flaked in CI.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

