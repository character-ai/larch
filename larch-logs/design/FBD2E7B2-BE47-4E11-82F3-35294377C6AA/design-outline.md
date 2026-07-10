## Proposed Design Outline

### Goals
- Replace `_RUN_EXTERNAL_TIMEOUT = 300` with `config.FIXER_LANE_TIMEOUT_SEC = 1800` for each external tier.
- Advance to the next tier when a tier exits 0 but makes no file delta.
- Route all repair-loop exhaustion outcomes to stall, never to `main-agent-edit`.

### Non-goals
- No changes to Step 8 / ship-pr-ci-* CI orchestration.
- No changes to fast-fail structural cases (complexity-baseline, structural-ruff remain fail-closed).
- No new tier roles or waterfall membership changes.

### Approach sketch
- In `_run_lint_fix_impl`: use `config.FIXER_LANE_TIMEOUT_SEC` for `--timeout`, `fixer_lane_budget_sec("implement.lint_fix_coder")` as total budget, `next_untried_tier()` for tier selection.
- Add per-tier delta check: after exit 0, snapshot HEAD and tracked paths; if no delta, add tier to `attempted_tiers` and continue to next.
- In `_repair_loop_action`: remove the `_populate_no_changes_stale_ledger` / `_populate_exhausted_ledger` routing gates; route all non-`main-agent-required` exhaustion to stall.
- Update `checks-repair-loop.md` to reflect that exhaustion on step3/5/6 now routes to stall.

### Surfaces in scope
- `python/larch/implement/checks_lint_fix.py`
- `skills/implement/references/checks-repair-loop.md`
- `skills/implement/SKILL.md` (checks-repair portions)
- `python/tests/implement/test_checks.py`
- `scripts/test-implement-structure.sh`
- `scripts/test-implement-fence-shape.sh`
- `docs/configuration-and-permissions.md`

### Open questions
- None.
