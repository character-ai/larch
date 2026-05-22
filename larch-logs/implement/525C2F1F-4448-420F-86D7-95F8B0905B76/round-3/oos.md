### FINDING_11: [OUT_OF_SCOPE] `CALLER_KIND` rename in `scripts/test-ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Treated as separate issue (e.g. 2539), not OOS gate scope; behavior consistent with SKILL Exit 5 / NEVER 15; no OOS-review change required.
- **Suggested revision**: None for this OOS review; track in the dedicated issue/PR if still desired.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] Committed implement run logs under `larch-logs/implement/...`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Intentional run-log flush per run-logs policy; chore noise unrelated to gate correctness.
- **Suggested revision**: None for this OOS review.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] `.claude-plugin/plugin.json` version bump ships with feature PR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Release metadata only; not a gate-correctness defect for this review.
- **Suggested revision**: None for this OOS review.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] `eval`-based dynamic reads in `audit-scan-run.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Pre-existing CLI arg validation pattern; not introduced or widened by OOS scan wiring.
- **Suggested revision**: None required for this branch.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] `SECURITY.md` not updated for security-routing heuristic
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators relying on `SECURITY.md` may miss how focus-area security routing interacts with OOS gating; no diff touch in scope.
- **Suggested revision**: Optional follow-up doc note if policy applies; not blocking this OOS review.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

