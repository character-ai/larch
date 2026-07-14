## Proposed Design Outline

### Goals
- Implement the metadata-preserving `--write` mode with `--reason TEXT`, history appending on metric increase, and UTC date stamping in `lint_complexity_baseline.py`
- Add the repeat-bump gate in check mode (second increase within 14 days = fail, with failure message and three exits) plus active-override listing
- Add `lint_complexity_debt.py` with `--report`, register it in `cli.py`, extend tests, and update `docs/linting.md` + `Makefile`

### Non-goals
- No changes to complexity thresholds (C901, PLR0912, etc.) or `ruff.toml`
- `--report` not wired into CI or `/larch-size` (explicit follow-up in issue)
- No schema changes to other `python/*-baseline.json` files

### Approach sketch
- Rewrite `_run_write` to load existing baseline, merge live records (preserve metadata, append history on increase, stamp UTC date, require `--reason` on new entry or increase), write merged result
- Add gate check in `_run_check`: for each record whose history shows 2+ increases within 14 days and no `operator_override`, emit failure message with three exits; always list active overrides at end
- New `lint_complexity_debt.py`: load baseline, print five sections (entry count, age buckets, top-10 by metric, symbols with 2+ bumps in 30 days, active overrides)
- Register `("lint", "complexity-debt")` in `cli.py`; update `Makefile` comment on `regen-complexity-baseline` target and add `make lint-complexity-debt` check

### Surfaces in scope
- `python/larch/lint/lint_complexity_baseline.py`
- `python/larch/lint/lint_complexity_debt.py` (new)
- `python/larch/cli.py`
- `python/tests/lint/test_lint_complexity_baseline.py`
- `docs/linting.md`
- `Makefile`

### Open questions
- Age bucket boundaries for debt report (planning: <14 days, 14-90 days, >90 days); no user decision needed, operator confirmed via issue
