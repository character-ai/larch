## Proposed Design Outline

### Goals
- Stop `/implement --merge` from reshipping and filing a spurious `[Bug]` when the post-merge log flush is skipped after a confirmed successful merge.
- Report such a run as the successful merge it is (`IMPLEMENT_NORMALIZED_OUTCOME=merged`), not `stalled`.

### Non-goals
- Do not change the pre-push `preterminal-outcome` reship path (`STALL_STEP=pr-create-guideline-outcome-refresh`, `PHASE=stalled`); that intended behavior stays.
- Do not change `retry_policy` caps or what the post-merge log flush itself commits (NEVER #16 policy stands).
- No broad refactor of stall classification or outcome normalization.

### Approach sketch
- Root-cause fix in `python/larch/implement/ship_pr.py` `run_postmerge_phase`: a skipped best-effort post-merge log flush after a confirmed merge becomes a non-terminal warning, not `Outcome.STALLED`; the run finalizes `OK`.
- Defense-in-depth guard in `python/larch/state/_classify.py` `classify()`: before `_classify_text()`, when `phase == "postmerge"` and merged `MERGE_RESULT` ∈ `_TERMINAL_MERGE_RESULTS`, classify as `operator-action` / `none` / `postmerge-flush-expected` (never `step8-shippr`).
- Keep the existing "post-merge flush skipped" warning breadcrumb.

### Surfaces in scope
- `python/larch/implement/ship_pr.py` — postmerge phase state writes
- `python/larch/state/_classify.py` — `classify()` postmerge guard (+ resume-hint / pattern-allowlist plumbing)
- Tests: `python/tests/implement/test_ship.py`, `python/tests/state/test_stall_recovery.py`

### Open questions
- None. Ship fix is scoped to intentional skips after a confirmed merge; classifier guard is phase-gated so the pre-push path is unaffected.
