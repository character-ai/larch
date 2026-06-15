## Proposed Design Outline

### Goals
- Add focused `python/checks.py` direct-target rows for `skills/implement/SKILL.md` and all `python/design_*.py` modules plus `design_log_ship.py`.
- Add the two missing harnesses (`test-design-step1d5.sh`, `test-design-log-ship` Make target) and the `AUTOFIX_STATUS=ok` harness case.
- Fix the dynamic-archetype cap export gap, update upgrade-larch cleanup, add the OOS disposition checkpoint, expose `/bug` in all consumer catalogs, and document the brainstorm sink pairing.

### Non-goals
- No refactors of existing checks.py structure beyond inserting new rows.
- No new test frameworks or cross-cutting infrastructure.
- No changes to `/design` or `/implement` orchestration flow.
- No dedicated focused target for `python/design_legacy.py` (no test file exists).

### Approach sketch
- Insert rows in `python/checks.py` before the broad `skills/*/SKILL.md` and `python/*.py` fallback rows.
- Create `skills/design/scripts/test-design-step1d5.sh` covering collect-mode logging, idempotency, and dirty-tree merge.
- Add the wrapper-owned `AUTOFIX_STATUS=ok` Warnings row to `design-step-validator-autofix.sh` and test it.
- Add `export LARCH_DYNAMIC_ARCHETYPES_MAX=...` in `step-5-review.sh` before `exec`, and add a `test_step5_*` assertion in `test_review_and_fix.py`.
- Extend `python/upgrade_larch.py` cleanup list and `python/oos_filer.py` checkpoint call; update docs/config for `/bug`.

### Surfaces in scope
- `python/checks.py`, `python/test_checks.py`
- `Makefile` (new targets + shard wiring)
- `skills/design/scripts/design-step-validator-autofix.sh`, `test-design-step-validator-autofix.sh`
- `skills/design/scripts/test-design-step1d5.sh` (new)
- `skills/design/references/brainstorm.md`
- `skills/implement/scripts/step-5-review.sh`, `python/test_review_and_fix.py`
- `python/upgrade_larch.py`, `python/test_upgrade_larch.py`
- `python/oos_filer.py`, `python/test_oos_filer.py`
- `skills/implement/references/oos-pipeline.md`
- `README.md`, `docs/skills.md`, `docs/configuration-and-permissions.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

### Open questions
- None.
