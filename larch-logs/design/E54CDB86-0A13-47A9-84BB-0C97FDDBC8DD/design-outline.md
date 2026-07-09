## Proposed Design Outline

### Goals
- Run every Cursor **reviewer** lane on `auto` (not `composer-2.5`) across `/design` plan review and `/implement` code review.
- Remove the one-off `plan-fidelity-auto` (#6553) additive lane and its per-slot plumbing.
- Keep `BUCKETS_cursor_by_model` cost attribution intact so before/after comparison stays possible.

### Non-goals
- Do NOT change `CURSOR_DEFAULT_MODEL = "composer-2.5"`.
- Do NOT touch voter slots (`review.voters`, `design.plan_voters`) or Cursor coder/implementer/fixer roles.
- Do NOT remove the `plan-fidelity-forced` low-coverage safeguard (keep it; it already runs on `auto`).

### Approach sketch
- Set `cursor_model=CURSOR_AUTO_MODEL` as a per-slot override on the Cursor reviewer `SlotDefault`s in `config.py` (code-review: correctness/edge-cases/testing; plan-review: arch/innovation/pragmatic/requirements).
- Propagate `cursor_model` (+ matching `resolved_model`) into plan-review manifest rows in `plan_review_panel.py` (currently dropped), and set `resolved_model` on code-review rows so display attribution matches the launched model.
- Set dynamic Cursor lanes to `auto` in both panels' dynamic-slot synthesis.
- Drop the `plan-fidelity-auto` slot + its `is_additive_plan_fidelity` special-casing; repoint the `plan-fidelity-forced` codex-fallback archetype reference off the deleted name.

### Surfaces in scope
- `python/larch/core/config.py` — Cursor reviewer `SlotDefault`s (both panels); remove `plan-fidelity-auto`.
- `python/larch/review/review_dispatch_panel.py` — code-review rows, additive special-case, forced-lane reference.
- `python/larch/review/plan_review_panel.py` — plan-review static + dynamic Cursor rows.
- `python/larch/review/review_tally.py`, `python/larch/report/timing.py` — orphaned `plan-fidelity-auto` references.
- Tests: `test_external_role_defaults.py`, `test_external_dispatch.py`, `test_review_pipeline.py` (+ targeted new coverage).

### Open questions
- None. (`plan-fidelity-forced` fate resolved in Round 1: keep, stays on `auto`.)
