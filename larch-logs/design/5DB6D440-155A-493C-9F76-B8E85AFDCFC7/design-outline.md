## Proposed Design Outline

### Goals
- Fix 4 code defects: `emit_tally` re-entry guard blocked by non-empty sink (Item 1), dead `annotate-skipped-empty-stdout` branch (Item 2), duplicate security classifier that can drift between design and review paths (Item 3), and `--structured-reviewer-validation` demotion applied after substantive validation passes (Item 8).
- Close 4 test gaps: remove redundant weak annotate test (Item 4), add `review_core_body` session-env integration test (Item 5), add Gate C reentry pool-reset regression test (Item 6), add once-only retry sentinel harness (Item 7).

### Non-goals
- No new features or behavioral changes beyond the named defect fixes.
- No changes to the `/implement` Step 5 validation path; Item 8 is scoped to the `/design` plan-review path only.
- No refactoring of unaffected tally or OOS-filing logic beyond the minimum required by each item.

### Approach sketch
- Item 1: Change the `emit_tally` non-empty sink guard so it skips re-clearing instead of aborting, allowing same-run re-entry after aggregate promotion.
- Item 2: Confirm `design_oos.py` emits only `annotate-failed-empty-stdout`; remove the dead `annotate-skipped-empty-stdout` branch from `design_step5b.py`.
- Item 3: Replace the standalone `_is_security` chain in `plan_review_tally.py` with the shared `voting.is_security_block_text` used by `review_tally.py`.
- Item 8: Gate `--structured-reviewer-validation` demotion in `plan_review_round.py` so it does not fire once substantive validation has passed.
- Items 4-7: Add targeted tests (Python unit/integration for Items 4, 5, 7; shell harness or Python for Item 6 based on `design-step3-entry.sh` test conventions).

### Surfaces in scope
- `python/larch/review/review_tally.py`
- `python/larch/review/plan_review_tally.py`
- `python/larch/review/plan_review_round.py`
- `python/larch/design/design_step5b.py`
- `python/larch/design/design_oos.py`
- `python/tests/design/test_design_oos.py`
- `python/tests/review/test_review_tally.py`
- Shell harness (if Items 6/7 require it) in `skills/design/scripts/`

### Open questions
- None.
