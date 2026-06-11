# Review Round 1

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: REVIEW_REQUIRED shortcut can admin-merge before CI, head, and version gates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-merge-review-integration-output.txt
- **Severity**: important
- **Concern**: The `REVIEW_REQUIRED` branch runs from the CI-not-ready path and calls `_attempt_merge(..., admin=True)` before the normal merge safety chain. This can bypass failing or pending CI, admin-eligible `mergeStateStatus` checks, local head matching, and version-race gates. It can also report review-required remediation when CI is the real blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require admin-eligible mergeStateStatus and run head-match and race gates before _attempt_merge on the fast path
  - From codex-specialist-correctness-output.txt: Only consider review-required admin fallback after the normal merge gates pass and a merge failure confirms REVIEW_REQUIRED; otherwise return CI_NOT_READY and preserve existing head/version checks.
  - From cursor-specialist-edge-cases-output.txt: Reuse the main-path pre-merge gate sequence before _attempt_merge on the REVIEW_REQUIRED branch
  - From codex-specialist-testing-output.txt: Move the reviewDecision probe to the failed-merge path after existing gates, keep failing CI as ci_not_ready, and add merge/ship tests for admin success, admin failure, and no-admin-fallback.
  - From dyn-merge-review-integration-output.txt: Do not call `_attempt_merge` from the CI-not-ready branch. Gate admin retry on confirmed-green CI (same as bash), or move detection to after a failed merge when `mergeStateStatus` is `BLOCKED`/`UNSTABLE` and checks are green; keep returning `CI_NOT_READY` when checks are pending or failing for non-review reasons.
  - From dyn-merge-review-integration-output.txt: Reuse the existing post-CI path (state check, head match, version race) before any admin merge attempt; only add the `REVIEW_REQUIRED` branch after those gates pass, or after a failed merge attempt on that guarded path.
  - From dyn-merge-review-integration-output.txt: Only emit `MERGE_RESULT_REVIEW_REQUIRED` when CI is confirmed passing and merge/review policy is the sole blocker; otherwise preserve `CI_NOT_READY` (or include explicit CI status in the terminal detail).


### FINDING_2: Green REVIEW_REQUIRED PRs can fall through to generic merge failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The normal gated merge path does not query `reviewDecision` after a failed merge attempt. A green PR blocked only by required review can return `admin_failed` or `policy_denied`, causing `ship.py` to report a generic stalled merge instead of `NEEDS_USER_INPUT` for review-required approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: After unsuccessful gh pr merge results in _attempt_merge, query reviewDecision and translate REVIEW_REQUIRED to MERGE_RESULT_REVIEW_REQUIRED with the requested user-input detail.
  - From codex-specialist-edge-cases-output.txt: Query reviewDecision after failed merge attempts, or before returning ADMIN_FAILED/POLICY_DENIED for blocked merge state, and return MERGE_RESULT_REVIEW_REQUIRED.
  - From codex-specialist-testing-output.txt: Move the reviewDecision probe to the failed-merge path after existing gates, keep failing CI as ci_not_ready, and add merge/ship tests for admin success, admin failure, and no-admin-fallback.


### FINDING_3: Missing merge.py tests for REVIEW_REQUIRED admin fallback behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_merge.py` lacks behavioral coverage for `REVIEW_REQUIRED` cases, including admin success, admin failure, and no-admin-fallback outcomes. This can let regressions reintroduce CI-not-ready loops or incorrect generic merge stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add RecordingRunner tests for REVIEW_REQUIRED with no-admin-fallback admin-failed and successful admin paths
  - From codex-specialist-testing-output.txt: Move the reviewDecision probe to the failed-merge path after existing gates, keep failing CI as ci_not_ready, and add merge/ship tests for admin success, admin failure, and no-admin-fallback.


### FINDING_4: Missing ship.py merge-loop test for REVIEW_REQUIRED early exit
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` does not assert that `MERGE_RESULT_REVIEW_REQUIRED` exits the merge loop as `Outcome.NEEDS_USER_INPUT`. A regression could continue looping until the merge-loop iteration cap instead of surfacing the review-required stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test stubbing merge.merge_pr to return review_required and assert Outcome.NEEDS_USER_INPUT plus no iteration-cap path
  - From codex-specialist-testing-output.txt: Move the reviewDecision probe to the failed-merge path after existing gates, keep failing CI as ci_not_ready, and add merge/ship tests for admin success, admin failure, and no-admin-fallback.


### FINDING_5: stall-recovery merge-loop-iteration-cap allowlist lacks fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The stall-recovery classifier changes for `merge-loop-iteration-cap` are not covered by harness fixtures. Removing the classifier branch or safe-step entry could restore transient-infra misclassification without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add classify_fixture for merge-loop-iteration-cap and include it in case20 production step-token preservation loop


