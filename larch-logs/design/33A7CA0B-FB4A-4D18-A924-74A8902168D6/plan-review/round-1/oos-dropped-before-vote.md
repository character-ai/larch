### OOS_3: No RULE contract pin test unlike markdown port
- **Description**: No RULE contract pin test unlike markdown port. Scenario: Markdown tests lock occurrence_baseline, syntax_policy, pathspecs, and allow_inline_suppression on RULE. Drift on those flags is easy to miss during a 900-line deletion.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_unreachable_branch.py:test_rule_contract_flags
- **Phase**: design

