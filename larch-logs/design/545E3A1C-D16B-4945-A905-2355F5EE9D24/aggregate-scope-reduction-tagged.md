### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/learn_from_bugs.py:252-260
- **Concern**: [SCOPE-REDUCTION] Rewrite `_split_sections` as a line scanner instead of filtering existing `finditer` matches. Scenario: The plan replaces the ~10-line `finditer` loop with a new scan-and-slice path, increasing offset and whitespace regression risk while `diff_lines: 80` already budgets a bounded change
- **Proposed resolution**: Widen `_HEADING_RE` to `#{2,4}`, precompute fenced interior line indices once, keep `finditer(prefix)` and drop matches whose line index is fenced; preserve today's `start`/`end` slicing unchanged
