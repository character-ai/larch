## Proposed Design Outline

### Goals
- Eliminate the standalone Step 2a Bash fence from `skills/design/SKILL.md` by folding sentinel writing into `step2b_drafter_main`.
- Replace the orchestrator's multi-field drafter-outcome parsing (POSTPLAN_RC, DRAFTER_STATUS, PAUSE_OK) with one wrapper-owned `DRAFTER_NEXT_ACTION` directive.
- Update tests and the launcher to reflect the removal of the `design step2a` CLI surface.

### Non-goals
- Changing the observable behavior of any drafter outcome (step3, inline-fallback, dirty-tree recovery, etc.).
- Refactoring the postplan pipeline beyond what's needed to emit the new directive.
- Touching any Step 3 or later surfaces.

### Approach sketch
- Move `step2a_main` logic (sentinel file writes, batch completion-sentinel touches, refuse-to-overwrite guard) into `step2b_drafter_main`, before the existing pause check at line 3634.
- After the `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN` delimiter, compute and emit `DRAFTER_NEXT_ACTION=<token>` covering all 10 outcome branches.
- Write rc12/rc13 plan-size diagnostic text to `$DESIGN_TMPDIR/.drafter-next-action-rc12.txt` so the orchestrator reads it only when the token is `postplan-rc12-split`.
- Update `SKILL.md`: delete Step 2a fence, update Step 2b drafter-fence prose to consume `DRAFTER_NEXT_ACTION`, update `resume@2a` routing to go to the drafter fence, update Anti-pattern #1 and the wrapper-contract-inventory.
- Delete `step2a_main` from `design_lifecycle.py`; remove the launcher mapping; remove `step2a` from `step2_verbs` in `test-design-structure.sh`; remove/repurpose step2a-specific tests in `test_design_lifecycle.py`.
- Update `sentinel-host-table.md` to show step-2a write moved to Step 2b drafter entry.

### Surfaces in scope
- `skills/design/SKILL.md` (Step 2a section, Step 2b drafter parsing, Anti-pattern #1, wrapper-contract-inventory)
- `python/design_lifecycle.py` (`step2a_main`, `step2b_drafter_main`)
- `python/larch/state/session_env.py` (launcher mapping for design-step2a.sh)
- `python/test_design_lifecycle.py` (step2a tests)
- `scripts/test-design-structure.sh` (lines 259, 350, 351, 371)
- `skills/design/references/sentinel-host-table.md`
- `skills/design/references/step2b-drafter-failsafe.md` (update failsafe token name)

### Open questions
- None.
