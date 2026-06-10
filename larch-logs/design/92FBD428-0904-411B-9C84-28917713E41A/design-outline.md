## Proposed Design Outline

### Goals
- Reduce each reviewer panel by one static archetype slot: combine `security` + `edge-cases` in `/implement`/`/review`; drop the `edge` slot in `/design` plan-review (distributing its focus to `arch` and `pragmatic`).
- Remove the Cursor-Edge sketch from the `/design` HARD sketch phase (3 remaining: Arch, Innovation, Pragmatic).
- Strip explicit reviewer count numbers from documentation (bias toward deletion over updating).

### Non-goals
- Do not change the `/review` voter panel (3-judge).
- Do not rename existing output files, slot names, or create new agent files.
- Do not refactor dispatch-plan-review-panel.sh to use a variable — just remove `edge` from the existing hardcoded loops.
- Do not delete `agents/reviewer-security.md` — keep it for existing test harnesses.

### Approach sketch
- `skills/review/scripts/dispatch-panel.sh`: remove `security` from `static_specialists` array.
- `agents/reviewer-edge-cases.md`: promote security from secondary scan to co-primary focus (injection, AuthN/Z, secrets, crypto).
- `skills/design/scripts/dispatch-plan-review-panel.sh`: remove `edge` from both `for _archetype in` loops; update the all-lenses Claude fallback text and the inline dynamic-archetype note.
- `skills/design/scripts/render-plan-review-prompt.sh`: remove the `edge` case; merge its focus into `arch` and `pragmatic` cases.
- `skills/design/references/sketch-prompts.md` + `sketch-launch.md`: remove EDGE_PROMPT entry and Cursor-Edge launch block; update ARCH/PRAGMATIC prompts to absorb edge-cases and failure-modes focus.
- `python/session_env.py`: add `3` to valid sketch_budget values `{"0","2","4"}` for HARD with 3 sketch slots.
- Docs + test fixtures: remove explicit reviewer counts; update test harnesses that reference `security` slot.

### Surfaces in scope
- `skills/review/scripts/dispatch-panel.sh`
- `agents/reviewer-edge-cases.md`
- `skills/design/scripts/dispatch-plan-review-panel.sh`
- `skills/design/scripts/render-plan-review-prompt.sh`
- `skills/design/references/sketch-prompts.md`
- `skills/design/references/sketch-launch.md`
- `skills/design/SKILL.md`
- `python/session_env.py`
- `skills/design/references/plan-review.md`
- `skills/design/scripts/dispatch-plan-review-panel.md`
- `docs/topology.md`, `docs/review-agents.md`, `docs/workflow-lifecycle.md`, `docs/skills.md`
- `README.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md`
- `skills/review/scripts/dispatch-panel.md`, `skills/review/scripts/check-reviewer-failure-threshold.sh`
- Test fixtures: `skills/review/scripts/test-tally-code-votes.sh`, `test-review-core.sh`

### Open questions
- None.
