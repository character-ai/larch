### OOS_1: Reuse importable frontmatter/body split helper instead of a second local parser
- **Description**: Reuse importable frontmatter/body split helper instead of a second local parser. Scenario: The issue allows reusing lint_skill_invocations helpers when importable; a bespoke parser can drift on edge cases such as unclosed fences or CRLF handling that extract_frontmatter_and_body already normalizes.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_agent_tool_contract.py
- **Phase**: design



