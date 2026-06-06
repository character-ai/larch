### OOS_1:
- **Description**: plan-review.md still gates Step 3.6 to HARD runs. Scenario: Zero-findings and all-rejected paths document assessor only on HARD; SIMPLE operators reading plan-review get wrong sequencing
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:125,179
- **Phase**: design

### OOS_2:
- **Description**: SECURITY.md still labels assessor lane HARD-only. Scenario: Policy doc understates SIMPLE assessor exposure after this change; trust-boundary prose still applies but tier label is stale
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:135
- **Phase**: design

### OOS_1:
- **Description**: Snapshot failure message still says HARD assessor flow. Scenario: Operator-facing error text stays tier-wrong after SIMPLE snapshots are enabled
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/design-postplan-emit.sh:261
- **Phase**: design

