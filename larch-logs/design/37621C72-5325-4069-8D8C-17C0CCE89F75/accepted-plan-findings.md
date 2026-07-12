### FINDING_1: Decompose placeholder newline contract is underspecified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The decompose update requires byte-compatible placeholder output while delegating to `compose_named_block`, which cannot reproduce the current blank line before the end marker. `compose_named_block` strips trailing newlines from inner content and appends exactly one newline before `<!-- larch:plan:end -->`, while the inline placeholder currently has two newlines after the prose line. An implementer pursuing byte compatibility may need to bypass `compose_named_block` or hand-compose markers again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Revise the decompose bullet: drop unconditional byte-compatible wording for inner newlines; state that visible fence and prose must match, allow one newline delta before the end marker, and golden-pin the exact fenced block in test_decompose.py after switching to compose_named_block.


### FINDING_2: Empty valid plan blocks lack explicit routing coverage
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Marker Contract Auditor
- **Severity**: minor
- **Concern**: The plan requires an empty but valid `larch:plan` block to route as `already-planned`, but the listed lifecycle tests cover whitespace tolerance and malformed or incomplete blocks without explicitly covering an empty valid block. A truthiness-based implementation could therefore route an empty valid block to `proceed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one routing test with an empty-inner valid plan block asserting ROUTE=already-planned. In design_router.py use plan_inner is not None (or malformed == "" and plan_inner is not None).
  - From Cursor-Requirements: Add a routing test with body `<!-- larch:plan:start -->\n<!-- larch:plan:end -->` (or whitespace-tolerant equivalent) and assert `ROUTE=already-planned`
  - From Cursor-dyn-Marker Contract Auditor: Add an explicit `design route` case with body `<!-- larch:plan:start -->\n<!-- larch:plan:end -->` asserting `ROUTE=already-planned`, plus a negative control with only a start marker.


### FINDING_4: Shared marker regex must reject markers split across lines
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-Marker Contract Auditor
- **Severity**: minor
- **Concern**: The planned public marker regex reuses `\s*`, which can consume newlines. This may allow marker syntax split across lines to be recognized by `diagnostic_prefix` or `parse_named_block` consumers, while line-by-line parsing rejects it, causing public and internal marker recognition to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use horizontal whitespace in the public line-anchored expression, such as `[ \t]*`, and add a regression case proving that marker syntax split across lines is rejected while ordinary whitespace-tolerant single-line markers remain accepted.
  - From Codex-dyn-Marker Contract Auditor: Use whitespace classes that exclude `\r` and `\n` in the shared expression, route both public and internal matching through it, and add a regression case proving a split-line marker is rejected.


