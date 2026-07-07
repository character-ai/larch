### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:28-32
- **Concern**: Trusted-override soft-advisory contract is not pinned by a test. Scenario: The plan says a trusted `oversize_override` still sets `SOFT_ADVISORY=true`, but the listed tests never exercise that suppressed-trigger path. A later change could keep `SIZE_TRIGGER_FIRED=false` and silently drop the soft advisory without breaking the suite.
- **Proposed resolution**: Extend the existing override test or add a small diff-size-over-threshold fixture with trusted `oversize_override: operator` that asserts `SIZE_TRIGGER_FIRED=false`, `SOFT_ADVISORY=true`, and non-empty `TRIGGER_REASONS`.



