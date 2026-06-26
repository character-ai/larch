## Proposed Design Outline

### Goals
- Remove ~28-39 lines from two always-loaded /implement references by splitting branch-only bodies into conditional sub-references.
- Load each split body only on its triggering branch (skip-eligible 18a.5 path; `NEXT_ACTION=oos-pipeline`; `NEXT_ACTION=ci-fix`).
- Update test harness to validate the new files and relocated needles.

### Non-goals
- No behavior change: same content, different load timing.
- No changes to CI workflow files.
- No changes to any Python implementation; edits are Markdown-only.

### Approach sketch
- Create 3 new `skills/implement/references/` files with Consumer/Contract/When-to-load headers.
- Remove the moved sections from `step18-cleanup.md` and `ship-pr-exit-matrix.md`; replace with MANDATORY READ pointers.
- Update `SKILL.md`'s `ci-fix` branch bullet to point to the new sub-reference.
- Update `scripts/test-implement-structure.sh`: relocate the moved needles to the new files, add header checks.

### Surfaces in scope
- `skills/implement/references/step18-cleanup.md`
- `skills/implement/references/ship-pr-exit-matrix.md`
- `skills/implement/SKILL.md`
- `scripts/test-implement-structure.sh`
- NEW: `skills/implement/references/step18a5-filing.md`
- NEW: `skills/implement/references/ship-pr-oos-checkpoint-router.md`
- NEW: `skills/implement/references/ship-pr-ci-fix.md`

### Open questions
- None.
