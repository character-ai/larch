### FINDING_1: Gate script still emits interactive questions on non-design BOTH_DOWN=false path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: On the non-design branch, `degraded-tools-gate.sh` ends with two question-style emits (lines 146–147). The plan only conditions the “final line,” so implement/review/research runs with one tool down can still print “Continue in this degraded mode (backup waterfall)…” after the auto-proceed path is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap both trailing emits in one BOTH_DOWN if/else (true: keep the two-line question; false: single "proceeding automatically" emit); extend Case 3 (or Case 13 with --skill implement) to assert the divergent last-line text on the else branch


### FINDING_2: Missing BOTH_DOWN parse fallback can auto-proceed when both externals are down
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan’s failure-modes bullet conflates partial-deploy safety with unparsed `BOTH_DOWN` on updated skills. After SKILL.md bullets replace the single interactive branch with `BOTH_DOWN=false`/`true` arms, an orchestrator that omits `BOTH_DOWN` from the parse has no documented fallback to ask-always; models often treat a missing flag like false and auto-proceed on `BOTH_DOWN=false`, including when both externals are down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In external-reviewers.md parse step, state that when DEGRADED=true and BOTH_DOWN is missing or not true|false, treat BOTH_DOWN=true (prompt); keep the partial-deploy bullet scoped to old skills only


### FINDING_3: external-reviewers.md intro still requires operator choice on every degraded run
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Section intro (line 26) still requires the operator to choose on every degraded run. After `BOTH_DOWN=false` auto-proceed, the canonical Step 0 contract contradicts the new single-tool-down behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Reword line 26 to require explicit confirmation only when BOTH_DOWN=true; single-tool-down may proceed after a notice


### FINDING_5: degraded-tools-gate.md contract intro still says orchestrator always asks
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: Contract intro (lines 14–16) still says the orchestrator always asks when `DEGRADED=true`. Operators reading `degraded-tools-gate.md` may miss that single-tool-down interactive runs auto-proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Amend lines 14-16 to match BOTH_DOWN branching (prompt only when BOTH_DOWN=true)

