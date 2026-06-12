## Decision 1: Target file
- **Question**: Which file owns the review progress report?
- **Resolution**: `scripts/render-review-phase-detail.sh` (called by both `/design` `render-final-summary.sh` and `/implement` `write-final-report.sh`)
- **Source**: codebase

## Decision 2: No-rounds message
- **Question**: When no review rounds completed, what should the section say?
- **Resolution**: Output `## Review Phase Detail\n\nNo review rounds completed.\n` instead of empty content. Change occurs at the `[ -s "$rounds_list" ]` guard.
- **Source**: issue body

## Decision 3: Gantt placement
- **Question**: Where in the section should Gantt charts appear?
- **Resolution**: After the per-round summary table, before the "Top reviewers" block.
- **Source**: codebase structure

## Decision 4: Data source for Gantt
- **Question**: What data drives the Gantt bars?
- **Resolution**: `vendor` rows in `timing-ledger.tsv` (col[8]=start_s, col[9]=end_s), windowed to each round's start/end from the corresponding `round` row.
- **Source**: codebase

## Decision 5: Gantt format
- **Question**: ASCII or mermaid?
- **Resolution**: Mermaid `gantt` with `dateFormat X`, `axisFormat %M:%S`, timestamps normalized relative to round start (0-based seconds).
- **Source**: issue request + existing mermaid usage in the repo
