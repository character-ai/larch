## Decision 1: Initial-state seeder home
- **Question**: The issue floats a new bash `seed-ship-pr-state.sh` or a `seed-initial` mode on `stall-recovery-report.sh`. Where should the single writer of the canonical initial `ship-pr-state.sh` key set live, given seeding is already Python-canonical and the migration playbook bans new `.sh` shims?
- **Resolution**: New Python verb `python/cli.py ship seed-initial-state` in `python/ship.py` (which already owns `_write_ship_state` / `_write_terminal_state`). The canonical key set becomes a module-level constant, pinned by `python/test_ship.py`.
- **Source**: user

## Decision 2: Acceptance item 4 (LARCH_SHIP_PR_IMPL compression)
- **Question**: Acceptance item 4 asks to compress `LARCH_SHIP_PR_IMPL=bash` opt-in prose, but that variable and any bash-ship opt-in prose no longer exist (bash ship driver + exit matrix already retired; migration playbook bans `LARCH_*_IMPL` selectors). Keep or drop?
- **Resolution**: Drop item 4 as moot. No prose to compress. Note the correction in the design so the issue record is accurate.
- **Source**: user

## Decision 3: Second duplicate-prose file location
- **Question**: The issue names `skills/review-and-fix/scripts/review-implement-step5-loop.md` as a second site duplicating the seed key list. Does it exist?
- **Resolution**: No. The entire `skills/review-and-fix/` tree is just `SKILL.md`. The real duplication is between `skills/implement/SKILL.md` (the canonical `<!-- write-initial-state-keys:begin/end -->` block + the Step 5 stall stub at SKILL.md) and `skills/implement/references/step5-review-branches.md` (the `stall` branch re-lists the full canonical key set inline). Dedup retargets to `step5-review-branches.md`; intent (one writer, no inline key re-list) is unambiguous.
- **Source**: codebase

## Decision 4: Scope boundaries (what stays untouched)
- **Question**: What is explicitly out of scope / must not change?
- **Resolution**: OUT of scope — (a) the terminal-stall seeder `python/cli.py stall-recovery seed-terminal-state` (`python/stall_recovery.py`) keeps its minimal-shape behavior unchanged; (b) the legacy bash `stall-recovery-report.sh cmd_seed_terminal_state`; (c) the pre-ship `oos file` hook; (d) the Python ship driver's `--state-file` refresh/JSON-exit contract; (e) the Python 3.11 guard in `step-8-ship.sh`. Hard constraints to preserve — the `MANIFEST_PATH`-must-be-empty guard and the design-manifest confusion note (move them into the seeder's contract, do not delete); the phantom probe stays advisory and `exit 0`; uppercase `KEY=value`-only state grammar.
- **Source**: codebase / issue

## Decision 5: Phantom-probe fold behavior
- **Question**: When the `8-pre-ship` phantom probe moves inside `step-8-ship.sh` (immediate-background), the orchestrator no longer parses its `PHANTOM_*` advisory KVs, and the probe runs on every driver re-invocation (OOS / transient / CI-fix re-entry) rather than once.
- **Resolution**: Acceptable and intended by the issue. The probe is advisory and always exits 0; its warning still surfaces in the wrapper's captured output. No first-entry sentinel (KISS) — running once per driver invocation is the smallest change. Drop the orchestrator-side `PHANTOM_*` parse note for the green path.
- **Source**: codebase / issue
