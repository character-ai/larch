### FINDING_1: **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file refs in markdown-link form like ``[`path`](...)``, but the new prompt contract in `scripts/render-specialist-prompt.sh:323-325` and `skills/review/scripts/dispatch-panel.sh:163-168` requires plain backticked paths like `` `scripts/foo.sh:12-15` ``. Concrete failing scenario: an OOS bullet `- **risk-integration** \`scripts/foo.sh:12-15\` — ...` is collected as `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream OOS issue/file-conflict handling. **Suggested fix:** extend the extractor to preserve the first plain backticked path token as well as markdown-link refs, and add a regression for the newly required bullet shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file refs in markdown-link form like ``[`path`](...)``, but the new prompt contract in `scripts/render-specialist-prompt.sh:323-325` and `skills/review/scripts/dispatch-panel.sh:163-168` requires plain backticked paths like `` `scripts/foo.sh:12-15` ``. Concrete failing scenario: an OOS bullet `- **risk-integration** \`scripts/foo.sh:12-15\` — ...` is collected as `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream OOS issue/file-conflict handling. **Suggested fix:** extend the extractor to preserve the first plain backticked path token as well as markdown-link refs, and add a regression for the newly required bullet shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] architecture: git_history merge-base..HEAD
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Two version bump commits ride with the feature branch on the sampled log PR description may need to mention bumps separately from the 16 prompt items Clarify in PR summary that bumps follow repo /implement policy
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Bulk run-log and token-report artifacts in diff Intentional committed logs per project policy; not a security defect of the prompt-audit code None (operational choice)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] correctness: skills/review/scripts/collect-findings.sh:OOS_normalize
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Bash-regex extraction of backtick path for OOS titles Edge-case titles with odd backtick payloads are theoretical; not shown as exploitable shell injection Harden only if telemetry shows misparsed titles
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

