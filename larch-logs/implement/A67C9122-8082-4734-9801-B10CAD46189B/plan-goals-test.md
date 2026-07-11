## Goal
Implement issue #6913: [IMPLEMENTING] [Bug] /implement terminal: Post-merge log flush failed after admin_merged because local checkout moved to main (transient-infra at unknown).

## Implementation Plan
## Plan

## Approach

Treat a skipped post-merge log flush as normal after `finalize.postmerge` succeeds.

- Keep calling `finalize_postmerge_logs` when the existing eligibility check passes.
- Ignore its `RefreshSkip` result.
- Remove the warning breadcrumb, STALLED finalize-state write, STALLED ship-state write, and early STALLED return.
- Let control reach the existing DONE ship-state write and `Outcome.OK` result.
- Leave post-merge finalize failures unchanged.
- Leave `ship_resume.py`, pre-merge flushing, and flush skip-reason logic unchanged.

## Files to modify/create

### UPDATED: python/larch/implement/ship_pr.py

Update `run_postmerge_phase` so a skipped `finalize_postmerge_logs` call does not alter the successful post-merge outcome. Preserve the flush attempt and the existing DONE/OK path.

### UPDATED: python/tests/implement/test_ship.py

Replace the regression test that expects a STALLED post-merge flush skip with one that verifies:

- The flush is still attempted.
- The result is `Outcome.OK` with the merged PR metadata preserved.
- `ship-pr-state.sh` records `PHASE=done` and no stall tracking.
- `finalize-state.sh` does not gain postmerge-flush stall metadata.
- Stderr contains no post-merge flush warning breadcrumb.

Keep existing coverage for successful flushes, ineligible flushes, and actual `finalize.postmerge` failures.

## Edge cases

- A skip with any reason, including checkout drift or commit failure, must follow the same silent success path.
- A non-OK result from `finalize.postmerge` must still return its existing terminal outcome.
- Runs that do not meet `_postmerge_should_flush` must continue directly to DONE without calling the flush.
- The fix must not change recovery behavior for already-stalled runs.

## Failure modes

- Removing the flush call would lose the best-effort behavior. Keep the call and ignore only its skip result.
- Leaving any warning or stall-state write in the skip branch would preserve the reported defect.
- Broadening the change into `ship_resume.py` would violate the approved scope.

## Testing strategy

Run the focused regression test first:

`python3 -m pytest -q python/tests/implement/test_ship.py -k postmerge_flush_skip`

Then run the full changed test module:

`python3 -m pytest -q python/tests/implement/test_ship.py`

Run Python lint and type checks for the changed runtime and test files through the repository's changed-file workflow, or run `make py-lint` if no narrower supported target is available.

Confidence: high. The faulty branch and its regression test are direct and localized. The ship-driver floor makes this MODERATE despite the small diff.

## Acceptance

Run the focused regression test first:

`python3 -m pytest -q python/tests/implement/test_ship.py -k postmerge_flush_skip`

Then run the full changed test module:

`python3 -m pytest -q python/tests/implement/test_ship.py`

Run Python lint and type checks for the changed runtime and test files through the repository's changed-file workflow, or run `make py-lint` if no narrower supported target is available.

Confidence: high. The faulty branch and its regression test are direct and localized. The ship-driver floor makes this MODERATE despite the small diff.

diff_added: 12
diff_deleted: 16
mechanical_churn: false
diff_lines: 28

## Test plan
(no test plan section in plan-file)
