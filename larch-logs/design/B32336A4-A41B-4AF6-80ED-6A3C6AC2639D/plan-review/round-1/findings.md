### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/degraded-tools-gate.sh:146-147
- **Concern**: Non-design branch ends with two question emits; plan only says to condition the "final line". Scenario: Implement/review/research runs with one tool down can still print "Continue in this degraded mode (backup waterfall)…" after the auto-proceed path is added
- **Proposed resolution**: Wrap both trailing emits in one BOTH_DOWN if/else (true: keep the two-line question; false: single "proceeding automatically" emit); extend Case 3 (or Case 13 with --skill implement) to assert the divergent last-line text on the else branch

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:109-111
- **Concern**: Failure-modes bullet conflates partial-deploy safety with unparsed BOTH_DOWN on updated skills. Scenario: After the four SKILL.md bullets replace the single interactive branch with BOTH_DOWN=false/true arms, an orchestrator that omits BOTH_DOWN from the parse has no documented fallback to ask-always; models often treat a missing flag like false and auto-proceed on BOTH_DOWN=false, including when both externals are down
- **Proposed resolution**: In external-reviewers.md parse step, state that when DEGRADED=true and BOTH_DOWN is missing or not true|false, treat BOTH_DOWN=true (prompt); keep the partial-deploy bullet scoped to old skills only

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/external-reviewers.md:26
- **Concern**: Section intro still requires the operator choose on every degraded run. Scenario: After BOTH_DOWN=false auto-proceed, the canonical Step 0 contract contradicts the new single-tool-down behavior
- **Proposed resolution**: Reword line 26 to require explicit confirmation only when BOTH_DOWN=true; single-tool-down may proceed after a notice

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:43
- **Concern**: Edge case claims the sentinel fires on BOTH_DOWN=false notice paths but the procedure never says to touch it. Scenario: BOTH_DOWN=false skips AskUserQuestion; on /implement dirty-tree or resume-plan-tail re-entry the gate re-runs and re-prints the explanation
- **Proposed resolution**: In the BOTH_DOWN=false sub-branch (and line 43), require the same sentinel check/touch before proceed; say re-warn/re-ask not only re-prompt

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/degraded-tools-gate.md:14-16
- **Concern**: Contract intro still says the orchestrator always asks on DEGRADED=true. Scenario: Operators reading degraded-tools-gate.md miss that single-tool-down interactive runs auto-proceed
- **Proposed resolution**: Amend lines 14-16 to match BOTH_DOWN branching (prompt only when BOTH_DOWN=true)
