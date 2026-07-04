## Proposed Design Outline

### Goals
- Add an aggregate-severity trigger to both tally functions so unaccepted OOS items promote to the filing batch when ≥1 `important`/`blocking` or ≥3 `latent` pool items exist.
- Fix Bug A: make the annotate handoff resilient to empty `/issue` stdout by emitting a retryable error state instead of silently stranding accepted OOS.
- Fix Bug B: on same-issue `/design` re-runs, skip filing only when the sentinel fully covers all accepted blocks; file new unfiled blocks otherwise.

### Non-goals
- No change to the vote-accepted path; this augments it.
- No changes to downstream filers (`oos_filer.py`, `file_oos.py`); they already handle non-empty batches.
- Security-classed OOS stays private regardless of the trigger.
- No changes to `/implement` main-agent OOS routing; the trigger evaluates only reviewer-surfaced items in the current ballot.

### Approach sketch
- In `plan_review_tally.py._render`: collect a `pool_chunks` list (non-security, non-accepted OOS + rerouted findings) and their severity during the item loop; evaluate the trigger at end of loop; append pool items to `oos_accepted_chunks` when trigger fires.
- In `review_tally.py.tally_code_votes`: mirror the same pool collection and trigger evaluation before writing final outputs; write qualifying pool items to `oos_accepted_file` (and `oos_accepted_out` when different).
- In `design_oos.py.file_oos_annotate_main` (line 790-797): on empty stdout, emit a louder WARN with a `NEXT_ACTION` that allows orchestrator retry, rather than returning rc=1 with no retry path.
- In `design_oos.py.file_oos_prepare_main` (line 403-414): after recovering sentinel URLs into `oos-accepted-design.md`, extract unfiled blocks from the updated accepted text; emit `skip-sentinel` only when no unfiled blocks remain, else fall through to normal prepare and file.

### Surfaces in scope
- `python/larch/review/plan_review_tally.py`
- `python/larch/review/review_tally.py`
- `python/larch/design/design_oos.py`
- `python/tests/review/test_plan_review.py`
- `python/tests/review/test_review_tally.py`
- `python/tests/design/test_design_oos.py`

### Open questions
- None.
