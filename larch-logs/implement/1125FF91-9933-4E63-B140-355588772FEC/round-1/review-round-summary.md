# Review Round 1

- Mode: `diff`
- 5 accepted, 11 rejected (10 neutral)

## Accepted Findings

### FINDING_13: correctness: scripts/lib-timing-kinds.sh:49-55
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [latent] Removing claude-phase3-aggregator from the timing allow-list is based on a false premise; aggregate-findings can still reach Claude phase-3 fallback via dispatch-with-waterfall. When aggregator dispatch runs with Codex/Cursor absent or failing, dispatch-with-waterfall launches phase3 with tool=claude for slot=aggregator, producing claude-phase3-aggregator and causing an unknown task-kind warning. Restore claude-phase3-aggregator to TIMING_TASK_KINDS_ALLOWED, or make aggregator dispatch truly skip Claude fallback before documenting/removing the kind.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/lib-timing-kinds.sh:49-54, scripts/dispatch-with-waterfall.sh:227,472-476
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plan item 3 removes claude-phase3-aggregator and claims it is never emitted, but phase-3 waterfall fallback always records claude-phase3-<slot> with tool=claude. When aggregate-findings.sh waterfall reaches phase 3 for the aggregator slot, timing kind claude-phase3-aggregator is recorded; main had it allow-listed and this branch removes it, reintroducing unknown-task-kind warnings on a real degraded path. Restore claude-phase3-aggregator in TIMING_TASK_KINDS_ALLOWED and document that it is emitted only on phase-3 Claude fallback for the aggregator slot.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/lib-timing-kinds.sh:49-54
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] claude-phase3-aggregator is omitted even though aggregator fallback can still emit it skills/review/scripts/aggregate-findings.sh:878-881 creates slot aggregator with primary tool codex; scripts/dispatch-with-waterfall.sh:227 and 472-476 launch phase3 fallback as claude, yielding claude-phase3-aggregator and a warning Re-add claude-phase3-aggregator to TIMING_TASK_KINDS_ALLOWED, fix the doc note, and cover aggregator phase3 fallback in tests
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/lib-timing-kinds.sh:49-54
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [latent] claude-phase3-aggregator was removed from the allow-list even though aggregator phase-3 fallback can still emit that timing kind. When aggregate-findings creates an aggregator slot and Codex/Cursor are absent or fail, dispatch-with-waterfall launches Claude phase 3 with task kind claude-phase3-aggregator, causing an unknown-task-kind warning. Restore claude-phase3-aggregator to TIMING_TASK_KINDS_ALLOWED, fix the docs, and add a phase-3 aggregator regression test.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: scripts/lib-timing-kinds.sh:49-54
- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: [latent] claude-phase3-aggregator was removed and documented as never emitted, but aggregate-findings can still reach Claude phase-3 fallback through dispatch-with-waterfall. When aggregation falls through to Claude, dispatch-with-waterfall emits timing kind claude-phase3-aggregator, so the ledger still warns and the allow-list/docs are wrong. Keep claude-phase3-aggregator in TIMING_TASK_KINDS_ALLOWED and document that it is emitted only by aggregator waterfall phase-3 fallback.
- **Suggested revision**: Address the concern above.


