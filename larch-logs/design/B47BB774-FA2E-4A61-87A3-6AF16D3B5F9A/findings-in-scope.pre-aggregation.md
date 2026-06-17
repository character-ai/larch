### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pr_body.py:217-225
- **Concern**: _append_merge_downgrade_warning reuses normalized_outcome_values with in_memory_stall_tracking="". Scenario: An empty string is falsy, so normalized_outcome_values falls back to os.environ STALL_TRACKING. After Step 5 stall the orchestrator can still export STALL_TRACKING=true while ship-pr-state.sh and finalize-state.sh already show a recovered pr-created run. The helper then sees any_stall=true, outcome stays stalled, and IMPLEMENT_MERGE_DOWNGRADED never becomes true even though summary-final.md should report pr-created.
- **Proposed resolution**: Pass in_memory_stall_tracking="false" (or read durable layers only) when evaluating merge downgrade from ship-seed-input.env and execution-issues.md, matching the Step 18a.5 post-clear-stall contract.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/review-core.sh:876-888
- **Concern**: Secondary zero-success gate keys off collector_success_count() only while primary threshold already counts successes from --reviewer-output-files. Scenario: Empty or non-OK collector-results.env with substantive reviewer output files can yield THRESHOLD_OK=true and SUCCEEDED_SLOTS>0 yet launched_success_count==0, tripping the post-consolidation panel-failed path described in issue #4547
- **Proposed resolution**: For the secondary gate, read SUCCEEDED_SLOTS from review-core-threshold.env (already emitted by check-reviewer-failure-threshold.sh) instead of collector_success_count(); keep the parseable-output bypass only when SUCCEEDED_SLOTS==0 and consolidated findings exist

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/review-core.sh:1037-1040; python/legacy_review_shell/tally-code-votes.sh:111-115
- **Concern**: OOS-only bypass can silently discard collected OOS findings. Scenario: The plan skips the post-aggregation zero-findings branch when collect-time OOS_COUNT is greater than 0, but the aggregate_zero path empties findings.md and the tally script truncates oos.md on startup. An all-OOS round can then exit cleanly with zero OOS handoff, losing the parseable reviewer output the fix is meant to preserve.
- **Proposed resolution**: Snapshot the collect-time findings or OOS ballot before aggregation and feed those OOS blocks into the tally/OOS path when MERGED_COUNT=0 and oos_count>0, or add a dedicated OOS-only clean branch that does not truncate the collected OOS file. Extend the regression to assert the OOS artifact or accepted-OOS handoff still contains the collected OOS rows.

