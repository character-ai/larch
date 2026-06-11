### FINDING_1:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/blocker-helpers.sh:50-53,140-147
- **Concern**: [SCOPE-REDUCTION] Planned blocker port accepts state casing that the retired helper does not. Scenario: Plan makes native and prose blocker state checks case-insensitive, so blocker all-open can emit BLOCKERS=N where bash emitted BLOCKERS= for uppercase native rows or lowercase prose issue rows
- **Proposed resolution**: Match the retired helper's exact state literals: native .state == "open" and prose gh issue view state == "OPEN"; remove uppercase-native and lowercase-prose behavior from the plan unless a separate issue changes admission semantics

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/get-issue-info.sh:25-37
- **Concern**: [SCOPE-REDUCTION] Planned issue info fail-open contract is broader than the retired helper for flag values with no argument. Scenario: The plan says VALUE= on missing required args and exit 0 always, but --issue, --field, or --repo without a following value exits 1 before the missing-arg VALUE= path runs
- **Proposed resolution**: Limit VALUE=/exit 0 to absent required args, invalid field, invalid flag, and gh failures; specify exit 1 with no VALUE= for final missing flag values if preserving actual helper parity
