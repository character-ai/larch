### OOS_1: [OUT_OF_SCOPE] Drop the duplicate $lint_prompt PLR0911 pin; the $lint_shared_prompt assertion already verifies the shared prompt section that all tiers consume.
- **Description**: [OUT_OF_SCOPE] Drop the duplicate $lint_prompt PLR0911 pin; the $lint_shared_prompt assertion already verifies the shared prompt section that all tiers consume.. Scenario: Combined-prompt duplication adds no new failure mode and makes the harness broader than the feature requires.
- **Reviewer**: Codex-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-prompt-template-invariants.sh:72-76
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

