### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: standalone reviews need a hoisted slug-valid gate
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-review-runlog
- **Severity**: important
- **Concern**: `review_run_id_valid` is only set inside the scout-manifest bash fence, so standalone `SCOUT_STATUS=na` reviews can skip transcript capture and commit even when `RUN_ID` is slug-valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Hoist a single shell snippet after line 75 that sets review_log_root and review_run_id_valid; gate all log-phase capture and commit prose on review_run_id_valid; remove duplicate assignments from the scout-only block
  - From cursor-specialist-edge-cases: Hoist slug-valid RUN_ID computation to orchestrator prose right after line 75; set review_run_id_valid before any log-phase, capture, or commit step
  - From cursor-specialist-testing: Hoist a shared bash fence that sets review_log_root and review_run_id_valid before all Step 4 log work, or inline the slug-valid test on the capture/commit lines
  - From dyn-dyn-review-runlog: Hoist the slug-valid computation into its own unconditional Step 4 fence (set review_run_id_valid=false, then flip it true with the same predicate as run_log_batch.validate_run_id_slug) before any bulk review log-phase, capture, or commit work; keep the scout jq block gated only on SCOUT_STATUS.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: bulk Step 4 logging still trusts non-empty RUN_ID
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-review-runlog
- **Severity**: important
- **Concern**: The bulk Step 4 opener still leads with `RUN_ID` non-empty instead of an explicit slug-valid predicate, so invalid-but-non-empty IDs can reach the first log-phase calls before the guard is clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Gate all Step 4 log-phase writes on review_run_id_valid only; remove or subordinate the bare non-empty RUN_ID check
  - From cursor-specialist-testing: Align line 77 with an executable slug-valid guard and extend scripts/test-review-structure.sh pin (18) for review_log_root and validate_run_id_slug wording
  - From dyn-dyn-review-runlog: Replace the line 77 opener with an explicit slug-valid predicate (or `review_run_id_valid=true`) as the sole gate, and update the `(18)` structure pin in `scripts/test-review-structure.sh` to match.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

