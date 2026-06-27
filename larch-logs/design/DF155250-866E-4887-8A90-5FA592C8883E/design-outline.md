## Proposed Design Outline

### Goals
- Drop the two dead MANDATORY loads (`execution-issues-tracking.md` + `oos-pipeline.md`) from the `oos-pipeline` SKILL.md branch and replace with a slim security-sidecar stall instruction.
- Remove ~20 lines of branch-only/informational sections from the 88-line every-ship `ship-pr-exit-matrix.md` load, relocating relevant content to branch-specific references.
- Fix the stale "run the `/issue` pipeline" directive on the Python path.

### Non-goals
- Changes to `python/ship.py` or `python/file_oos.py` behavior.
- Changes to the bash-path OOS pipeline procedure in `oos-pipeline.md`.
- Any change to `execution-issues-tracking.md` cross-references to `oos-pipeline.md`.

### Approach sketch
- Replace `:810` `oos-pipeline` branch body with security-sidecar stall instruction + keep `ship-pr-oos-checkpoint-router.md` MANDATORY load.
- Update `ship-pr-exit-matrix.md` `:46` oos-pipeline branch to match; remove 4 branch-only sections.
- Move OOS cap section into `ship-pr-oos-checkpoint-router.md` (specified by issue).
- Move steps_ran invariant into `ship-pr-oos-checkpoint-router.md` (logical home).
- Add conflict-resolution.md MANDATORY READ inline to SKILL.md stall branch; trim remaining active-driver notes and transient-retry from matrix.

### Surfaces in scope
- `skills/implement/SKILL.md` (lines ~767, ~810, ~816, ~325)
- `skills/implement/references/ship-pr-exit-matrix.md`
- `skills/implement/references/ship-pr-oos-checkpoint-router.md`

### Open questions
- None.
