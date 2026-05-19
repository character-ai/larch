### FINDING_1: **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1195`: degraded rounds are still included in the Important-finding scan even though they are excluded from the convergence count. In a run where round 1 is clean/small, round 2 is degraded and contains an Important finding, and round 3 is clean/small, `prev_round_a` becomes round 1 but the loop scans `round-1` through `round-3`, so the degraded round 2 finding blocks `converged-small-changes`. Suggested fix: scan only the current round and the selected previous non-degraded round, or skip `round_degraded` rounds inside the scan loop.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1195`: degraded rounds are still included in the Important-finding scan even though they are excluded from the convergence count. In a run where round 1 is clean/small, round 2 is degraded and contains an Important finding, and round 3 is clean/small, `prev_round_a` becomes round 1 but the loop scans `round-1` through `round-3`, so the degraded round 2 finding blocks `converged-small-changes`. Suggested fix: scan only the current round and the selected previous non-degraded round, or skip `round_degraded` rounds inside the scan loop.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:1459-1483
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Custom --convergence-threshold positive convergence path not asserted (only suppression tested in Test 8). A regression could break non-default threshold convergence while default-threshold and suppression tests still pass. Add one stubbed case with --convergence-threshold 1 and two consecutive low-accept rounds expecting converged-small-changes.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1195-1197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Important-findings scan includes every findings.md between prev non-degraded round and current, not only the two rounds used for accept-count comparison. An intermediate degraded round can still carry Important headings in findings.md and block convergence even though accept counts were compared across non-adjacent rounds per the plan text. Restrict Important scan to the two compared rounds or update the contract and tests to the wider interpretation.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review-and-fix/scripts/review-and-fix.sh:990-1027
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale degraded-retry.flag/.done from an earlier completed run suppresses the one allowed panel retry on a later re-invocation while voting-tally.md can still show the degraded banner after a fresh review-core run. A second Step 5 run reusing the same round-N directory can leave DEGRADED_ROUND=true and skip the extra review-core attempt even though this invocation only executed review-core once and the banner persists. Clear or re-key retry markers at round start or gate skip logic on artifact freshness tied to the current review-core output.
- **Suggested revision**: Address the concern above.


