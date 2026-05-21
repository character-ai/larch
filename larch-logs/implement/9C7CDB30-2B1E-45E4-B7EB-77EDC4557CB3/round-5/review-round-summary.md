# Review Round 5

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 0
- Exonerated findings: 15
- Neutral findings: 0

## Accepted Findings

### FINDING_1: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:200-442
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Mangled-row jq output cached to a temp path is only deleted in the category-stats block; early exit 1 after oos-category-mangle skips that block. A custom scans.tsv with oos-category-mangle followed by an unknown scan name hits exit 1 after mktemp; the jq_out temp file is left in TMPDIR (same class of leak if required-file-presence exits after oos when scans order is customized). Use an EXIT trap to rm the cache file whenever set, or clear the cache on every exit path before leaving the scan loop.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: .claude/skills/audit-runs/scripts/audit-compute-counters.sh:102-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] OOS clean/blank delta skipping depends on grepping a human-readable detail substring Rewording the missing-jsonl detail string or an unrelated detail containing the same phrase changes whether placeholder partial rows contribute to cumulative counters, corrupting audit deltas without loud failure Add a stable partial_reason code emitted by audit-scan-run.sh and key off that in audit-compute-counters.sh
- **Suggested revision**: Address the concern above.


