### OOS_1:
- **Description**: [OUT_OF_SCOPE] Review core does not short-circuit after aggregation collapses to zero findings. Scenario: A legitimate duplicate-only merge still launches voters and tallies an empty ballot; if voters fail or parse badly, a no-findings round can surface degraded voting noise
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:598-653
- **Phase**: design

### OOS_2:
- **Description**: Empty ballot still launches three voters after ok empty merge. Scenario: Wasted tokens; no functional break per plan
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-code-voters.sh (via review-core)
- **Phase**: design

