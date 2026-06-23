## Proposed Design Outline

### Goals
- Add `ship route-exit` Python verb that maps ship-driver exit code + `needs_user_reason` → one `NEXT_ACTION=` token.
- Extend `step8_oos_checkpoint_main` (already in `implement_dispatch.py`) to emit `NEXT_ACTION=reship` on exit 0 after folding run-statistics write + `OOS_PENDING=false` update into Python.
- Reduce Step 8+ orchestrator prose in `SKILL.md` from dense exit-matrix paragraphs to a short NEXT_ACTION branch table.

### Non-goals
- Do not change the `ship pr` driver or its JSON stdout contract.
- Do not move the 30s transient sleep, the CI-fix autonomy procedure, or `/issue` skill calls into Python.
- Do not change `oos disposition-checkpoint` itself.

### Approach sketch
- Add `ship_route_exit_main` in `python/implement_dispatch.py`; registered as `("ship", "route-exit")` in `python/cli.py`.
- Extend `step8_oos_checkpoint_main` in `python/implement_dispatch.py`: on rc 0, write run-statistics via `run-log write`, set `OOS_PENDING=false` via `larch_io.read_kvs`/`write_kvs`, emit `NEXT_ACTION=reship`.
- Update `skills/implement/scripts/step-8-oos-checkpoint.sh` to call `python/cli.py implement step-8-oos-checkpoint` instead of `oos disposition-checkpoint` directly; strip now-redundant shell logging logic.
- Add one new fence to `skills/implement/SKILL.md` after `step-8-ship.sh`: call `ship route-exit`; replace the ~5-paragraph exit-matrix prose with a NEXT_ACTION branch table.
- Update `EXPECTED_NEW` in `scripts/test-implement-fence-shape.sh` (34 → 35).

### Surfaces in scope
- `python/implement_dispatch.py`
- `python/cli.py` (registry entry)
- `python/test_implement_dispatch.py` (new tests)
- `skills/implement/SKILL.md` (Step 8+ prose + one new fence)
- `skills/implement/scripts/step-8-oos-checkpoint.sh` (call `implement step-8-oos-checkpoint`)
- `skills/implement/scripts/step-8-oos-checkpoint.md` (update contract)
- `skills/implement/references/ship-pr-exit-matrix.md` (update routing docs)
- `scripts/test-implement-fence-shape.sh` (`EXPECTED_NEW` counter)

### Open questions
- None.
