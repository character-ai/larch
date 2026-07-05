## Proposed Design Outline

### Goals
- Fix `_gate_b_apply_start_s` so it finds design plan-review vendor rows labeled `skill="implement"`.
- Ensure the Gate B apply bar is written to the timing ledger and renders in design round Gantts.
- Add a regression test with `skill="implement"` vendor rows to prevent recurrence.

### Non-goals
- Relabeling design plan-review vendor rows from `skill="implement"` to `skill="design"` (not needed; ledger is per-run).
- Changes to the Gantt renderer or round-window derivation (already correct).
- Fixing any `/implement` apply-lane timing (unaffected by this bug).

### Approach sketch
- Drop `cols[3] != "design"` from the `if` guard in `_gate_b_apply_start_s` in `plan_review_loop.py`.
- Add one new test: vendor rows with `skill="implement"` + a gate-b-apply-ready marker; assert `gate-b-apply` row written with correct span.
- Verify existing tests still pass (they write `skill="design"` vendor rows and remain valid).

### Surfaces in scope
- `python/larch/review/plan_review_loop.py` (one-line defect fix)
- `python/tests/review/test_plan_review.py` (new regression test)

### Open questions
- None.
