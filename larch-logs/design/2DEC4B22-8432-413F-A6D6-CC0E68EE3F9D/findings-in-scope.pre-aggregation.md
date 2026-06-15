### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-step2b-drafter.sh:131-149
- **Concern**: Default-route test will not exercise unset LARCH_DESIGN_DRAFTER. Scenario: write_session_env always exports LARCH_DESIGN_DRAFTER=codex into session.env; sourcing that file overrides a shell unset, so the planned CODEX_PRESENT=true default test can still route to Codex and pass without covering the new behavior
- **Proposed resolution**: Add a write_session_env parameter (or sibling helper) that omits LARCH_DESIGN_DRAFTER for the default-route case; keep explicit codex coverage for existing scenarios

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-step2b-drafter.sh:131-148
- **Concern**: Default-routing test conflicts with write_session_env exporting LARCH_DESIGN_DRAFTER=codex. Scenario: Plan requires unset LARCH_DESIGN_DRAFTER but reuse of write_session_env; wrapper sources session.env and always picks codex, so the new test never covers Claude-as-default
- **Proposed resolution**: The harness step should omit or unset LARCH_DESIGN_DRAFTER in session.env for the default-routing case only; keep explicit codex export for existing cases

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:170
- **Concern**: SECURITY.md is omitted from the plan even though the Step 2b drafter default and Claude model default change. Scenario: After this PR the security policy still says Step 2b defaults to Codex when Codex is present and LARCH_DESIGN_PLAN_MODEL defaults to claude-fable-5, misleading consumers about the default subprocess and security posture
- **Proposed resolution**: Add ### UPDATED: SECURITY.md with a minimal edit to the Step 2b drafter subprocess paragraph and include SECURITY.md in the stale-default grep

