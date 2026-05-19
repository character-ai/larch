### FINDING_1: **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1195`: degraded rounds are still included in the Important-finding scan even though they are excluded from the convergence count. In a run where round 1 is clean/small, round 2 is degraded and contains an Important finding, and round 3 is clean/small, `prev_round_a` becomes round 1 but the loop scans `round-1` through `round-3`, so the degraded round 2 finding blocks `converged-small-changes`. Suggested fix: scan only the current round and the selected previous non-degraded round, or skip `round_degraded` rounds inside the scan loop.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1195`: degraded rounds are still included in the Important-finding scan even though they are excluded from the convergence count. In a run where round 1 is clean/small, round 2 is degraded and contains an Important finding, and round 3 is clean/small, `prev_round_a` becomes round 1 but the loop scans `round-1` through `round-3`, so the degraded round 2 finding blocks `converged-small-changes`. Suggested fix: scan only the current round and the selected previous non-degraded round, or skip `round_degraded` rounds inside the scan loop.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: skills/review-and-fix/SKILL.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Standalone review-and-fix skill doc not updated while implement SKILL documents new statuses/cap math. Operators may miss converged-small-changes and DEGRADED_ROUND semantics when not using /implement Step 5. Add a short cross-reference in skills/review-and-fix/SKILL.md to review-and-fix.md for the new contract fields.
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: skills/review-and-fix/scripts/test-review-and-fix.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Tests use custom REVIEW_AND_FIX_REVIEW_CORE_SH stubs rather than the plan's TEST_CORE_STATUS=degraded-panel hook names. Plan-to-test traceability by the names in implementation plan §3 is weaker; coverage is still present. Optional adapter or align naming with the plan for traceability only.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1195-1197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Important-findings scan includes every findings.md between prev non-degraded round and current, not only the two rounds used for accept-count comparison. An intermediate degraded round can still carry Important headings in findings.md and block convergence even though accept counts were compared across non-adjacent rounds per the plan text. Restrict Important scan to the two compared rounds or update the contract and tests to the wider interpretation.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1212-1224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Churn warning compares against last prior non-degraded round, not literal round N-1 from the requirements text. When round N-1 is degraded, the warning compares to an older round, which can differ from the stated round-to-round churn signal. Align docs/requirements with the non-degraded predecessor rule or add an explicit N-1 branch when N-1 is non-degraded.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:996-1024
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Progress-style degraded-retry messages use larch_err instead of a non-error channel. Retry breadcrumbs are mixed with genuine failures in stderr-oriented tooling. Use emit_breadcrumb or a dedicated info helper consistent with nearby review-and-fix logging.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1212-1225
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Churn warning compares current ACCEPTED_COUNT to the last prior non-degraded round, not strictly round N-1 as the feature text states. Example: round 1=4 accepts, round 2 degraded, round 3=8 accepts; warning compares 8>4 using round 1 as the baseline and never reflects round 2 as the immediate predecessor, so the message can imply the wrong pairwise comparison. Compare to round-(N-1) when appropriate, or change the warning copy to say last non-degraded round explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1212-1226
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Churn warning uses find_previous_non_degraded_round instead of strict round-(N-1) from the feature text. When round N-1 is degraded, the warning compares to an earlier round's ACCEPTED_COUNT, so the message may not reflect N vs N-1 as written. Compare N to N-1 for churn only, or document/implement both as "previous non-degraded round."
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review-and-fix/scripts/review-and-fix.sh:990-1027
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale degraded-retry.flag/.done from an earlier completed run suppresses the one allowed panel retry on a later re-invocation while voting-tally.md can still show the degraded banner after a fresh review-core run. A second Step 5 run reusing the same round-N directory can leave DEGRADED_ROUND=true and skip the extra review-core attempt even though this invocation only executed review-core once and the banner persists. Clear or re-key retry markers at round start or gate skip logic on artifact freshness tied to the current review-core output.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/run-step5-review.sh:171-184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New --convergence-threshold flag is not forwarded by the Step 5 launcher. Feature is only reachable for callers that invoke review-and-fix.sh directly unless env wiring is added elsewhere. Optionally plumb a session-env knob into REVIEW_AND_FIX_ARGS or document the limitation explicitly in run-step5-review.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/run-step5-review.sh:171-186
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] The Step 5 launcher never passes --convergence-threshold to review-and-fix.sh, so /implement cannot set a non-default threshold via the supported launcher path. Operators who expect session-configurable convergence in implement mode will always get the default unless they bypass the launcher. Optional session-env wiring for the flag, or explicit documentation that the threshold is only for direct/harness invocation.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/run-step5-review.sh:50-66
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Round-cap inflation counts only rounds whose final DEGRADED_ROUND is true; recovered retries do not add to the inflated cap. Operators expecting each degraded-banner episode to extend the cap may still hit the base round_cap after a successful retry clears DEGRADED_ROUND. Persist a separate degraded-attempt counter for cap math or document the final-state-only behavior.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.md:1-9
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness contract doc not updated for new convergence/degraded/churn coverage. Readers rely on test-review-and-fix.md to know what the harness proves; stale text understates behavior and risks duplicate or missing tests. Extend test-review-and-fix.md with bullets for the new regression blocks and key stdout/env artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:1459-1483
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Custom --convergence-threshold positive convergence path not asserted (only suppression tested in Test 8). A regression could break non-default threshold convergence while default-threshold and suppression tests still pass. Add one stubbed case with --convergence-threshold 1 and two consecutive low-accept rounds expecting converged-small-changes.
- **Suggested revision**: Address the concern above.

### FINDING_15: security: skills/review-and-fix/scripts/review-and-fix.sh:875-879
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Persisted review-and-fix.env writes REVIEW_AND_FIX_STATUS and REVIEW_CORE_STATUS via printf from values originating in review-core output without normalizing embedded newlines. A compromised or buggy upstream could emit multi-line values so line-oriented env parsers mis-read following lines or mirror ambiguous metadata. Strip or reject newline and control characters in those fields before write, or enforce a single-line contract at the review-core producer and validate here.
- **Suggested revision**: Address the concern above.

