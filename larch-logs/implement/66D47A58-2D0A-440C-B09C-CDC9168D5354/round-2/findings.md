### FINDING_1: Gate B presentation can run before mode is resolved
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Gate B presentation in `approval-gates.md` appears before the mode-resolution subsection, so a linear run can emit manual-mode presentation output before knowing whether `manual_gate_b` is true or false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_4: Step 3.5 prose implies full manual presentation for all Gate B runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 3.5 text says Gate B presents all accepted findings before describing the auto-apply compact-list path, which can mislead orchestrators/readers into using full manual presentation during default auto-apply runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
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

### FINDING_8: Missing executable coverage for `--manual` jq-merge recovery
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Literal pins do not prove that jq-merge recovery preserves `manual_gate_b=true` when write-run-params fails with `--manual`; a regression in the merge path could ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Gate B jq-read warning is not pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The warning emitted when `manual_gate_b` cannot be read from `run-params.json` is not structurally pinned, so wording or append-tool-failure behavior could drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Runtime Gate B branch behavior lacks automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Existing tests do not execute Gate B to verify auto-apply versus manual branch behavior, breadcrumb emission, or Apply-all ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Manual per-finding path duplicates Apply-all pipeline
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The manual “Go through each” path duplicates the post-revision Apply-all pipeline, creating a drift risk if the shared terminal ordering changes in only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Auto-apply increases untrusted-reviewer prompt-injection risk before Gate C
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Default Gate B auto-applies accepted reviewer findings into `plan.txt` before final Gate C approval. Because reviewer artifacts are untrusted, this increases the risk that malicious or overreaching text becomes part of the plan before the operator reviews the final result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: SECURITY.md and Gate B trust-boundary docs need to stay synchronized
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` documents Gate B auto-apply trust boundaries and manual-mode fail-closed behavior, so future edits to Gate B behavior need corresponding security-doc alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_16: [OUT_OF_SCOPE] Pre-Step-0 argv scan omits `--manual`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-Step-0 argv scan prose does not list `--manual`, which may make readers think the flag is not validated at entry even though Step 0b parses it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Post-PR blocked-by relationship is not evidenced
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The required GitHub blocked-by edge `2667 blocked-by 2930` is not evidenced in the branch diff, so issue dependency ordering may not be recorded unless an operator runs the block command after PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
