## Decision 1: Auto-generated vs manually maintained split file
- **Question**: Should the new `reviewer-templates-code-reviewer.md` be auto-generated via a new generator verb, or manually maintained?
- **Resolution**: Auto-generated. Follows the existing pattern for `agents/code-reviewer.md`. CI drift detection ensures the split stays in sync with `reviewer-templates.md` whenever the archetype evolves.
- **Source**: codebase

## Decision 2: Include Variables section in the split file
- **Question**: Should the new file include only the Code Reviewer body, or also the Variables section?
- **Resolution**: Include the Variables section. Makes the file self-contained so the orchestrator understands `{REVIEW_TARGET}`, `{CONTEXT_BLOCK}`, and `{OUTPUT_INSTRUCTION}` without loading the full catalog.
- **Source**: codebase

## Decision 3: Scope of changes to other consumers
- **Question**: Do any other consumers (rendering.py `render reviewer`, /design, /review, /research) need changes?
- **Resolution**: No. Only `conflict-resolution.md` is changed. All other consumers continue to load the full `reviewer-templates.md`. The rendering.py `render_reviewer_main` (line 994) hardcodes the full template path and is not on the conflict-resolution path.
- **Source**: codebase

2 scope decisions resolved + 1 confirmed no-change.
