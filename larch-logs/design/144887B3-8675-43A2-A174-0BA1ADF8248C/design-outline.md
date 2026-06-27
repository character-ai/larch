## Proposed Design Outline

### Goals
- Reduce `step2b_drafter_main` complexity to its pre-#5630 levels (C901 ≤28, PLR0911 ≤11, PLR0912 ≤30, PLR0915 ≤123) through behavior-preserving extraction.
- Regenerate `python/complexity-baseline.json` so the four bumped entries drop back down, undoing the ratchet.
- Keep `make py-lint-checks-fast` and the design test suite green.

### Non-goals
- No change to drafter runtime behavior: `DRAFTER_NEXT_ACTION` values, exit codes, printed rows, sentinel/file writes, and pause + postplan semantics stay identical.
- No refactor of sibling over-baseline functions (`route_main`, `failure_report_core`, `step0_route_main`, etc.).
- No change to the complexity lint config or thresholds.

### Approach sketch
- Extract cohesive blocks of `step2b_drafter_main` in `design_lifecycle.py` into private one-call-site helpers: the output-artifact cleanup loop, the drafter launch-command build + subprocess run, the dirty-tree detection, and the structural-success → postplan dispatch.
- Keep each new helper under the ruff complexity thresholds so it needs no (or a minimal) baseline entry.
- Regenerate the baseline mechanically via `make regen-complexity-baseline` (= `lint complexity-baseline --write`), not by hand-editing JSON (issue #5041).
- Verify with `make py-lint-checks-fast` and `pytest python/test_design_lifecycle.py` plus the design-structure / drafter harnesses.

### Surfaces in scope
- `python/larch/design/design_lifecycle.py` — `step2b_drafter_main` plus new private helpers.
- `python/complexity-baseline.json` — regenerated (four entries lowered; minimal new helper entries only if unavoidable).
- `python/test_design_lifecycle.py` — confirm coverage; add a focused test only if a new seam needs it.

### Open questions
- None.
