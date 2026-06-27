### OOS_1: Active orchestrator docs still blame empty `<task-notification>` events solely on bash `set -m`
- **Description**: Active orchestrator docs still blame empty `<task-notification>` events solely on bash `set -m`. Scenario: After monitor mode is removed, operators and future reviewers may misdiagnose residual empty notifications as a regression of this fix rather than separate harness behavior
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:165
- **Phase**: design



### OOS_2: `kill -- -"$_pid"` teardown is only valid when the worker became its own process-group leader
- **Description**: `kill -- -"$_pid"` teardown is only valid when the worker became its own process-group leader. Scenario: Plan ties correctness to always passing `--new-process-group` from the wrapper; any future caller that omits the flag would keep using PGID-style teardown against a non-leader background job
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:360-364
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Active Step 3 wait docs still attribute all empty-output notifications to bash set -m only
- **Description**: [OUT_OF_SCOPE] Active Step 3 wait docs still attribute all empty-output notifications to bash set -m only. Scenario: After this change, set -m is gone but design-background-wait.md and skills/design/SKILL.md Anti-pattern #5 still tell operators empty notifications are spurious job-control from set -m (#5240). Residual harness signals may remain. Misleading recovery guidance, not a functional break.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:21
- **Phase**: design



