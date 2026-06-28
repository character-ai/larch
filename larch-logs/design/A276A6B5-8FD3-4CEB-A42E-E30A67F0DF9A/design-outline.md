## Proposed Design Outline

### Goals
- Retire five orphaned reference files that have no runtime loader, removing ~490 lines of dead weight.
- Keep content with audit or contributor-spec value accessible under `docs/`.
- Update all live pointers and structure-test pins to the retired files.

### Non-goals
- No Python code changes or runtime behavior changes.
- No refactoring of active references files.
- No changes to SKILL.md or any operational orchestration logic.

### Approach sketch
- Delete `skills/implement/references/pr-body-template.md` and `step-16-17-sentinel.md` (zero live references after structure-test pin removal).
- Move `skills/design/references/dialectic-legacy.md` → `docs/attic/dialectic-legacy.md` (create `docs/attic/`); update `skills/shared/dialectic-protocol.md` pointer.
- Move `skills/implement/references/summary-comment-template.md` → `docs/summary-comment-template.md`; update `docs/run-logs.md`, `docs/issue-anchored-plan.md`, and `scripts/test-implement-structure.sh`.
- Remove `pr-body-template.md` and `summary-comment-template.md` from `scripts/test-implement-structure.sh` file-existence check list.
- (Adjacent) Delete `skills/design/references/oos-step5b-dispatch.md`; remove its pins from `scripts/test-design-structure.sh`, `scripts/test-design-structure.md`, and `skills/design/scripts/design-step5b-prepare.md`.

### Surfaces in scope
- `skills/design/references/` — `dialectic-legacy.md`, `oos-step5b-dispatch.md`
- `skills/implement/references/` — `pr-body-template.md`, `step-16-17-sentinel.md`, `summary-comment-template.md`
- `docs/` — new: `attic/dialectic-legacy.md`, `summary-comment-template.md`
- `skills/shared/dialectic-protocol.md`
- `scripts/test-implement-structure.sh`, `scripts/test-design-structure.sh`, `scripts/test-design-structure.md`
- `docs/run-logs.md`, `docs/issue-anchored-plan.md`
- `skills/design/scripts/design-step5b-prepare.md`

### Open questions
- None.
