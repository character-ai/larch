### FINDING_1: Empty `in_memory_stall_tracking` falls back to process env `STALL_TRACKING`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Callers pass `in_memory_stall_tracking=""` into `normalized_outcome_values`. An empty string is falsy, so the helper falls back to `os.environ["STALL_TRACKING"]`. After a Step 5 stall, the orchestrator can still export `STALL_TRACKING=true` while `ship-pr-state.sh` and `finalize-state.sh` already reflect a recovered `pr-created` run. `any_stall` stays true, the normalized outcome remains `stalled`, and merge-downgrade signaling (e.g. `IMPLEMENT_MERGE_DOWNGRADED`) never fires even though `summary-final.md` should report `pr-created`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass in_memory_stall_tracking="false" (or read durable layers only) when evaluating merge downgrade from ship-seed-input.env and execution-issues.md, matching the Step 18a.5 post-clear-stall contract.

### FINDING_2: Secondary zero-success gate ignores threshold `SUCCEEDED_SLOTS`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The post-consolidation secondary gate at `review-core.sh:876-888` keys off `collector_success_count()` over `collector-results.env` only. The primary threshold in `check-reviewer-failure-threshold.sh` already counts successes from `--reviewer-output-files`. When `collector-results.env` is empty or non-OK but substantive reviewer output files exist, `THRESHOLD_OK` can remain true with `SUCCEEDED_SLOTS>0` while `launched_success_count==0`, tripping `panel-failed` with reason `no successful launched reviewer output` despite completed reviewers and parseable output (issue #4547 scenario).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For the secondary gate, read SUCCEEDED_SLOTS from review-core-threshold.env (already emitted by check-reviewer-failure-threshold.sh) instead of collector_success_count(); keep the parseable-output bypass only when SUCCEEDED_SLOTS==0 and consolidated findings exist

### FINDING_3: OOS-only bypass can discard collected OOS findings after aggregation
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: An OOS-only bypass can skip the post-aggregation zero-findings branch when collect-time `OOS_COUNT>0`, but the `MERGED_COUNT==0` path still runs `emit_zero_findings_branch`, which drives tally through an emptied `findings.md`. `tally-code-votes.sh:111-115` truncates `oos.md` on startup. An all-OOS round can therefore exit cleanly with zero OOS handoff, losing parseable reviewer OOS output the fix is meant to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Snapshot the collect-time findings or OOS ballot before aggregation and feed those OOS blocks into the tally/OOS path when MERGED_COUNT=0 and oos_count>0, or add a dedicated OOS-only clean branch that does not truncate the collected OOS file. Extend the regression to assert the OOS artifact or accepted-OOS handoff still contains the collected OOS rows.
