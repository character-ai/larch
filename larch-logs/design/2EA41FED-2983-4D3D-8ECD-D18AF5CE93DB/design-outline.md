## Proposed Design Outline

### Goals
- Add a Step 5 external-stop recovery entry to `docs/workflow-lifecycle.md`, parallel to the existing Step 3 paragraph.
- Add `orphan-timeout` to the Tool Failures routing list in `skills/implement/references/step5-review-branches.md`.

### Non-goals
- No code changes; all updates are documentation only.
- No new runtime behavior; the recovery mechanics already exist and are tested.
- No changes to files outside the two listed targets.

### Approach sketch
- Insert a `Step 5 external-stop recovery` bullet in the Standalone Usage section of `docs/workflow-lifecycle.md` immediately after the Step 3 bullet, mirroring its structure.
- In `step5-review-branches.md`, append `orphan-timeout` to the Tool Failures token list in the `stall` section prose.

### Surfaces in scope
- `docs/workflow-lifecycle.md` (Standalone Usage section, after the Step 3 external-stop bullet)
- `skills/implement/references/step5-review-branches.md` (stall section Tool Failures list)

### Open questions
- None.
