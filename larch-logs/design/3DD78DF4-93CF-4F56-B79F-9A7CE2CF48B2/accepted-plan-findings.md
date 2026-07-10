### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_cost.py:127-138
- **Concern**: Keep GLM alias canonicalization on the main-agent pricing path, not in the shared `rate_row()` used by subprocess pricing. Scenario: The plan requires `claude_sub` to remain priced from its recorded Claude model. If `rate_row()` canonicalizes `glm-5.2[1m]` globally, `_claude_sub_rates_for_model()` will also receive GLM handling, changing subprocess pricing when a recorded subprocess model uses that alias
- **Proposed resolution**: Apply the helper in `display_rates()` or another main-lane-only lookup path, or add an explicit non-GLM/subprocess path that preserves the recorded subprocess model unchanged

