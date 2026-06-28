## Decision 1: Target for auto-error-reporting content
- **Question**: New `references/auto-error-reporting.md` or append to existing `finalize-step5.md`?
- **Resolution**: Append to `finalize-step5.md` — avoids new file, matches the issue's explicit "or into finalize-step5.md" suggestion.
- **Source**: issue body + codebase

## Decision 2: What stays in SKILL.md for the sentinel folded-contract block
- **Question**: Which lines of the "Completion sentinels for pause/resume" block (SKILL.md lines 67-74) stay vs. move?
- **Resolution**: Remove Folded contract paragraph (line 67), Tradeoff paragraph (line 69), and Pause/resume coverage lines (71-72). Keep only the existing pointer at line 74. Move the removed prose to sentinel-host-table.md under a new "## Folded contract and tradeoff" section.
- **Source**: codebase

## Decision 3: Inline sentinel provenance notes per-step
- **Question**: Should the ~10 inline `.completed/step-X is batch-written by...` / `is written by...` notes be removed entirely or condensed to per-step pointers?
- **Resolution**: Remove entirely — the sentinel-host-table.md table already captures all provenance. The line 74 pointer is the single canonical reference maintainers need.
- **Source**: codebase
