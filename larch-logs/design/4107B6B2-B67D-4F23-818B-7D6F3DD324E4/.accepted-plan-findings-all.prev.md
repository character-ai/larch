### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/merge.py:476-500
- **Concern**: [SCOPE-REDUCTION] Standalone "not mergeable" in _MERGE_CONFLICT_SIGNALS is over-broad. Scenario: GitHub policy-only plain-merge failures can include "not mergeable" without merge conflicts; with review_decision REVIEW_REQUIRED the plan would return MAIN_ADVANCED and trigger rebase/CI retries instead of review-required stall
- **Proposed resolution**: Drop standalone "not mergeable"; match only "merge conflicts" or "cannot be cleanly created", or require both "not mergeable" and "cannot be cleanly created"


### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/merge.py:31-32
- **Concern**: [SCOPE-REDUCTION] Standalone "not mergeable" is planned as a conflict signal. Scenario: GitHub can emit "not mergeable" for base branch policy, so review-required policy failures can be mapped to MAIN_ADVANCED and loop instead of returning review_required
- **Proposed resolution**: Remove bare "not mergeable" or require it with "cannot be cleanly created"; keep only conflict-specific phrases such as "merge conflicts" and "cannot be cleanly created"




### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/merge.py (plan.txt:6-11,55-62)
- **Concern**: The plan omits the explicitly scoped `"not mergeable"` conflict signal and adds a negative assertion that preserves the current bug for that wording.. Scenario: If GitHub reports the merge-time conflict as `"not mergeable"` without also saying `"merge conflicts"` or `"cannot be cleanly created"`, `_maybe_review_required` will still return `review_required` and block the existing auto-recovery path.
- **Proposed resolution**: Include `"not mergeable"` in `_MERGE_CONFLICT_SIGNALS` under the planned `ADMIN_FAILED` plus `REVIEW_REQUIRED` guard, and update the negative test to use a non-conflict review-only diagnostic instead.



### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/merge.py:489-491
- **Concern**: [SCOPE-REDUCTION] Conflict override is gated on pr_review_decision REVIEW_REQUIRED but the issue requires treating merge-conflict diagnostics independently of review gating. Scenario: When admin+fallback merge fails with conflict keywords and reviewDecision is APPROVED or empty, _maybe_review_required returns MERGE_RESULT_ADMIN_FAILED at line 491 and ship.py stalls at merge (ship.py:1722-1737) instead of looping for rebase
- **Proposed resolution**: After the early ADMIN_FAILED/POLICY_DENIED guard, if outcome.result is MERGE_RESULT_ADMIN_FAILED and outcome.error matches _MERGE_CONFLICT_SIGNALS, return MERGE_RESULT_MAIN_ADVANCED before calling gh.pr_review_decision; keep the existing REVIEW_REQUIRED path only when no conflict signals match


