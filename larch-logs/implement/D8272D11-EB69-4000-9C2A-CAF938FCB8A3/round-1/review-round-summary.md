# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: python/merge.py:35-38,499-506
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Standalone "not mergeable" is a conflict signal and the check runs before pr_review_decision() Admin+plain merge both fail with admin_diag "PR requires approving review" and plain_diag "not mergeable" but no real conflict; branch is up to date. Fix returns MAIN_ADVANCED, ship loops up to 50 iterations, then stalls instead of immediate NEEDS_USER_INPUT for review. Remove bare "not mergeable" or require it with "cannot be cleanly created" / "merge conflicts".
- **Suggested revision**: Address the concern above.


### FINDING_12: **correctness** `python/merge.py:35-38,499-506` — The standalone `"not mergeable"` substring is broader than the merge-time race the fix targets. GitHub can emit that phrase for review-gated or otherwise blocked PRs even when there is no main-advance conflict. On `MERGE_RESULT_ADMIN_FAILED`, that match now returns `MERGE_RESULT_MAIN_ADVANCED` before `gh.pr_review_decision(...)`, so a review-only failure that happens to include `"not mergeable"` in the fallback stderr will skip `MERGE_RESULT_REVIEW_REQUIRED` and enter the ship merge loop (CI pass + not behind → merge again) instead of the prior immediate `NEEDS_USER_INPUT` stall. `python/test_merge.py:519-544` locks in this behavior but does not add a negative case with a realistic review-only `"not mergeable"` diagnostic. **Suggested fix:** Drop bare `"not mergeable"` from `_MERGE_CONFLICT_SIGNALS`, or require it together with `"cannot be cleanly created"` (the reported #4247 plain failure already has both). Keep `"merge conflicts"` and `"cannot be cleanly created"` as standalone signals.
- **Reviewer**: dyn-merge-race-output.txt
- **Concern**: - **correctness** `python/merge.py:35-38,499-506` — The standalone `"not mergeable"` substring is broader than the merge-time race the fix targets. GitHub can emit that phrase for review-gated or otherwise blocked PRs even when there is no main-advance conflict. On `MERGE_RESULT_ADMIN_FAILED`, that match now returns `MERGE_RESULT_MAIN_ADVANCED` before `gh.pr_review_decision(...)`, so a review-only failure that happens to include `"not mergeable"` in the fallback stderr will skip `MERGE_RESULT_REVIEW_REQUIRED` and enter the ship merge loop (CI pass + not behind → merge again) instead of the prior immediate `NEEDS_USER_INPUT` stall. `python/test_merge.py:519-544` locks in this behavior but does not add a negative case with a realistic review-only `"not mergeable"` diagnostic. **Suggested fix:** Drop bare `"not mergeable"` from `_MERGE_CONFLICT_SIGNALS`, or require it together with `"cannot be cleanly created"` (the reported #4247 plain failure already has both). Keep `"merge conflicts"` and `"cannot be cleanly created"` as standalone signals.
- **Suggested revision**: Address the concern above.


