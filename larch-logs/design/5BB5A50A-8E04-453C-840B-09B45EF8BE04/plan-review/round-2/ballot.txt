### FINDING_1:
- **Reviewer(s)**: Codex-dyn-test-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44-57; <TMPDIR>/plan.txt:84-85; skills/design/SKILL.md:171-181
- **Concern**: Case 14 does not cover both-explicit conflicting alias values. Scenario: Step 0 builds writer argv with both CODEX_PRESENT and CODEX_AVAILABLE when both are present, but the planned test only rewrites with --codex-present false and omits --codex-available. An implementation can still emit contradictory explicit values such as CODEX_PRESENT=false and CODEX_AVAILABLE=true because the planned normalization only handles one-explicit/one-omitted pairs.
- **Proposed resolution**: Add the minimum Case 14 coverage for --codex-present and --codex-available supplied together with conflicting values, and assert the intended contract: reject the conflict or normalize to the canonical explicit value.

