## Decision 1: Historical run-log backfill
- **Question**: Should the fix backfill the ~1 week of committed /implement run logs that lost the `Step 2 — implementation` mark, or fix forward only?
- **Resolution**: Fix forward only. Restore the mark so new runs are attributed correctly; leave committed `token-report.json` / `timing-report.json` files unchanged. Step 2 spans cannot be reliably reconstructed after the fact.
- **Source**: user

## Decision 2: Fix breadth beyond restoring the mark
- **Question**: How far should the change reach beyond root-causing and restoring the dropped Step 2 mark on the live dispatch path?
- **Resolution**: Restore the mark on every implementer launch route AND harden the other `.codex.per_step` consumers so they do not silently misattribute coder cost. Add a regression guard so the live path cannot silently drop the mark again. Restoring the mark is necessary but not sufficient; consumers are made robust rather than left to depend solely on the restored mark.
- **Source**: user

## Hard constraints (from codebase, not asked)
- Keep the mark label prefix `Step 2 ` intact: `python/analysis/codex_role_costs.py` keys the coder split on `CODER_STEP_PREFIX = "Step 2 "`, and `python/larch/report/tokens.py` `_per_step_json` labels spans from `mark["step"]`. The canonical label is `Step 2 — implementation`.
- Preserve the existing dispatcher mark contract asserted by `python/tests/implement/test_implement_dispatch.py` (both `token mark` and `timing mark` for `Step 2 — implementation`, best-effort).
- Marks stay best-effort (must never abort dispatch), but must not silently no-op on the live path.
