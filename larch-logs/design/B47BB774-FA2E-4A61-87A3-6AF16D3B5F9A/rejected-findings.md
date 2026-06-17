### [Plan Review] FINDING_2

### FINDING_2: Secondary zero-success gate ignores threshold `SUCCEEDED_SLOTS`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The post-consolidation secondary gate at `review-core.sh:876-888` keys off `collector_success_count()` over `collector-results.env` only. The primary threshold in `check-reviewer-failure-threshold.sh` already counts successes from `--reviewer-output-files`. When `collector-results.env` is empty or non-OK but substantive reviewer output files exist, `THRESHOLD_OK` can remain true with `SUCCEEDED_SLOTS>0` while `launched_success_count==0`, tripping `panel-failed` with reason `no successful launched reviewer output` despite completed reviewers and parseable output (issue #4547 scenario).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For the secondary gate, read SUCCEEDED_SLOTS from review-core-threshold.env (already emitted by check-reviewer-failure-threshold.sh) instead of collector_success_count(); keep the parseable-output bypass only when SUCCEEDED_SLOTS==0 and consolidated findings exist


### [Plan Review] FINDING_3

### FINDING_3: OOS-only bypass can discard collected OOS findings after aggregation
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: An OOS-only bypass can skip the post-aggregation zero-findings branch when collect-time `OOS_COUNT>0`, but the `MERGED_COUNT==0` path still runs `emit_zero_findings_branch`, which drives tally through an emptied `findings.md`. `tally-code-votes.sh:111-115` truncates `oos.md` on startup. An all-OOS round can therefore exit cleanly with zero OOS handoff, losing parseable reviewer OOS output the fix is meant to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Snapshot the collect-time findings or OOS ballot before aggregation and feed those OOS blocks into the tally/OOS path when MERGED_COUNT=0 and oos_count>0, or add a dedicated OOS-only clean branch that does not truncate the collected OOS file. Extend the regression to assert the OOS artifact or accepted-OOS handoff still contains the collected OOS rows.

