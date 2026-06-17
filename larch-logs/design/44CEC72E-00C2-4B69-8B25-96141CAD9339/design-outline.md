## Proposed Design Outline

### Goals
- Port the Step-3 plan-review loop bodies into native Python: loop mechanics, panel/voter dispatch, MainAgent vote, Gate-B dedup, continuation, re-entry, Step 3b diagram, Step 4 tail.
- Remove `_run_legacy`, `_materialize_legacy_root`, the `_LEGACY_ASSETS` gzip blobs, and `import gzip` from `python/plan_review.py`.
- Preserve every orchestrator-visible contract: `STEP3_REVIEW_LOOP_STATUS` envelope, exit codes, result-env files, pause/resume marker bytes, `docs/issue-anchored-plan.md` payload.

### Non-goals
- Do not re-port `tally` (already in-process in `python/plan_review_tally.py`, #4433).
- Do not change Step 3 panel composition, voting thresholds, or any other /design step.
- Do not delete launcher-invoked wrappers; they stay as thin bash.

### Approach sketch
- House loop mechanics in `python/plan_review.py`; move panel and voter dispatch into `python/plan_review_panel.py`; keep `cli.py plan-review` verbs.
- Replace each `_run_legacy(...)` call with a direct in-process function, then delete the body it referenced.
- Shrink launcher-invoked Step-3 `.sh` files to thin wrappers that call the new verbs; delete pure internal bodies and retired on-disk bash with no stubs.
- Apply low-risk fixes and dedup where safe; keep parity-critical bytes intact.

### Surfaces in scope
- `python/plan_review.py`, `python/plan_review_panel.py`, `python/cli.py`.
- `python/test_plan_review.py`, `python/test_plan_review_panel.py`, `python/migration_lint.py`.
- `skills/design/scripts/` Step-3 `.sh` wrappers, internal bodies, `test-*.sh` + `.md` siblings.
- `skills/design/SKILL.md`, `skills/design/references/*.md`, `Makefile`, CI, `python/migrated-scripts.tsv`.

### Open questions
- None.
