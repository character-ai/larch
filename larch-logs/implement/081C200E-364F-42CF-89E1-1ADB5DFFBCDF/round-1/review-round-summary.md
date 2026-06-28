# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_2: Chronic-surface completeness test parametrizes ghost review_phase_detail path; canonical row under-covered
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-check-routing
- **Severity**: important
- **Concern**: `test_direct_targets_chronic_surface_full_union_sets` asserts routing for non-existent `python/review_phase_detail.py` instead of canonical `python/larch/report/review_phase_detail.py`. The dedicated rule row at `checks.py:588` covers the real module, but dropping or misrouting that row would not fail CI because the parametrized case exercises a ghost path that never appears in real `git diff` output. Codex also notes the canonical row omits `py-lint` (`wants_py_lint=False`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Replace the ghost path with python/larch/report/review_phase_detail.py expecting {py-test}; optionally keep python/test_review_phase_detail.py for catch-all coverage.
  - From codex-specialist-correctness: Set wants_py_lint=True for the real nested row and assert python/larch/report/review_phase_detail.py directly in the completeness test
  - From cursor-specialist-edge-cases: Parametrize python/larch/report/review_phase_detail.py with expected {py-test}; drop the dead shim pattern from _DIRECT_TARGET_RULES if unused.
  - From dyn-dyn-check-routing: Replace the parametrized case with `python/larch/report/review_phase_detail.py` and expected `{"py-test"}` (matching the other canonical report rows), and drop or demote the dead shim path from the completeness table unless a top-level shim is reintroduced.


