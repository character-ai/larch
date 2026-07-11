## Decision 1: Terminal outcome for post-merge flush failure after a successful merge
- **Question**: After a PR is admin-merged and the local checkout moves to main, the best-effort post-merge log flush fails and the whole run is reported STALLED. What should the terminal outcome be?
- **Resolution**: Report the ship as SUCCESS (OK/DONE). Do NOT stall. Do NOT emit a warning. Rationale (user): the post-merge log tail can never be committed to the already-merged PR (the PR necessarily merges before the workflow ends), so the log tail is dropped. This is normal and expected and must not cause either a stall or even a warning.
- **Source**: user

## Decision 2: Scope of the fix
- **Question**: Should the fix also cover the stall-recovery / reship (`_resume_plan` checkout-mismatch) path, or focus only on the forward ship-driver path?
- **Resolution**: Forward ship-driver path only (`run_postmerge_phase` in `python/larch/implement/ship_pr.py`). Do NOT modify the stall-recovery / reship (`_resume_plan` checkout-mismatch) guard in `ship_resume.py`. Already-stalled runs (e.g. the #6900 run behind this report) are out of scope.
- **Source**: user

## Hard constraints (derived)
- On the post-merge flush skip after a successful merge (`finalize.postmerge` returned OK), emit NO warning breadcrumb and NO stall; report OK/DONE.
- Keep the flush attempt best-effort (logs still flush when the flush succeeds); only the skip handling changes.
- Surgical scope: `python/larch/implement/ship_pr.py` plus its test (`python/tests/implement/test_ship.py`). Do not touch `ship_resume.py`.
