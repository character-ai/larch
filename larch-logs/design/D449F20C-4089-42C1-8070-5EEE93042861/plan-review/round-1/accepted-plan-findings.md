### FINDING_1: Integration case inherits mutated harness stubs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Entry 2 integration/reset-only assertions can run after earlier cases mutate mock dispatch, monitor, and assessor state, allowing the subcase to exercise broken harness dependencies and either flake or false-pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require an isolated `mktemp` sub-tmpdir with fresh default stubs (or explicitly restore the file-top dispatch/monitor scripts and `LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/.../tally-plan-assessor.sh"`) before Entry 2 assertions


### FINDING_2: Plan-size and validator-defect branch lacks explicit Step 3.6 disposition
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The `plan-size-trigger|plan-validator-defects` branch is still silent or contradictory about whether Step 3.6 is routed through or skipped, while surrounding prose claims every exit path has an explicit disposition and matching breadcrumb guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Minimally update the existing plan-size-trigger|plan-validator-defects branch line to state that Step 3.6 is skipped, and either add matching skip breadcrumbs there or change the later parenthetical so it does not claim breadcrumbs exist for statuses that do not have them
  - From Cursor-Requirements, Codex-Requirements: Add a minimum edit to that existing branch entry: note it skips Gate B and Step 3.6, and either add the intended skip breadcrumb there or remove the inaccurate per-status-breadcrumb expectation for those statuses.

