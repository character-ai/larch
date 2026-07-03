### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Step 2 floor matching uses the wrong path set
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Step 2 floor matching feeds the wrong path set into `difficulty write-record`. Unrelated dirty files can inflate `applied_tier`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Build the floor path list from manifest `files_touched` / `tests_added_or_modified` (or the post-commit pathspec).
  - From dyn-dyn-difficulty-records: Build the floor path list from manifest `files_touched` / `tests_added_or_modified` (or the post-commit pathspec).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: review_core_body drops scout difficulty KVs
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: review_core_body does not relay scout difficulty KVs into its stdout envelope. Standalone `/review` consumers can miss scout difficulty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Forward `SCOUT_DIFFICULTY_RATING` and `SCOUT_DIFFICULTY_STATUS` in `dispatch_scout_rows` when present.
  - From dyn-dyn-difficulty-records: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

