## Proposed Design Outline

### Goals
- Remove every near-empty Bash turn whose only payload is prelude (source-env + pause-check + timing mark) or a `.completed/step-N` sentinel write.
- Preserve pause coverage at all surviving Bash boundaries and full sentinel coverage for pause/resume.
- Document the chosen tradeoff: coarser timing granularity, pause honored at the next real fence.

### Non-goals
- No changes to `design-pause-save.sh` / `design-pause-load.sh` or resume routing logic.
- No folding of sentinel writes that already share a fence with real work (in-fence writes, Gate-B-bypass branch writes, `.outline-approved`).
- No reference-file fence restructuring (brainstorm.md launch fences stay).

### Approach sketch
- Delete the 5 standalone prelude fences (1c, 1d, 1d.5, 1d.7, 1e); host one combined `Steps 1c–1e — discussion block` timing mark in the Step 0c fence.
- Batch sentinels step-1c/1d/1d.5/1e into the Step 2a entry fence, after source-env and before the pause-check.
- Full audit folds: step-2a → 2a.5 fence (HARD), step-2a.5 → 2b prelude, step-3 → 3.5 fence, step-3.5 → 3.6 fence, step-4 → 4b emit-preview fence (absorbing 4b's timing-only prelude), step-4b → Step 5 fence, step-5b → first 5c fence, step-5d → Step 6 fence.
- Keep check 21 green via section-local prose naming each folded write site; consciously update assertions only where a section loses all sentinel text.

### Surfaces in scope
- `skills/design/SKILL.md` (primary), `scripts/test-design-structure.sh` (check 21 / fence assertions), `skills/design/references/discussion-rounds.md` and sibling references only if step-boundary prose names moved write sites, docs note for the timing tradeoff.

### Open questions
- None.
