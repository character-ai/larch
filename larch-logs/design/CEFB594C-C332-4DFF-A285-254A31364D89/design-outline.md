## Proposed Design Outline

### Goals
- After a successful admin-merge, a skipped best-effort post-merge log flush reports the ship as OK/DONE, never STALLED.
- That skip emits no warning breadcrumb: a dropped post-merge log tail is normal and expected.

### Non-goals
- No change to the stall-recovery / reship `checkout-mismatch` guard (`_resume_plan` in `ship_resume.py`).
- No change to the flush attempt, its skip-reason machinery, or the pre-merge (pre-push) flush that commits the run log.
- No fix for runs already stalled at `postmerge-flush` (e.g. the #6900 run behind this report).

### Approach sketch
- In `run_postmerge_phase` (`python/larch/implement/ship_pr.py`), when `finalize.postmerge` returned OK, treat a `finalize_postmerge_logs` skip as a non-event.
- Drop the warning breadcrumb, the STALLED terminal-finalize write, and the STALLED ship-state write on that skip.
- Keep the flush call best-effort (logs still flush when it succeeds); fall through to the existing DONE/OK return on skip.

### Surfaces in scope
- `python/larch/implement/ship_pr.py` (`run_postmerge_phase`)
- `python/tests/implement/test_ship.py` (post-merge flush skip test)

### Open questions
- None. I-Flush-1 tension reconciled: the pre-merge (pre-push) flush that commits the run log is untouched; the post-merge tail is structurally uncommittable (the PR merges before the workflow ends), and the operator who authored the invariant explicitly chose silent success in Round 1.
