### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:590-591
- **Concern**: Pre-merge reconciliation must require a successful correction push before merge. Scenario: `flush_logs_pre` can commit the corrected `final-summary.md` locally, but `push.push_branch` returns `status="failed"` after retries rather than raising; if the helper then continues to `merge.merge_pr`, GitHub can merge the old remote head that still contains `Outcome: stalled`.
- **Proposed resolution**: Treat push exceptions or any push result other than `pushed` as a terminal stalled recovery result before calling `merge.merge_pr`; reuse the existing `_post_ensure_flush_and_push` failure pattern.



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:338-354
- **Concern**: PR-created recovery returns before the planned reconciliation hook. Scenario: The plan adds the guarded strict flush only immediately before merge.merge_pr, but the non-merge or draft success branch returns OK after PR creation without any committing flush; a run that previously committed final-summary.md as stalled can recover to pr-created/pr-created-draft and still leave the git-tracked summary stalled.
- **Proposed resolution**: Call the same stale-heading gated reconciliation helper on the early PR-created/draft success path before returning; keep the existing guard so fresh runs and active failures do not reflush, and fail closed on flush or push failure instead of claiming success.



### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:338-353
- **Concern**: Pre-merge reconciliation still misses successful PR-created early returns after the prior accepted recovery-success gap. Scenario: The plan places the committing reconciliation immediately before merge.merge_pr, but recovered runs that create a non-merge or draft PR return OK from this branch without entering the merge loop, so a previously committed final-summary.md can remain Outcome: stalled despite shipping as pr-created or pr-created-draft
- **Proposed resolution**: Invoke the same guarded reconciliation before this successful PR-created or draft return, or move the helper to a shared post-ensure point before branches that can return success, keeping the existing committed-stalled-summary and clean normalized-outcome gates



