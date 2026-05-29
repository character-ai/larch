### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:292
- **Concern**: Integration case appended before `pass` inherits mutated harness env. Scenario: Late cases replace `mock-dispatch.sh`, `mock-monitor.sh`, and `LARCH_TALLY_PLAN_ASSESSOR_SH`; a reset-only subcase can still run round-2 assess against a broken tally/dispatch and flake or false-pass
- **Proposed resolution**: Require an isolated `mktemp` sub-tmpdir with fresh default stubs (or explicitly restore the file-top dispatch/monitor scripts and `LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/.../tally-plan-assessor.sh"`) before Entry 2 assertions

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1115,1130
- **Concern**: Plan claims every Step 3 exit path gets explicit Step 3.6 routing, but leaves the plan-size-trigger|plan-validator-defects branch without an explicit Step 3.6 disposition while the later note says to see per-status breadcrumbs above. Scenario: Implementer follows the plan literally and creates contradictory routing prose: the summary says these short-circuits skip Step 3.6, but the branch matrix still only routes to the handler before Gate B/3b and has no matching breadcrumb
- **Proposed resolution**: Minimally update the existing plan-size-trigger|plan-validator-defects branch line to state that Step 3.6 is skipped, and either add matching skip breadcrumbs there or change the later parenthetical so it does not claim breadcrumbs exist for statuses that do not have them

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1115
- **Concern**: The plan leaves the plan-size-trigger and plan-validator-defects branch-matrix entry without an explicit Step 3.6 disposition or breadcrumb, despite requiring every LOOP_STATUS exit to name route-through or skip-with-breadcrumb.. Scenario: Manual read-through acceptance can still fail because this exit remains silent in the branch matrix while the follow-up text says to see per-status breadcrumbs above.
- **Proposed resolution**: Add a minimum edit to that existing branch entry: note it skips Gate B and Step 3.6, and either add the intended skip breadcrumb there or remove the inaccurate per-status-breadcrumb expectation for those statuses.
