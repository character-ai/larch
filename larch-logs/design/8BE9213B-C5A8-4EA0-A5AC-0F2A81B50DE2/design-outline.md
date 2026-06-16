## Proposed Design Outline

### Goals
- Make one Python verb the sole writer of the initial `ship-pr-state.sh` key set; delete prompt-side composition (the NEVER #11 / #12 anti-pattern).
- Fold the `8-pre-ship` phantom probe into `step-8-ship.sh` so one Bash call enters the ship driver on the green path.
- Pin the canonical key set in a harness; collapse the stall-branch key re-list to one seeder call.

### Non-goals
- No change to the terminal-stall seeder (`stall-recovery seed-terminal-state`) or its minimal shape.
- No change to the `oos file` hook, the Python ship driver JSON/exit contract, or the 3.11 guard.
- Item 4 (`LARCH_SHIP_PR_IMPL` prose) is dropped as moot; the bash ship path is already retired.

### Approach sketch
- Add `python/cli.py ship seed-initial-state` in `python/ship.py`; the canonical key set becomes a module constant.
- The verb takes dynamic values (`BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, ...) plus stall-override flags; it writes uppercase `KEY=value` only and preserves the `MANIFEST_PATH`-empty guard + design-manifest note in its contract.
- SKILL.md Step 8: replace the `write-initial-state-keys` prose block with one seeder call; keep the `oos file` hook; remove the standalone probe fence.
- `step-8-ship.sh`: run `phantom-probe-with-warn.sh --step 8-pre-ship` internally before the ship driver.
- `step5-review-branches.md` stall branch: call the seeder, then apply stall overrides instead of re-listing keys.

### Surfaces in scope
- `python/ship.py`, `python/cli.py` (registry), `python/test_ship.py`
- `skills/implement/scripts/step-8-ship.sh` (+ `.md`), `skills/implement/scripts/test-step-8-ship.sh`
- `skills/implement/SKILL.md` (Step 8 entry + Step 5 stall stub), `skills/implement/references/step5-review-branches.md`
- `scripts/test-implement-fence-shape.sh` (Step 8 Bash-fence shape changes)

### Open questions
- None. Seeder home and stale-scope items resolved in Round 1.
