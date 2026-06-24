## Proposed Design Outline

### Goals
- Emit `NEXT_ACTION=skip-pipeline|file-issues` and `OOS_SKIP_BREADCRUMB=...` from `step5b_prepare_main` so SKILL.md Step 5b collapses from a 5-way parse to a single branch.
- Emit `SETTLE_NEXT_ACTION=<site-keyed-value>` from `design-step35-settle.sh` so the orchestrator branches on one key instead of cross-referencing rc × site.
- Shrink `settle-rc-dispatch.md` to a fallback reference; update SKILL.md Step 5b and Step 3.5 prose.

### Non-goals
- Do not migrate `design-step35-settle.sh` to Python (it stays Bash; only adds `printf` lines at each exit arm).
- Do not move the `/larch:issue` call or the annotate step out of the SKILL.md orchestrator.
- No behavior change — every existing path retains the same outcome.

### Approach sketch
- In `design_lifecycle.py` `step5b_prepare_main`: after status is determined, emit `NEXT_ACTION=skip-pipeline` (all skip-* cases) or `NEXT_ACTION=file-issues` (ready), and for skip cases emit `OOS_SKIP_BREADCRUMB=⏩ 5b: oos filing — <reason>`.
- In `design-step35-settle.sh`: before each final `exit`, printf `SETTLE_NEXT_ACTION=<value>` keyed on `($POSTPLAN_MACHINE_RC, $SITE)`; values like `gate-b-continue`, `gate-a-return`, `gate-b-validator-fail`, `gate-a-validator-fail`, `gate-b-hard-size`, `gate-a-hard-size`, `gate-b-split`, `gate-a-split`, `dedup-revise`.
- Update SKILL.md Step 5b to parse `NEXT_ACTION` and `OOS_SKIP_BREADCRUMB` from prepare env, replacing the 5-way if-elif.
- Update `settle-rc-dispatch.md` dispatch-key section to name `SETTLE_NEXT_ACTION` as primary, rc as fallback.
- Update SKILL.md Step 3.5 (Gate B) and Step 1e (Gate A) settle-dispatch references accordingly.
- Add `NEXT_ACTION`, `OOS_SKIP_BREADCRUMB`, `SETTLE_NEXT_ACTION` to `PHASE_RESULT_ENV_ALLOW_KEYS` if absent.
- Add tests in `python/test_design_lifecycle.py` for the new `step5b_prepare_main` outputs.

### Surfaces in scope
- `python/design_lifecycle.py` (step5b_prepare_main)
- `skills/design/scripts/design-step35-settle.sh`
- `skills/design/SKILL.md` (Step 5b, Step 3.5, Step 1e settle references)
- `skills/design/references/settle-rc-dispatch.md`
- `python/test_design_lifecycle.py`

### Open questions
- None.
