### OOS_1: [OUT_OF_SCOPE] larch-logs flush commit excluded from review scope
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `c001fc63a` — chore(larch-logs): flush is out of review scope per instructions. The branch otherwise implements the plan: shared PLR0911 consolidation guidance in `_compose_prompt`, a narrow `PLR0911 (new)` carve-out in `_is_complexity_baseline_regression_log`, preventive implementer checklist text, harness invariants, and regression tests for the carve-out and prompt content. Metric-growth fast-fail still runs first; mixed `PLR0911 (new)` + metric regression is tested; `PLR0912 (new)` fast-fail is unchanged.

### OOS_2: [OUT_OF_SCOPE] Log tail truncation may miss earlier `(new)` regressions
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_is_complexity_baseline_regression_log` only inspects the last 60KB of the checks log (pre-existing `_PROMPT_TAIL_BYTES` behavior). With the new carve-out, a tail that shows only `PLR0911 (new)` plus the complexity-baseline command could route to an external fixer even if an earlier truncated-away section contained another `(new)` regression; old code would have fast-failed. Unlikely for typical small complexity-baseline output, and re-checks would still surface the other regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only if this becomes observed in practice, consider scanning the full log for fast-fail decisions or recording regression lines in a bounded header section.

### OOS_3: [OUT_OF_SCOPE] Missing test for `PLR0911 (new)` plus another `(new)` fast-fail
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: No explicit test that `PLR0911 (new)` plus another `(new)` code (e.g. `PLR0912 (new)`) in the same log still fast-fails. Plan edge cases describe this case; the mixed test only pairs `PLR0911 (new)` with `PLR0913` metric. The `any(code != "PLR0911")` branch is logically correct and mixed-with-metric is covered, but CI would not catch a future regression that exempts all `PLR0911`-prefixed lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a small unit or integration test mirroring `test_run_lint_fix_complexity_baseline_plr0911_new_with_metric_fast_fail` for the two-`(new)` case.
  - From cursor-specialist-testing: Add a fixture with both `(new)` lines and assert `_assert_complexity_fast_fail`.

### OOS_4: [OUT_OF_SCOPE] Missing test for `PLR0911` metric growth fast-fail
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: No explicit or integration test that `PLR0911 metric N > baseline M` still fast-fails. The plan’s failure-modes section flags metric-growth over-carve-out as a risk, but coverage relies on the existing `PLR0913` metric test as a proxy. Current code checks metrics before the `(new)` carve-out, and reordering that block would also break the `PLR0913` test, so this is a latent guardrail gap rather than a shipped defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optional one-liner regression line swap to pin PLR0911 metric growth if you want symmetry with the carve-out target code.
  - From cursor-specialist-testing: Add `test_run_lint_fix_complexity_baseline_plr0911_metric_growth_fast_fail` mirroring the `PLR0913` fixture with a `PLR0911 metric` line.

### OOS_5: [OUT_OF_SCOPE] No direct unit test on `_is_complexity_baseline_regression_log`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no direct unit test on `_is_complexity_baseline_regression_log`; coverage is only through `run_lint_fix` integration tests. That matches existing style for this helper, but a small parametrized unit test would make carve-out edge cases cheaper to debug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `@pytest.mark.parametrize` cases for the helper returning `True`/`False` on synthetic log strings.

---

**Merge notes (diagnostic):** Input `FINDING_1` (`a33f1c7aa`) restated the commit title with boilerplate “Address the concern above” and no distinct behavioral risk; it was subsumed rather than emitted as its own block. `cursor-specialist-edge-cases` appears in FINDING_1–4; `cursor-specialist-testing` appears only in `[OUT_OF_SCOPE]` blocks FINDING_3–5.

