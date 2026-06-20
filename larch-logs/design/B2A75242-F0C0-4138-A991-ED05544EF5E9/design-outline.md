## Proposed Design Outline

### Goals
- Fix all 7 OOS items on `/design` Step 5c publish/final-summary and plan-review/panel/timeout.
- Stop the Step 5c publish fd1 leak and cover the failure-path / cleanup-eligibility matrix with tests.
- Make dynamic-slot render failures loud (Item 6); stop round-2+ plan review from re-raising already-applied findings (Item 5).

### Non-goals
- Do not revert the 60s probe timeout. Item 7 keeps 60s; document the #4801 rationale only.
- Do not re-implement behavior already closed in current code (Item 2 session-id rejection, Item 3 render-failure gating). Add tests and residual hardening only.
- Do not change Step 5c public contracts: FD3 grammar, `LARCH_FINAL_SUMMARY_*` markers, publish exit codes {0,1,3,4}, terminal sentinels.

### Approach sketch
- Item 1: redirect the `named-block write` child stdout in `design_publish.py` so it stops leaking into the Step 5c contract-stream capture.
- Items 2-4: add Step 5c failure-path + cleanup-eligibility tests in `test_design_lifecycle.py`; close any residual stale on-disk `final-summary.md` emission on success paths.
- Item 5: dedup plan-review findings across rounds in `plan_review.py` so applied round-1 findings do not reappear in round-2+.
- Item 6: emit a WARNING (and execution-issue) when a dynamic slot's `render plan-review` exits non-zero, instead of silently using the plan-blind one-line fallback.
- Item 7: keep the 60s default; add a grounded code comment recording the #4801 reason; no behavior change.

### Surfaces in scope
- `python/design_publish.py` (overlap-sensitive with in-flight #4865; edit merge-order-agnostically), `python/design_lifecycle.py`.
- `python/plan_review.py`, `python/plan_review_panel.py`, `python/agents.py` (comment only).
- Tests: `python/test_design_lifecycle.py`, `python/test_plan_review.py`, `python/test_plan_review_panel.py`.

### Open questions
- Item 3: can a stale on-disk `final-summary.md` from an earlier step still surface on a Step 5c success path? Resolve by code inspection at drafting.
- Item 5: the second of the "two related causes" was truncated at the OOS cap. Recover the full failure mode from `plan_review.py` round handling at drafting.
