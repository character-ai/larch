### FINDING_27: [OUT_OF_SCOPE] architecture: branch vs main (aggregate diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Large tangled changes outside the enumerated 16 prompt edits (vote tally, compose JSONL, logs, version bumps). Review surface is wide; harder to reason about blast radius of the PR as a pure “prompt audit”. None required for this review; split or document intent when merging.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed implement run logs ship with the PR. Low: future log content could include sensitive host or env text if capture/redaction fails. Maintain redaction discipline; avoid logging secrets; rely on existing redact tooling in collectors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] code-quality: larch-logs/implement/** (bulk)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large run-log artifacts in diff noise review surface Not introduced as a functional defect per repo logging policy None required for this review
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/render-plan-review-prompt.sh:unquoted-heredoc
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unquoted heredoc expands PLAN_FILE when building the plan-review prompt. If a caller ever passed a PLAN_FILE value containing shell command substitution, bash could execute it while composing the prompt. Keep path variables out of unquoted heredocs; use printf or a quoted heredoc.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_4: **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file references written as markdown links, but the new reviewer prompt contract asks for raw backticked `path:line` tokens. Concrete failing scenario: an OOS bullet like `- **risk-integration** \`scripts/foo.sh:12\` — ...` is rewritten to `[OUT_OF_SCOPE] risk-integration`, dropping the path from the OOS title that later becomes the public issue title. Suggested fix: also extract the first raw backticked file token, preferably `path[:line[-line]]`, before falling back to category-only, and add a regression matching the new prompt shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file references written as markdown links, but the new reviewer prompt contract asks for raw backticked `path:line` tokens. Concrete failing scenario: an OOS bullet like `- **risk-integration** \`scripts/foo.sh:12\` — ...` is rewritten to `[OUT_OF_SCOPE] risk-integration`, dropping the path from the OOS title that later becomes the public issue title. Suggested fix: also extract the first raw backticked file token, preferably `path[:line[-line]]`, before falling back to category-only, and add a regression matching the new prompt shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

