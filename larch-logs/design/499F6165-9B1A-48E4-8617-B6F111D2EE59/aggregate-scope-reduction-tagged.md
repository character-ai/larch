### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:126-143
- **Concern**: [SCOPE-REDUCTION] Planned `_renumber_finding_blocks` duplicates `review_aggregate._renumber_findings`. Scenario: The plan adds `_renumber_finding_blocks` even though `review_aggregate._renumber_findings` already splits with `parse_findings_text(..., boundary="any_heading")` and rewrites `### FINDING_N:` headings identically (`review_aggregate.py:603-606`). Two renumber helpers drift on heading grammar changes.
- **Proposed resolution**: Call `review_aggregate._renumber_findings` (or move one shared helper) instead of adding `_renumber_finding_blocks`.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:42-47
- **Concern**: [SCOPE-REDUCTION] Add an optional prefix_rows hook to _zero_findings_branch. Scenario: The caller already owns rows and can prepend gate rows before calling _zero_findings_branch. The extra parameter never changes emitted output, but it widens the contract and test surface.
- **Proposed resolution**: Remove prefix_rows and keep row concatenation in the caller.
