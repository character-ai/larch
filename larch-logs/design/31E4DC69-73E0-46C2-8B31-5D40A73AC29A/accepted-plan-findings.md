### FINDING_7: Repeated Root Cause sections are lost by dictionary-based parsing
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: minor
- **Concern**: The planned origin helper relies on `_split_sections()`, which overwrites repeated headings. When an issue contains multiple Root Cause sections, only the last body remains, so markers in earlier sections are missed and the required document-order classification becomes incorrect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal origin-specific ordered section iterator, or adjust section parsing to preserve repeated headings, then test a marker in the first of two root-cause sections
  - From Codex-Requirements: Add an ordered, unsqueezed section iterator or extend the splitter to preserve duplicate sections, then classify every allowed root-cause body in document order.

