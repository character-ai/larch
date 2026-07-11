### FINDING_1: Documentation records Composer 2.5 as the Cursor default
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `docs/review-agents.md:99-109` documents Composer 2.5 defaults rather than the former per-slot `auto` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_2: Token-cost tests reflect removal of the Cursor `auto` bucket
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `python/tests/report/test_report_tokens_cost.py:214-216` verifies that the `("cursor", "auto")` row is absent and that `rate_row("cursor", model="auto")` falls back to Composer rates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_3: Review-and-fix tests cover Composer defaults and Cursor model-resolution failure
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `python/tests/review/test_review_and_fix.py:2544-2590` covers the default `--model composer-2.5` launch and model-resolution failure behavior for `_run_coder_cursor`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_4: Cursor launch paths resolve the default model when no override is supplied
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `python/larch/agents/_ci_launcher.py:367-371` and `python/larch/review/coder_runner.py:215-218` both use `resolve_model_args("cursor", with_effort=True)` when no explicit model override is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_5: Panel manifests and review launch use consistent Cursor model resolution
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `review_dispatch_panel.py` and `plan_review_panel.py` set `resolved_model` through `_resolved_model_for_row("cursor")`, matching the launch path in `_review_launcher.py:1127-1128`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_6: Legacy Cursor `auto` buckets are attributed to Composer pricing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `cursor_argv_from_buckets()` in `report_tokens_cost.py:342-348` folds legacy `model="auto"` buckets into the Composer lane, with coverage in `test_report_tokens_cost.py:753-780`; runtime routing, manifest attribution, two-lane cost emission, and legacy repricing are consistent with the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
