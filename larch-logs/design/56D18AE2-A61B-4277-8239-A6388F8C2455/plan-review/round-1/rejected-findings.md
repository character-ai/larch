### [Plan Review] FINDING_7

### FINDING_7: Dynamic-only pruned threshold mode lacks stable flag and denominator semantics
- **Reviewer(s)**: Cursor-dyn-degradation-denominator, Codex-dyn-degradation-denominator
- **Severity**: important
- **Concern**: The planned post-filter failure-threshold mode does not specify an exact opt-in CLI flag or how review-core/check-reviewer-failure-threshold should compute the denominator when the filtered manifest has zero static rows, risking false zero-findings passes for all-failing dynamic-only panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-degradation-denominator: Implementers must invent flag spelling and wiring; harness pins in test-check-reviewer-failure-threshold.sh cannot assert argv without a stable name Name the flag in plan UPDATED sections (e.g. --dynamic-denominator-when-no-static) and add it to check-reviewer-failure-threshold.md Args plus review-core.sh threshold_args construction
  - From Codex-dyn-degradation-denominator: Name the exact flag, and state that review-core.sh passes it only when pruning is active and the filtered canonical manifest has zero static rows; in that mode pass the filtered launched row count as the intended/launched denominator and stop skipping dynamic rows inside the threshold script


