## Proposed Design Outline

### Goals
- Shrink `skills/implement/SKILL.md` and `skills/design/SKILL.md` by moving late and large step BODIES into on-entry references, so every turn before that step is cheaper.
- Advance guideline G-Skill-1 (load phase-local content lazily, at the point of need) with no change to step behavior or order.

### Non-goals
- No behavior, sequencing, or wrapper-call change. KEEP-safe: step markers, transitions, anti-halt boundaries stay inline.
- No blanket move. Mid-run steps without an existing on-entry Read stay inline.
- No relocation of S030-pinned literal paths or contract tokens out of SKILL.md.

### Approach sketch
- Two clean targets only. (a) Fold body into steps that already MANDATORY-READ on entry (zero new turns). (b) Relocate the latest steps into references read on entry (one new turn there; body absent for most of the run).
- `/implement` candidates: Step 5 (already reads on entry), Step 8+, Step 18.
- `/design` candidates: Step 5 / 5b / 5c / 5d (5b already reads `oos-step5b-dispatch.md` on entry).
- Each relocated body becomes a new or extended `references/*.md`; SKILL.md keeps the step skeleton plus an on-entry `MANDATORY — READ ENTIRE FILE` pointer.
- Where ```bash fences move, update `scripts/test-implement-fence-shape.sh` EXPECTED counts; run `make test-implement-fence-shape`.

### Surfaces in scope
- `skills/implement/SKILL.md`, `skills/design/SKILL.md`
- `skills/implement/references/`, `skills/design/references/` (new or extended files)
- `scripts/test-implement-fence-shape.sh` (fence-count update only if fences move)

### Open questions
- None. Per-step body selection is plan-drafting judgment under the two-clean-targets rule.
