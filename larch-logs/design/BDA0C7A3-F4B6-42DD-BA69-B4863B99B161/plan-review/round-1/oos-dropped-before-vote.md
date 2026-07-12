### OOS_4: Plan says canonical blocked-by command path without naming the automation entrypoint
- **Description**: Plan says canonical blocked-by command path without naming the automation entrypoint. Scenario: Two add paths exist (`block-issue` GraphQL vs `issue add-blocked-by` REST used by `/larch:issue` batch filing). Unspecified choice risks inconsistent idempotency/retry behavior in migrate-deps.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py
- **Phase**: design

### OOS_5: Retired panel failure may leave misnamed `failed-judge-panel` terminal outcome
- **Description**: Retired panel failure may leave misnamed `failed-judge-panel` terminal outcome. Scenario: Inline validation failure is not a judge-panel failure, but existing final-summary wiring still knows `failed-judge-panel`.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md
- **Phase**: design

