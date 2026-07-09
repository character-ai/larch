### OOS_1: Bracketless lifecycle alternation in `LIFECYCLE_REJECT_RE` evades substring token checks
- **Description**: Bracketless lifecycle alternation in `LIFECYCLE_REJECT_RE` evades substring token checks. Scenario: Pattern `^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]` embeds bare state names, so neither `[DONE]` nor normalized `[DONE] ` substrings match; a major production reject path stays unlinted
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/issue_wire.py:33
- **Phase**: design



