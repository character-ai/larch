## Decision 1: Fix scope — Part A only, Part B deferred
- **Question**: Should this fix cover only the exit-1 crash (Part A), or also resolve harness-regenerated baseline ownership (Part B)?
- **Resolution**: Part A only. Fix `_commit_fixes_stage_all` so an all-clean collected path set is a benign noop. Part B (regenerated ratchet baselines stranding the tree dirty) is explicitly out of scope — it is a distinct ownership question (how to distinguish regenerated baselines from pre-existing unrelated dirt) that likely touches the check-running flow, not just commit-fixes. Consistent with #5715's philosophy that non-review-delta dirt is unrelated and left alone.
- **Source**: user

## Hard constraints (carry into plan)
- Behavior must remain: empty collected path list → benign noop (issue #5715, `review_and_fix.py:193`).
- New behavior required: nonempty collected path list where every path is already clean → benign noop (exit 0, `COMMIT_OUTCOME=noop`), NOT a Tool Failure.
- Partially-clean set must still commit the dirty subset correctly (do not regress the working commit path).
- Baseline files (`*-baseline.json` etc.) must NOT be specially staged or reverted by this change; they stay out of scope.
- Fix is scoped to `_commit_fixes_stage_all` (the `--stage-all` path). The non-`--stage-all` path (`review_and_fix.py:1280`) is unaffected and must not change.

## Non-goals
- No baseline-ownership logic (no staging/reverting of `*-baseline.json`).
- No changes to `_collect_review_fix_stage_paths` collection semantics.
- No changes outside `python/larch/review/review_and_fix.py`.
