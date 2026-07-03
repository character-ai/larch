### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Post-rebase invalidation still needs a paired run-log flush
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: After a rebase or goto-rebase phase, `_invalidate_guidelines_note` can log a warning after push without any follow-up flush, so `execution-issues.ndjson` stays empty even though stderr already recorded the warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: When post-rebase _invalidate_guidelines_note returns True, run flush_logs_pre and stall before merge if the flush cannot commit, matching the pre-ensure_pr seam.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

