### [Plan Review] FINDING_2

### FINDING_2: Compact-table headers still use print/render language outside scoped rewrite
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan scopes legend removal and post-notification bullet rewrites, but surviving header language still implies orchestrator-side TSV selection or manual rendering. The Files-to-modify exemplar does not retire the numbered step-2 title `**Print the compact table once** using this data path:`. Progress Reporting line 49 (`Print the compact table once`) and all three numbered step-2 headers sit outside the scoped rewrite ranges and are not explicitly retired. This conflicts with the read-only Read-tool emit contract and can leave orchestrator-side TSV rendering instructions in place even when nested bullets below are updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit Files-to-modify bullet: replace the step-2 title with `**Emit the compact table once**` (or equivalent) and drop `using this data path`; the only source is Read on `$DESIGN_TMPDIR/reviewer-status-table.txt`.
  - From Cursor-Pragmatic: Require all three compact-table sites to rename step 2 to an emit-only header (for example "Emit the pre-rendered reviewer-status table once") and rewrite line 49 to state the only output is the verbatim Read of `$DESIGN_TMPDIR/reviewer-status-table.txt`; delete any remaining "print/render from TSV" phrasing in those headers.


