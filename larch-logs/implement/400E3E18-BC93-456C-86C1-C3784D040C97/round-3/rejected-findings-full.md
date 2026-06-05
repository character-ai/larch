### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: MAV re-tally env key convention is assumed but not verified
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The deferred implement helper expects `ACCEPTED_COUNT`/`REJECTED_COUNT` keys in `review-tally.env`, but there is no direct test that `tally-code-votes.sh --review-tmpdir` writes those exact keys for MAV re-tally handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Design round-start no-clobber behavior can preserve stale timestamps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `_persist_plan_round_start` intentionally uses no-clobber semantics, but if a prior re-entry left a `round-start-s` for the same round number, duration can be inflated by preserving the stale start timestamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Implement in-loop round timing bypasses deferred helper count/idempotency path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_emit_implement_round_timing_row` writes directly via `timing-ledger.sh record-round` using `IRF_LAST_*` counts, while deferred MAV paths use `record-implement-review-round-timing.sh` and re-tally into `review-tally.env`. Counts and idempotency behavior can diverge for the same round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Implement in-loop guard verification can miss a written row and allow duplicates
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-handoff-telemetry-output.txt
- **Severity**: latent
- **Concern**: `_emit_implement_round_timing_row` only sets its guard after an awk probe matches the just-written row. If the row is written but the probe misses it due to visibility, path, sanitization, or exact timestamp matching, the guard remains unset and a later call can write a duplicate row with a different duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-handoff-telemetry-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: record-plan OOS tally uses less-portable awk trim pattern
- **Reviewer(s)**: dyn-bash32-compat-output.txt
- **Severity**: latent
- **Concern**: The AWK trim uses alternation in a single `gsub` pattern. Although POSIX-compliant, reviewers flagged potential macOS awk edge cases that could leave whitespace and cause OOS counts to read as zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-compat-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: timing-report interval test lacks negative assertion for orphan rounds
- **Reviewer(s)**: dyn-interval-attachment-output.txt
- **Severity**: nit
- **Concern**: The fixture verifies expected Step 5 round arrays but does not assert that an orphaned round attaches nowhere else. A future interval-only refactor could attach it to an unexpected step without failing the current assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interval-attachment-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Implement loop has many scattered timing emit call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Numerous branches duplicate `_emit_implement_round_timing_row` calls. A future terminal/stall/continue branch can omit the emit call and silently drop per-round timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Deferred round-timing helper plumbing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Design and implement deferred timing helpers duplicate tmpdir, ledger, and idempotency plumbing, so future fixes may drift between the two paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: timing-report round sorting uses ad hoc O(n²) bubble sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `emit_round_array` uses a bubble sort for matched rounds, inconsistent with other renderer sorting patterns. This is not currently breaking but is avoidable maintenance debt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

