### OOS_1: [OUT_OF_SCOPE] `resume.start == "done"` / `"merged"` skips committed-summary reconciliation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `python/larch/implement/ship.py:272-300` — `resume.start == "done"` and `resume.start == "merged"` return success without calling `reconcile_committed_stalled_summary_if_recovered`, and post-merge log commits are forbidden (#2182). A run that merged in a prior session while the git-tracked summary still says `stalled` will not be repaired on a later resume. **Why OOS:** the plan scoped reconciliation to the early PR-created and pre-merge call sites and explicitly excluded historical log migration; this is a known residual limitation for already-merged reruns, not a regression in the new paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `force-merged-externally` not accepted as recovered outcome for reconciliation
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-recovery-logs
- **Severity**: important
- **Concern**: `_live_recovered_outcome` accepts only `pr-created`, `pr-created-draft`, and `merged`, so a resume where `ship-pr-state.sh` already carries `MERGE_RESULT=already_merged` (normalized to `force-merged-externally`) skips reconciliation even if the committed summary still says `stalled`. **Why OOS:** this needs inconsistent/partial state (merge result recorded while the summary was never corrected and the PR is still treated as open-pr); the plan listed the three allowed outcomes explicitly, and the normal first-recovery path sets `MERGE_RESULT` only after reconciliation runs. For dyn-dyn-recovery-logs: narrow residual gap for external-merge resumes where the plan omitted that label.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-recovery-logs: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `_read_state` duplicates wire-file parsing in `larch.state._tokens`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/implement/ship_pr.py:53-61` — New `_read_state` duplicates wire-file parsing already in `larch.state._tokens._read_state_file` (quote stripping differs). **Why OOS:** maintainability only; no demonstrated behavioral divergence on paths this feature produces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Missing test for strict flush skip during reconciliation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan’s failure-mode table calls out strict flush skip during reconciliation (`refresh.skipped` → `Outcome.STALLED`), and `reconcile_committed_stalled_summary_if_recovered` implements it at `ship_pr.py:132-147`, but there is no test mirroring the push-failure cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a ship test that monkeypatches the second `flush_logs_pre` to return `RefreshSkip(skipped=True, ...)` and asserts `Outcome.STALLED`, no merge, and a `run-log reconciliation flush skipped` detail.

### OOS_5: [OUT_OF_SCOPE] Missing test for fail-closed `strict_final_report` manifest-only path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `_reconcile_stalled_summary_backstop` raises `ShipError` under `strict_final_report=True` when manifest-only reconciliation is needed but cannot complete (`run_log_flush.py:407-409`), but no test exercises that fail-closed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a flush test with `status=done` + stalled heading/outcome where `reconcile_stalled_summary_from_manifest` is forced to return `False`/`still_needed`, and assert `flush_logs_pre(..., strict_final_report=True)` raises.

### OOS_6: [OUT_OF_SCOPE] Missing test for non-merge early `pr-created` success path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan explicitly lists a non-merge early PR-created success path (`merge=false`, no merge loop); only the draft variant is covered (`test_recovered_draft_pr_reconciles_stalled_summary_before_ok`). Both use `_complete_pr_created_without_merge`, so regression risk is low.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional duplicate of the draft test with `MERGE=false` and assert `— pr-created` before OK return.
