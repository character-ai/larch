## Proposed Design Outline

### Goals
- Stop `--merge` (admin-fallback-enabled) runs from bailing to review-required while CI is still pending; wait for CI, then let the `--admin` fallback merge.
- Preserve the correct early review-required bail for `--no-admin-fallback` runs (review genuinely blocks; no bypass).
- Correct the misleading hardcoded `mergeStateStatus=BLOCKED` bail detail to report the real observed state.

### Non-goals
- No change to `MERGE_PR_INITIAL_UNKNOWN_RETRIES` or any retry/wait constant.
- No new CI-wait cap; the existing `_CiNotReadyGuard` / `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD` already bounds the wait.
- No change to `merge.py`'s UNKNOWN→CI_NOT_READY ordering or the `_attempt_merge` admin fallback itself.

### Approach sketch
- In `ship.py` CI_NOT_READY branch (~747-778), gate the `REVIEW_REQUIRED`→terminal conversion on `working.no_admin_fallback`; otherwise fall through to `_handle_merge_ci_not_ready` + `continue` (wait/re-loop) regardless of `reviewDecision`.
- Only query `gh.pr_review_decision` when it can change routing (i.e. when `no_admin_fallback`), avoiding a wasted per-iteration `gh` call on the default `--merge` path.
- Replace the hardcoded `mergeStateStatus=BLOCKED` bail detail with the real state (or drop the false assertion) so the operator message is truthful.
- Regression test in `test_ship.py`: `no_admin_fallback=False` + `CI_NOT_READY` + `REVIEW_REQUIRED` → loop waits/re-loops (no `NEEDS_USER_REVIEW_REQUIRED`); keep the existing `no_admin_fallback=True` bail asserted.

### Surfaces in scope
- `python/larch/implement/ship.py` (~747-762) — primary fix site.
- `python/tests/implement/test_ship.py` — regression coverage.
- `python/larch/implement/ship_merge.py` — read-only context (`_handle_merge_ci_not_ready`, guard).

### Open questions
- None. Cap question resolved (existing guard suffices); detail-fix scope resolved (included, minimal).
