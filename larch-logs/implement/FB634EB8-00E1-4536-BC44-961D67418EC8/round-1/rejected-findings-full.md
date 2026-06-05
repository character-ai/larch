### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `flush_logs_pre` performs duplicate manifest recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `flush_logs_pre` recovers the manifest via both `load_or_recover_manifest_checked` and `update_manifest`, which can repeat synthesis/write work and make fail-closed recovery reasoning harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Quiet-log OSError suppression is unrelated review surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: An unrelated quiet-log `OSError` suppression change is bundled with finalize parity work, expanding the review surface and blurring scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Timing harness additions may overload Make shard 16
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New timing harness targets were added to shard 16 without rebalancing, risking intermittent wall-time flakes in that CI shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Orphan cleanup hard reset can destroy misclassified local work
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Orphan cleanup may `git reset --hard origin/main` when flush-subject and larch-logs-only guards pass. If those guards misclassify commits or path prefixes, unpushed non-log work on `main` can be destroyed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_24: Detached-HEAD postbump preflight branch fallback appears inverted
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `postbump_preflight` can treat detached HEAD with a valid target branch in context as branch mismatch instead of using the target branch per bash guard semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_29: Ship postmerge phase may remain stuck at `postmerge`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: After `run_postmerge_phase`, Python writes `phase=done` only on `Outcome.OK`, while bash advances to `done` after postmerge finalize even for cleanup partials. Python can leave state at `postmerge`, blocking resume semantics bash would not block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: Step 5 resume marks timing ledger but not token ledger
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: `run-step5-review.sh --starting-round > 1` writes a timing mark but no matching token mark, causing token and timing ledgers to disagree on Step 5 segment boundaries after handoff resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: Design round timing idempotency can append duplicate rows
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` only skips duplicates when counts also match. A second call with the same round/start/end but different post-MAV counts appends another row; JSON may dedupe while raw TSV consumers see inconsistent history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

