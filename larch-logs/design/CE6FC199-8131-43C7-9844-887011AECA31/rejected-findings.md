### [Plan Review] FINDING_3

### FINDING_3: Baseline identity field is not restricted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The shared baseline parser accepts both `normalized_condition` and `pattern_name` rows, so this rule could accept mixed or incorrectly keyed baseline identities despite selecting `normalized_condition`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add rule-aware baseline schema validation that rejects pattern_name or mixed rows for this normalized_condition rule, and test those rejection cases.

