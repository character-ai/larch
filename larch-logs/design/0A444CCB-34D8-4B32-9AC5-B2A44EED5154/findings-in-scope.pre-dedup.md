### FINDING_1:
- **Reviewer(s)**: Codex-dyn-Lint Contract Reviewer
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_agent_tool_contract.py:30-177; test_output_mandate_without_read_intent_passes, test_read_tool_granted_still_requires_fail_closed
- **Concern**: Add explicit v2 independence coverage for missing and scalar `tools:` declarations. Scenario: The plan requires v2 to run independently of the declaration, including missing and scalar values, but the proposed tests cover only Read-enabled and Read-less declarations. A regression that restores an early return for `declaration is None` or `not declaration.explicit_list` would leave the suite green while violating the required contract.
- **Proposed resolution**: Add focused tests for a missing `tools:` key and a scalar declaration such as `tools: *`, each with read intent plus `Emit strict JSONL only.` and no fail-closed language; assert exactly one v2 finding at the mandate line, no v1 finding, and exit code 1.



