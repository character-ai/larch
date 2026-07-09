## Proposed Design Outline

### Goals
- Clear `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` in `_step3_clear_downstream_sentinels()` so re-entry and auto-continuation take the fresh-launch path.
- Add regression tests asserting both result envs are absent after `--direct-review-entry` and `--auto-continuation-entry`.

### Non-goals
- Defense-in-depth plan fingerprinting in `review_provenance()`.
- Changes to the Bash launchers (`design-step3-review.sh`, `design-step3b-tail.sh`) beyond the Python fix.
- Any other state the launchers read (registry, live process check).

### Approach sketch
- Add two `unlink(missing_ok=True)` calls inside `_step3_clear_downstream_sentinels()` in `python/larch/review/plan_review_loop.py`.
- Extend `_seed_step3_downstream()` in `python/tests/review/test_plan_review.py` to create both result envs.
- Assert both are absent after `--direct-review-entry` and after `--auto-continuation-entry` in the existing test functions.

### Surfaces in scope
- `python/larch/review/plan_review_loop.py` — `_step3_clear_downstream_sentinels()`
- `python/tests/review/test_plan_review.py` — `_seed_step3_downstream`, two existing test functions

### Open questions
- None.
