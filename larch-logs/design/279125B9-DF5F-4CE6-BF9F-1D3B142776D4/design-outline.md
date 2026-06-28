## Proposed Design Outline

### Goals
- Elide the `step1d5 --mode entry` Bash fence when `brainstorm_requested=false`, saving ~1 orchestrator turn per non-brainstorm run.
- Preserve pause/resume correctness by folding the three `.completed` sentinel writes (step-1c, step-1d, step-1d.5) into `step1d7_main` before its existing `check_pause_and_exit` call.
- Keep the brainstorm-on path (entry fence + run/already-complete handling) fully intact.

### Non-goals
- No change to `step1d5 --mode complete` or `step1d5 --mode collect`.
- No change to the drafter sentinel writes (already idempotent and correct).
- No removal of the entry fence contract from SKILL.md — it remains under the brainstorm-on guard.

### Approach sketch
- Add a brainstorm-off guard at the top of the Step 1d.5 section in `skills/design/SKILL.md`: when `brainstorm_requested=false`, print the skip breadcrumb and continue to Step 1d.7 without running the entry fence.
- In `step1d7_main` (Python), write/touch `.completed/step-1c`, `.completed/step-1d`, `.completed/step-1d.5` before `check_pause_and_exit` (idempotent; no-op on brainstorm-on paths where entry fence already wrote them).
- Update SKILL.md sentinel-documentation lines for step-1c/step-1d/step-1d.5 to reflect `step1d7` as the new batch-write site on the brainstorm-off path.
- Add a new test in `test_design_lifecycle.py` asserting that `step1d7_main` writes the three sentinels before the pause check.
- Update `test-design-structure.sh` to check for the brainstorm-off guard in SKILL.md.

### Surfaces in scope
- `skills/design/SKILL.md` — Step 1d.5 section + sentinel documentation lines
- `python/larch/design/design_lifecycle.py` — `step1d7_main`
- `python/test_design_lifecycle.py` — new test for sentinel writes in `step1d7_main`
- `scripts/test-design-structure.sh` — new assertion for the brainstorm-off guard

### Open questions
- None.
