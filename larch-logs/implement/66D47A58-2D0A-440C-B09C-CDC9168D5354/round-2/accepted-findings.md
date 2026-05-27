### FINDING_1: Gate B presentation can run before mode is resolved
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Gate B presentation in `approval-gates.md` appears before the mode-resolution subsection, so a linear run can emit manual-mode presentation output before knowing whether `manual_gate_b` is true or false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Gate A re-entry lacks rollback procedure after auto-applied findings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate A re-entry mentions rollback of auto-applied findings via `discussion-round2.md` but does not define how to reconcile or revert already-applied plan text when discussion changes the accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Step 3/3.5 prose references argv instead of persisted `manual_gate_b`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `SKILL.md` Step 3/3.5 wording refers to `--manual` argv rather than persisted `manual_gate_b`, which can confuse re-entry after Gate C(c) review reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Manual Gate B mode can be lost when run-params persistence or jq fails
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `--manual` / `manual_gate_b` depends on persisted `run-params.json` or in-memory state. If write-run-params fails, `jq` is unavailable, or execution resumes in a later subshell/context, Gate B can silently default to auto-apply instead of fail-closed manual mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: `--simple` flag table contradicts manual Gate B semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `--simple` row in `skills/design/SKILL.md` unconditionally describes auto-applied findings, which conflicts with `--manual` / `-m` and the shared Gate B mode semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Structural tests do not pin Step 0b `--manual|-m` parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` pins downstream manual-mode wiring but not the public flag parse enumeration, so future edits could drop `--manual` / `-m` parsing while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Auto-apply branch grep pin is not unique
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `manual_gate_b=false` structural pin can match fallback/degradation prose instead of the actual auto-apply branch, allowing branch behavior to regress without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Structural tests do not pin auto-apply breadcrumb and header
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Gate B auto-apply breadcrumb and `## Plan Review Findings — Auto-applying` header are acceptance-relevant but not pinned in structural tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


