## Proposed Design Outline

### Goals
- Port the Step 6 combined + prelude + cleanup orchestration from the three `design-step6*.sh` wrappers into in-process Python in `python/design_lifecycle.py`, byte-for-behavior parity.
- Cut the SKILL.md launcher basenames to new `python/cli.py design step6*` verbs; delete the wrappers, the Step 6 test harness, and the two debug scaffolds.
- Keep `make lint-retired-scripts` green via `python/migrated-scripts.tsv` rows.

### Non-goals
- No behavior change to Step 6 logic. Parity-only port.
- No touching sibling G6 surfaces (clarify #4674, terminal/final-summary #4675, Step 5b #4676, Step 5c #4677 — all DONE).
- No redesign or consolidation of the combined → prelude → cleanup structure beyond parity.

### Approach sketch
- Add prelude / cleanup / combined entrypoints to `python/design_lifecycle.py`, mirroring the bash guard ladder (pause-save exec, `.bg-wait-active` in-flight guard, missing-sidecar, plan-write / publish / standalone-heavy / cleanup-eligible gates, sentinels, timing mark).
- Register `design step6`, `design step6-prelude`, `design step6-cleanup` rows in `python/cli.py`; route the three wrapper basenames to them in the design launcher map.
- Port the 5 `test-design-step6.sh` guard cases into `python/test_design_lifecycle.py`; then delete the bash harness.

### Surfaces in scope
- `python/design_lifecycle.py`, `python/cli.py`, design launcher basename map
- `skills/design/scripts/design-step6{,-prelude,-cleanup}.sh` (+ `.md` siblings)
- `skills/design/scripts/test-design-step6.sh` (+ `.md`), `python/test_design_lifecycle.py`
- `skills/design/scripts/_dbg-validator.sh`, `skills/design/scripts/_dbg5c2.sh`
- `skills/design/SKILL.md`, `python/migrated-scripts.tsv`, `scripts/test-design-structure.sh` pins

### Open questions
- None. Blockers landed; debug-scaffold disposition resolved (delete both).
