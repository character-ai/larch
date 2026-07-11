## Decision 1: Fix locus / scope
- **Question**: The issue scopes the fix to the stall classifier, but the classifier-only fix cannot stop the spurious [Bug] filing because `ship_pr.py` `run_postmerge_phase` marks the run `STALLED` (nonzero EXIT_CODE + STALL_TRACKING=true) before classification runs. Where should the fix land?
- **Resolution**: **Ship driver + classifier guard (layered / defense-in-depth).** (1) Root-cause fix in `python/larch/implement/ship_pr.py`: a *skipped* (intentional) post-merge log flush after a confirmed successful merge must be a non-terminal warning, NOT `Outcome.STALLED`. (2) Defense-in-depth guard in `python/larch/state/_classify.py` `classify()`: before `_classify_text()`, when `phase == "postmerge"` and the merged state shows `MERGE_RESULT` in `_TERMINAL_MERGE_RESULTS`, return `("operator-action", "none", "postmerge-flush-expected")` so a stray `preterminal-outcome` string can never route to a reship again.
- **Source**: user

## Decision 2: Done criteria
- **Question**: What does "fixed" mean for this bug?
- **Resolution**: A `/implement --merge` run whose PR merges and whose post-merge log flush is skipped (reason `preterminal-outcome`) must: NOT attempt a reship, NOT file a spurious `[Bug]` issue, and be reported as the successful merge it was (`IMPLEMENT_NORMALIZED_OUTCOME=merged`). The existing warning breadcrumb that post-merge log cleanup was skipped is preserved (operator-visible, non-terminal).
- **Source**: user (implied by fix-locus choice) + issue "Expected behavior"

## Decision 3: Other `preterminal-outcome` emission sites (issue Open Question 2)
- **Question**: Does the same over-match occur on any other expected `preterminal-outcome` emission site besides post-merge flush?
- **Resolution**: No. The only emitter of `config.REFRESH_SKIP_PRETERMINAL_OUTCOME` is `_preterminal_outcome_refresh_skip()` (`python/larch/report/run_log_flush.py:710`), consumed by `flush_logs_pre` (pre-push, the *intended* reship trigger) and `finalize_postmerge_logs` (post-merge, the bug). No third site. The classifier guard is phase-scoped (`postmerge`), so it does not touch the pre-push path.
- **Source**: codebase

## Decision 4: Hard constraint — preserve pre-push reship behavior
- **Question**: What must not break?
- **Resolution**: The pre-push `_ship_refresh_preterminal_stall` path must keep classifying `PHASE=stalled` / `STALL_STEP=pr-create-guideline-outcome-refresh` with a `preterminal-outcome` reason as `transient-infra` / `step8-shippr` (existing `test_classify_preterminal_ship_refresh_stall`, `test_classify_refresh_stall_remedy_wins_over_lint_substring`). Both the ship-driver fix and the classifier guard are gated on `phase == "postmerge"` + confirmed merge, so the pre-push phase is unaffected.
- **Source**: codebase
