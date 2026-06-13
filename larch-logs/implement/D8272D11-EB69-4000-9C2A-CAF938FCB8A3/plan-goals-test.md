## Goal
Implement issue #4256: [IMPLEMENTING] [BUG] ship-pr classifies merge-conflict-at-merge-time as review-required, blocking auto-recovery.

## Implementation Plan
## Plan

## Approach

- Keep the fix in the **Python ship path** only.
- Add a private lowercase conflict signal tuple in `python/merge.py`:
  - `"merge conflicts"`
  - `"cannot be cleanly created"`
  - `"not mergeable"`
- Add a private helper to classify merge-attempt conflict diagnostics:
  - accept `outcome.error`
  - normalize with `.lower()`
  - return true when any conflict signal is present
- In `_maybe_review_required`, keep the current early return unless the outcome is merge or policy related.
- After that early return, check conflict signals **before** calling `gh.pr_review_decision(...)`.
- Limit the conflict override to `MERGE_RESULT_ADMIN_FAILED`.
  - This matches the reported admin plus fallback failure.
  - This handles conflicts even when `reviewDecision` is `APPROVED`, empty, or unavailable.
  - This keeps `"not mergeable"` scoped to merge-attempt failures instead of broad policy checks.
  - This avoids changing `--no-admin-fallback` policy-denied behavior.
- Return `MergeResult(result=config.MERGE_RESULT_MAIN_ADVANCED, error=outcome.error)` when a conflict-specific signal matches.
- Keep the existing `REVIEW_REQUIRED` path for non-conflict diagnostics.
- Do not change `ship.py`.
  - It already treats `MERGE_RESULT_MAIN_ADVANCED` as a retry path back through CI monitor.
- Do not add a new result constant.
- Do not add rebase-budget checks in `_maybe_review_required`.

## Files to modify/create

### UPDATED: python/merge.py

- Add `_MERGE_CONFLICT_SIGNALS` near the existing module-private regex constants.
- Include the merge-time conflict phrases:
  - `"merge conflicts"`
  - `"cannot be cleanly created"`
  - `"not mergeable"`
- Add `_has_merge_conflict_signal(error: str | None) -> bool`.
- Implement the helper with:
  - `lowered = (error or "").lower()`
  - `any(signal in lowered for signal in _MERGE_CONFLICT_SIGNALS)`
- In `_maybe_review_required`, place the conflict check:
  - after the existing early guard for non-merge, non-policy outcomes
  - before `gh.pr_review_decision(...)`
- Guard the override with:
  - `outcome.result == config.MERGE_RESULT_ADMIN_FAILED`
  - `_has_merge_conflict_signal(outcome.error)`
- Preserve `outcome.error` in the returned `MAIN_ADVANCED` result.
- Leave policy-denied and no-admin-fallback review behavior unchanged.

### UPDATED: python/test_merge.py

- Add regression coverage near `test_merge_pr_review_required_after_admin_failed`.
- Use the existing `_open_pr_responses()` helper.
- Mock the normal successful pre-merge setup:
  - checks pass
  - local head resolves
  - version race gate returns none
  - post flush succeeds
- Simulate admin merge failure with the reported combined diagnostic:
  - `"PR requires approving review"`
  - `"Pull Request has merge conflicts"`
  - `"not mergeable"`
  - `"cannot be cleanly created"`
- Ensure the conflict result does **not** depend on `gh.pr_review_decision(...) == "REVIEW_REQUIRED"`.
  - Prefer asserting `pr_review_decision` is not called for this conflict path if the test harness makes that practical.
  - Otherwise cover `APPROVED` or empty review decision and assert the result still becomes `MERGE_RESULT_MAIN_ADVANCED`.
- Assert:
  - result is `config.MERGE_RESULT_MAIN_ADVANCED`
  - error keeps the merge diagnostic text
- Add focused coverage for a bare `"not mergeable"` merge-attempt diagnostic.
  - It should return `MERGE_RESULT_MAIN_ADVANCED` under the `ADMIN_FAILED` guard.
  - It should not require a review-required decision.
- Add or extend a narrow negative assertion with a review-only diagnostic.
  - It must lack `"merge conflicts"`, `"cannot be cleanly created"`, and `"not mergeable"`.
  - It should still call the review-decision path.
  - It should return `MERGE_RESULT_REVIEW_REQUIRED` when `gh.pr_review_decision(...)` returns `"REVIEW_REQUIRED"`.
- Keep `test_merge_pr_review_required_after_admin_failed` unchanged unless its fixture contains one of the new conflict signals.
  - If it does, change that fixture to a review-only diagnostic so it remains the negative control.

## Edge cases

- If GitHub reports both review-required and conflict-specific text, conflict wins for admin plus fallback merge failures.
- If GitHub reports conflict text while `reviewDecision` is `APPROVED` or empty, conflict handling still wins.
- If the error only says `"not mergeable"` during an admin plus fallback merge failure, conflict handling wins.
- If the error lacks conflict text, review-required behavior stays unchanged.
- If `--no-admin-fallback` is set, existing review-required behavior stays unchanged.
- Matching should be case-insensitive.

## Failure modes

- If the signal list is too broad, ship may rebase when the true blocker is review-only.
  - Keep `"not mergeable"` scoped by the `MERGE_RESULT_ADMIN_FAILED` guard.
- If GitHub changes wording, this fix may miss new conflict phrasing.
  - The existing `mergeStateStatus` checks still cover pre-merge conflict states.
- If the conflict check remains behind `REVIEW_REQUIRED`, approved or empty review states can still stall at merge.
  - Place the check before `gh.pr_review_decision(...)`.

## Testing strategy

- Run the focused test:
  - `python3 -m pytest python/test_merge.py -k 'review_required or conflict or not_mergeable'`
- Run the module test:
  - `python3 -m pytest python/test_merge.py`
- Run the required repo check after implementation:
  - `bash scripts/relevant-checks.sh`

## Acceptance

- `_maybe_review_required` in `python/merge.py` returns `MERGE_RESULT_MAIN_ADVANCED` when `outcome.result == MERGE_RESULT_ADMIN_FAILED` and `outcome.error` contains any of the three conflict signals.
- The check fires before `gh.pr_review_decision()` so it works regardless of review approval state.
- `test_merge.py` has a positive test (conflict signals → MAIN_ADVANCED) and a negative control (no conflict signals → REVIEW_REQUIRED via existing path).
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 90

## Test plan
(no test plan section in plan-file)
