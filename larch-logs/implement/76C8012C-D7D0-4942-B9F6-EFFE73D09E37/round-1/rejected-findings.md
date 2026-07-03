### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Scout difficulty sidecars are read from the wrong directory
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `_round_difficulty_object` only looks inside the round directory, but scouts write the sidecar at the session tmpdir root. The committed round metadata can miss a successful scout rating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Main-agent implement difficulty records do not persist the right inputs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: The Claude-coder implement path relies on ambient env and tmpdir state. It does not reliably read the design prior and changed-path list from sidecars or persist the record to the committed run-log batch, so fallback difficulty remains in the repo and floor raises can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From dyn-dyn-difficulty-records: Read prior and changed paths from tmpdir sidecars via session read-key or explicit `--changed-paths-file`.
  - From dyn-dyn-difficulty-records: After main-agent `difficulty write-record`, mirror the external path: call `run-log write --batch difficulty-rating` (or fold both into one shared Python helper invoked from SKILL and dispatch).
  - From dyn-dyn-difficulty-records: Build a changed-path list from the Step 2.4 pathspec (or post-implementation porcelain) and pass it to `difficulty write-record` on every implement path.
  - From dyn-dyn-difficulty-records: Use the same Python/run-log write path as external Step 2 and pass changed paths plus panel-skipped.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Step 2 floor matching uses the full dirty tree
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Step 2 floor matching includes unrelated dirty files from the entire working tree. That can raise `applied_tier` from paths that are not part of the implement change set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Match floors against manifest or recovery pathspec instead of the entire working tree.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: `write-record` falls back to MODERATE too eagerly
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `write-record` synthesizes a MODERATE fallback in normal records, so missing or invalid explicit ratings can be logged as if they were real ratings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Default fallback-tier to empty, only synthesize fallback on named recovery paths, and fail invalid explicit rating files.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Review core drops scout difficulty
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Review pipeline loses `SCOUT_DIFFICULTY_RATING`, so round metadata and standalone review cannot consume scout difficulty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Thread SCOUT_DIFFICULTY_RATING and status through review core rows/status files and consumers.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Step 2 difficulty write-record failures are silent
- **Reviewer(s)**: dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: `_write_step2_difficulty_record` can return silently on missing difficulty or CLI failures, so operators do not see a warning when the committed record was never refreshed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-difficulty-records: Log a bounded warning on any skip or non-zero CLI result, consistent with other Step 2 diagnostics.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

