### OOS_1: [OUT_OF_SCOPE] _finalize_dropped_reviewer_round is a misleading no-op
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `_finalize_dropped_reviewer_round` in `python/review_pipeline.py:2285-2291` is a no-op loop; diagnostics are already produced by `agent_waterfall`. Maintainers may assume extra staging happens here; future edits could duplicate or break waterfall-owned diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove the stub or implement/document the intended staging contract.

### OOS_2: [OUT_OF_SCOPE] Synthetic dyn-slot drop key path appears unreachable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The synthetic dyn-slot drop key path in `python/review_pipeline.py:1955-1959` appears unreachable because `_dynamic_drop_output_base` always resolves `dyn-*` basenames. The dead code path is untested; FINDING_3 relies on base-in-statuses skip instead. No user-visible breakage today; the synthetic fallback could rot silently if heuristics change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add explicit unit test or remove unreachable synthetic branch if heuristics guarantee resolution.

### OOS_3: [OUT_OF_SCOPE] Invalid-slot drops invisible to threshold accounting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Invalid-slot drops remain on `*.invalid-slots` and are not fed into threshold accounting or `progress_report` dropped-slot merging. Dynamic invalid-slot drops stay invisible to the new accounting, same as before this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire invalid-slots into threshold/progress_report if parity with straggler drops is desired (separate issue).

### OOS_4: [OUT_OF_SCOPE] Static-straggler warning test omits production-shaped manifest
- **Reviewer(s)**: dyn-dyn-threshold-accounting-output.txt
- **Severity**: latent
- **Concern**: `python/test_review_and_fix.py:507-530` omits a manifest containing `dyn-*` rows, so it does not catch the production false-positive in FINDING_16. A fixture with both a static straggler drop row and a dynamic manifest entry would match `_run_round` and fail today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-threshold-accounting-output.txt: A fixture with both a static straggler drop row and a dynamic manifest entry would match `_run_round` and fail today.

### OOS_5: [OUT_OF_SCOPE] Missing review-core-threshold.env fallback in _failed_reviewers
- **Reviewer(s)**: dyn-dyn-threshold-accounting-output.txt
- **Severity**: latent
- **Concern**: The plan called for secondary `FAILED_SLOTS` / `DROPPED_SLOTS` fallback from `review-core-threshold.env` when labels are unavailable; `_failed_reviewers` in `python/progress_report.py:989-1027` only merges collector and dropped-slot sources today.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no fix direction provided by reviewer)

