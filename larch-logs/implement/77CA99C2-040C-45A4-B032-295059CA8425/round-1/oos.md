### FINDING_11: Make attempt allocation recoverable across start and finalize
- **Reviewer(s)**: dyn-dyn-bgjob-lineage
- **Severity**: major
- **Concern**: Attempt numbering is split between lineage TSV rows, appended only during `--finalize`, and `fixer-rounds.tsv`, written when the lane completes. If a successful bgjob is not finalized or finalize fails before lineage append, the next start can reuse an attempt already recorded by the lane and wedge the waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lineage: Derive the next attempt from both lineage and `fixer-rounds.tsv` (or a single source of truth), add a finalize completion sentinel keyed by `STEP`, and/or let finalize succeed idempotently when merge/status envelopes already validate so a completed tier can be recovered without relaunching the lane.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] Register the wrapper harness in CI shards
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-ci-fixer.sh` is not included in the default Makefile CI harness shards, so the wrapper smoke harness may not run on the default branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Add explicit Step 8 orchestration fences
- **Reviewer(s)**: dyn-dyn-bgjob-lineage
- **Severity**: minor
- **Concern**: The Step 8 `ci-fix` protocol is documented in prose but lacks thin launcher fences for `--start`, the identical `bgjob wait --step "$STEP"` command, and `--finalize`. This increases the risk of improvised polling or skipped finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lineage: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Strengthen tmpdir containment checks
- **Reviewer(s)**: dyn-dyn-bgjob-lineage
- **Severity**: minor
- **Concern**: `safe_root` verifies only that `IMPLEMENT_TMPDIR` is absolute and non-symlink, while the retired path helper also enforced canonical containment under the tmp root. The weaker check leaves a TOCTOU risk before launch-envelope writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lineage: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Restore fence-shape regression coverage
- **Reviewer(s)**: dyn-dyn-bgjob-lineage
- **Severity**: minor
- **Concern**: The plan-listed `scripts/test-implement-fence-shape.sh` was not updated for dynamic `STEP` capture, identical wait commands, and finalize ordering, while the structure harness adds only string-presence checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lineage: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
