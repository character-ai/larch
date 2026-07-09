### FINDING_1: Violations should follow stderr contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan appears to route lint violations to stdout, but the repo’s sibling lint helpers and their tests expect violations on stderr. Following the plan as written would diverge from the established lint stream contract and likely break the mirrored tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Align the plan with sibling lints: print violations to stderr in the pinned path:line:message format, keep tool failures on stderr, and state explicitly that tests assert capsys.readouterr().err like test_lint_shared_convention_regex.py and test_lint_skill_invocations.py.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Reuse importable frontmatter/body split helper instead of a second local parser
- **Description**: Reuse importable frontmatter/body split helper instead of a second local parser. Scenario: The issue allows reusing lint_skill_invocations helpers when importable; a bespoke parser can drift on edge cases such as unclosed fences or CRLF handling that extract_frontmatter_and_body already normalizes.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_agent_tool_contract.py
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

