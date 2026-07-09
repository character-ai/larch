### OOS_4: Shared bug_title_match() could replace some hand-rolled prefix tests
- **Description**: Shared bug_title_match() could replace some hand-rolled prefix tests. Scenario: Call sites might keep re-deriving prefix logic with constants instead of the helper
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/title_match.py:18-30
- **Phase**: design

### OOS_8: Aliased `re` imports are not mentioned
- **Description**: Aliased `re` imports are not mentioned. Scenario: Production code consistently uses `import re`; supporting `import re as regex` adds matcher complexity with no current trigger
- **Reviewer**: Cursor-dyn-Ast Ratchet Reviewer
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan: regex match positions
- **Phase**: design

