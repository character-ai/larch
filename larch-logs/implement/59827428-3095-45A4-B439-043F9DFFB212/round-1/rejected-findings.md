### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: cap-1 partial-failure rollup guard lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no regression covering the cap-1 partial-failure guard, so a change that stamps failed originals via the rollup URL could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a cap-1 fixture with ISSUE_1_URL plus ISSUE_2_FAILED=true; assert OOS_2 has no Filed URL and no OOS_FILE_MAP row


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: cap-1 rollup regression does not cover the ordinary multi-slot path
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The current regression only exercises the cap-1 rollup path, so a bug in ordinary per-slot URL mapping could still ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a second regression that files two successful non-rollup OOS items with distinct URLs and asserts each original block gets the right Filed URL


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

