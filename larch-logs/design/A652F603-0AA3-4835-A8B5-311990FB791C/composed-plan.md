## Plan

## Approach

- Keep the fix in the ship loop.
- Treat `MERGE_RESULT_CI_NOT_READY` as pending CI when admin fallback is enabled.
- Only convert `CI_NOT_READY` to `REVIEW_REQUIRED` when `working.no_admin_fallback` is true and GitHub reports `REVIEW_REQUIRED`.
- Route the admin-fallback path through `_handle_merge_ci_not_ready(...)` and `continue`.
- Do not change `merge.py`, retry constants, `_attempt_merge`, or the CI stall guard.
- Fix the review-required bail text so it does not hardcode `mergeStateStatus=BLOCKED`.
- Fetch the current merge state only for the `--no-admin-fallback` review-required bail. If the read fails, omit the state instead of inventing one.

## Files to modify/create

### UPDATED: python/larch/implement/ship.py

- In the `merged.result == config.MERGE_RESULT_CI_NOT_READY` branch:
  - Check `working.no_admin_fallback` before calling `gh.pr_review_decision`.
  - When `working.no_admin_fallback` is false, skip `pr_review_decision` and call `_handle_merge_ci_not_ready(...)`.
  - When `working.no_admin_fallback` is true:
    - Preserve the existing review-required terminal route if `reviewDecision == "REVIEW_REQUIRED"`.
    - Otherwise call `_handle_merge_ci_not_ready(...)` as today.
- Add a small private helper near the merge-loop helpers if needed:
  - Read `gh.pr_merge_state(...).merge_state_status`.
  - Return a formatted parenthetical such as ` (mergeStateStatus=UNKNOWN)` only when a state is available.
  - Catch `ShipError` or use an existing safe read pattern so a diagnostic refresh failure does not replace the intended review-required handoff.
- Replace the hardcoded detail:
  - From `mergeStateStatus=BLOCKED`.
  - To the observed merge state when available, or no merge-state claim when unavailable.
- Keep the final `MERGE_RESULT_REVIEW_REQUIRED` handling unchanged.

### UPDATED: python/tests/implement/test_ship.py

- Add a regression test for the default admin-fallback path:
  - Start from `PHASE=ci-initial`, `MERGE=true`, open PR stubs, and default `no_admin_fallback=False`.
  - Make `ship.merge.merge_pr` return `MERGE_RESULT_CI_NOT_READY`, then `MERGE_RESULT_DRIVER_ALREADY_MERGED`.
  - Make `ship.gh.pr_checks_not_ready_detail` return a pending-check detail.
  - Make `ship.gh.pr_review_decision` fail the test if called, because review state must not affect routing while admin fallback is enabled.
  - Make `run_postmerge_phase` return OK.
  - Assert the run reaches OK, consumes both merge results, and does not produce `NEEDS_USER_REVIEW_REQUIRED`.
- Add or update a `--no-admin-fallback` regression test:
  - Use `no_admin_fallback=True`.
  - Make `merge_pr` return `MERGE_RESULT_CI_NOT_READY`.
  - Make `pr_review_decision` return `REVIEW_REQUIRED`.
  - Make the merge-state read return `UNKNOWN` or another explicit state.
  - Assert `Outcome.NEEDS_USER_INPUT`, `NEEDS_USER_REVIEW_REQUIRED`, and a detail containing the observed state.
  - Assert the detail does not contain the old false `mergeStateStatus=BLOCKED` string unless the mocked state is actually `BLOCKED`.
- Keep existing CI-not-ready guard tests valid. If they no longer need `pr_review_decision` on the admin path, remove those stubs or turn them into no-call assertions.

## Edge cases

- `reviewDecision == "REVIEW_REQUIRED"` plus admin fallback enabled:
  - Wait for CI and re-loop.
  - Later, once `mergeStateStatus` is determinable, `merge.py` can reach `_attempt_merge` and try `--admin`.
- `reviewDecision == "REVIEW_REQUIRED"` plus `--no-admin-fallback`:
  - Bail as review-required, because no admin bypass is allowed.
- `reviewDecision` empty, approved, or unavailable:
  - Existing CI-not-ready wait path remains unchanged.
- Merge-state diagnostic read fails:
  - Bail remains review-required.
  - The message omits the state instead of fabricating one.
- CI stays pending forever:
  - Existing `_CiNotReadyGuard` and `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD` still bound the loop.

## Failure modes

- A misplaced `continue` could fall through to terminal merge handling after a CI-not-ready result.
  - Tests should assert the admin-fallback path re-loops.
- Calling `pr_review_decision` on the admin-fallback path could reintroduce the premature bail.
  - The new test should fail if that call happens.
- A diagnostic merge-state read could raise and mask the intended handoff.
  - Keep it best-effort.

## Testing strategy

- Run the focused Python test file:
  - `python3 -m pytest python/tests/implement/test_ship.py`
- If available and dependencies are installed, run scoped lint for changed Python:
  - `make py-lint`
- Do not run broad repo sweeps unless the implementation changes more surfaces than planned.

## Acceptance

- Run the focused Python test file:
  - `python3 -m pytest python/tests/implement/test_ship.py`
- If available and dependencies are installed, run scoped lint for changed Python:
  - `make py-lint`
- Do not run broad repo sweeps unless the implementation changes more surfaces than planned.

review_status: ok
rounds_completed: 1
diff_added: 75
diff_deleted: 15
mechanical_churn: false
diff_lines: 90
