### OOS_1: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out. Scenario: The plan updates the Step 3 fingerprint paragraph and Tier-1 surfaces but leaves the shared Immediate-background wait rule at line 15 unchanged. Final summary and Step 4 tail fences load that generic rule first and can still treat prefix-identical repeats as probe-eligible before operators reach the Step 3-only repeat paragraph.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan limits repeat-fingerprint wording to the Step 3 subsection, orchestrator-never, AGENTS.md, anti-pattern #5, and explicit Step 5c prose. The shared generic rule at line 15 still says any non-empty premature notification may take one foreground probe with no prefix-identical repeat exception, so Final summary and Step 4 callers that load only that section can still probe on repeated identical output.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design



### OOS_3: Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan updates only the Step 3 fingerprint paragraph and adds local Step 5c repeat prose. The shared Immediate-background wait rule at line 15 still authorizes a foreground probe on any non-empty premature notification with no prefix-identical repeat exception, so Step 4 and Final summary waits can still probe on repeats.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design



