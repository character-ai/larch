### OOS_1: [OUT_OF_SCOPE] ci_monitor case-sensitive bucket matching
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ci-merge-policy
- **Severity**: latent
- **Concern**: Optional JSON classification in `ci_monitor._classify_checks_json` still compares buckets case-sensitively (`== "fail"` / `== "pending"`), while `gh._pr_check_bucket` lowercases. A capitalized bucket like `"Pending"` can yield monitor `merge` while the merge gate blocks with `CI_NOT_READY`. Pre-existing monitor/gate skew; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] alternating gh failures reset stall guard
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The unchanged-detail stall guard resets when diagnostics change. Transient `gh` failures that alternate between `"unable to read PR checks"` and real blocker text can prevent reaching `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD`, allowing fallback to the 50-iteration cap. Residual weakness of the guard design, not the cancelled/skipping bug this PR fixes.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] duplicated blocking-bucket policy between gh and ci_monitor
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ci-merge-policy
- **Severity**: latent
- **Concern**: Blocking JSON bucket policy is defined in `gh._CHECKS_JSON_BLOCKING_BUCKETS` while `ci_monitor._classify_checks_json` still inlines `fail`/`pending` matching. Future policy edits can reintroduce monitor/merge disagreement without a compile-time link. The plan accepts this duplication; a shared constant would reduce drift but is outside this change's scope.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] missing ship-level test for REVIEW_REQUIRED precedence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: There is no ship-level test that `MERGE_RESULT_CI_NOT_READY` plus `pr_review_decision() == "REVIEW_REQUIRED"` still routes to `Outcome.NEEDS_USER_INPUT` instead of the new `merge-ci-not-ready` stall. `test_merge_pr_ci_not_ready_even_when_review_required` covers `merge.py`, but the plan's failure-mode note is not locked at the ship layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a ship test with mocked `merge_pr` returning `CI_NOT_READY` and `pr_review_decision` returning `REVIEW_REQUIRED`, asserting `NEEDS_USER_INPUT` and no `STALL_STEP=merge-ci-not-ready`.

### OOS_5: [OUT_OF_SCOPE] missing test for race-branch diagnostic string
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `pr_checks_not_ready_detail` has no test for the race branch that returns `"no fail or pending PR checks remain"` when JSON rows are mergeable under the new policy but `merge_pr` still reported `CI_NOT_READY`. That string drives the stall guard on transient read disagreement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test with JSON like `[{"name":"ci","bucket":"cancelled"}]` (or pass+cancelled mix) asserting that exact detail.

### OOS_6: [OUT_OF_SCOPE] test_merge_retry_results_consume_iteration_budget brittleness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `test_merge_retry_results_consume_iteration_budget` still does not stub `pr_checks_not_ready_detail` or `pr_review_decision`, so it depends on `RecordingRunner` default empty `gh` responses for the new `CI_NOT_READY` path. It passes today with one `CI_NOT_READY`, but it is brittle if the test scenario grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Stub those helpers explicitly, as the new stall-guard tests do.

### OOS_7: [OUT_OF_SCOPE] _CiNotReadyGuard not persisted across resume
- **Reviewer(s)**: dyn-dyn-ci-merge-policy
- **Severity**: latent
- **Concern**: `_CiNotReadyGuard` is reinitialized on every `run_ship` call and is not persisted in ship state, so a resumed merge loop keeps `ITERATION` but resets the guard counter, weakening early stall protection across process resumes. The iteration cap remains the backstop.
- **Suggested revisions (informational for voters; coder decides)**:
