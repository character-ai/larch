### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: risk-integration: skills/implement/scripts/step-7a.sh:371-372,381-382,386-390
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Empty-SKIP_REASON fallback on skipped/failed branches is untested; generator-crash hits wildcard *) not kv_value fallback. Regression in else branches on skipped/failed would not fail CI; only production envelope gaps would surface. Add stub mode with STATUS=failed or skipped and no SKIP_REASON line, or document wildcard as sole empty-envelope path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: security: skills/implement/scripts/step-7a.sh:368-382
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Generator SKIP_REASON is copied into CODE_FLOW_SKIP_REASON and published on the tracking issue without sanitize_diagnostic_line or markdown neutralization. If gen_out ever carries C0 controls or embedded newlines in SKIP_REASON, the larch:diagrams comment body or rendered GitHub markdown could be corrupted or structurally manipulated before redact-secrets runs. Pipe _skip_reason through sanitize_diagnostic_line (and optionally reject newline-containing values) before assigning CODE_FLOW_SKIP_REASON.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: security: scripts/ci-failed-jobs.sh:100-134
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Item D strips control bytes and drops empty names but still emits printable metacharacters from gh job names into TSV rows and downstream KV consumers when regex classification accepts them. A hostile or crafted workflow job name with shell or markdown metacharacters could still reach operator-visible TSV/KV surfaces; sanitize_list does not scrub per-row TSV cells. Apply job_re-style allowlist filtering at the parse boundary before TSV/KV emit, or document residual risk and verify ship-pr per-job fix loop never interpolates raw TSV fields unsafely.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

