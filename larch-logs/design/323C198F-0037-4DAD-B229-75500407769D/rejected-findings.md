### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/agent_voters.py:488-498
- **Concern**: [SCOPE-REDUCTION] Both-externals-down still preserves a launched Claude voter, but the feature requires zero voters and main-agent adjudication.. Scenario: With --codex-available=false and --cursor-available=false, the planned unchanged launched_policies includes voter 1; a parseable Claude vote yields one effective judge. review_tally only returns TALLY_STATUS=main-agent-vote-required when effective == 0, so review_core can proceed with TALLY_STATUS=ok instead of the required main-agent adjudication path.
- **Proposed resolution**: Change the both-externals-down branch to launch no voter policies and route tally through the existing zero-voter main-agent-required path; update the paired tests and docs that currently preserve the single-Claude floor.




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/_auth.py:672-718; python/larch/agents/agent_voters.py:491-498
- **Concern**: [SCOPE-REDUCTION] Both-down still uses pre-vote hard fail or a Claude voter instead of the specified zero-voter main-agent adjudication.. Scenario: With CODEX_PRESENT=false and CURSOR_PRESENT=false, /review stops with DEGRADED_HARD_FAIL before a ballot can be adjudicated; if that gate is bypassed, the planned unchanged voter dispatch still launches voter 1 as Claude, so tally can resolve findings through a single judge instead of REVIEW_CORE_STATUS=main-agent-vote-required.
- **Proposed resolution**: Use the existing zero-voter tier for code-review both-down: do not launch voter policies when both externals are unavailable, make review core pass empty voter files so tally emits main-agent-vote-required, and adjust /review and /implement Step 5 gate text only as needed for that scoped handoff.




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/agent_voters.py:488-498
- **Concern**: [SCOPE-REDUCTION] Both-down path still launches a slot-1 Claude voter instead of the required zero-voter main-agent handoff. Scenario: With codex_available=false and cursor_available=false, the planned unchanged launched_policies keeps voter 1, dispatch-waterfall can produce a substantive Claude vote, and tally can decide findings instead of returning main-agent-vote-required
- **Proposed resolution**: Change the both-externals-down branch to launch no voter policies and route review_core/tally through the existing zero-voter main-agent-required path; update the both-down test and docs from single-Claude voter to zero-voter main-agent adjudication

