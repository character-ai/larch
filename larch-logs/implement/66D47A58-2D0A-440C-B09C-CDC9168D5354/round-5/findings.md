### FINDING_1: Gate B manual mode can degrade to auto-apply without mechanical persisted-state read
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate B manual/auto mode resolution relies on prompt memory or readable run-params instead of mechanically re-reading persisted manual intent. On `/design --manual`, jq/write-run-params failure or context loss can cause Gate B to auto-apply accepted findings despite `MANUAL_REQUESTED=true` existing on disk, contradicting argv and SECURITY.md. The normative docs also leave the `--manual` session-env override and precedence chain under-specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: manual_gate_b recovery merge rule is ambiguous and may clobber or preserve stale manual mode incorrectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Router-flag jq recovery treats `manual_gate_b` differently from partition/brainstorm flags by assigning from `manual_requested` instead of OR-merging. Reviewers disagree on the intended invariant: overwrite may clear stale manual mode, while OR-merge may preserve manual mode across recovery. The branch needs one documented canonical rule plus tests covering the chosen stale-state behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: --trivial flag row omits Gate B mode guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The compact flag table documents Gate B mode behavior for `--simple` and `--hard` but not `--trivial`, which may imply the trivial tier bypasses or differs on Gate B auto-apply/manual behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Gate B prose is duplicated across multiple normative surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Gate B mode and apply-path guidance is duplicated in SKILL Step 3, Step 3.5, approval-gates.md, and SECURITY.md, creating risk that future gate changes update only one surface and leave contradictory operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Manual Gate B path can run the shared post-apply pipeline twice
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Manual Gate B documentation duplicates the shared post-apply pipeline in option-specific text and the after-iteration block. An orchestrator following both normative blocks may run dedup-sweep, EMIT_PLAN validation, validator, and Step 2b.5 twice during one Gate B pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Apply-all body uses inconsistent lowercase “execute”
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The Apply-all body uses lowercase `execute` for the shared post-apply pipeline while other call sites use `Execute`, creating a minor normative consistency issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Default Gate B auto-apply can merge untrusted accepted findings before per-finding consent
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Default Gate B auto-apply writes all voted-in reviewer findings into `plan.txt` without per-finding operator consent. Malicious or mistaken accepted finding text can influence the plan before Gate C, including later validator dry-runs of plan command blocks. Security guidance should clearly direct high-risk runs to `--manual` and full Gate C review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Auto-apply breadcrumb exposes only truncated concern excerpts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate B auto-apply shows truncated concern excerpts, so operators may not see the full accepted reviewer text before the plan is revised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Same-UID tmpdir tampering can poison review artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A same-UID attacker could tamper with session tmpdir review artifacts such as accepted-plan-findings before Gate B. The reviewer marked this as existing trust-model behavior not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Gate B rollback semantics diverge from the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Gate A re-entry rollback semantics differ from the planned subsequent Gate B adjustment path. After Gate C sends an operator back to Gate A, the current docs require a Step 3 re-run instead of having the next Gate B honor `discussion-round2.md`, which may violate expected rollback behavior unless codified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Blocked-by dependency edge is not evidenced
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The acceptance criteria require a native blocked-by edge from #2667 to #2930, but the branch evidence does not show that dependency being recorded. Without it, #2667 may proceed against stale Gate B contract assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Step 3.5 emits duplicate Gate B breadcrumbs on default path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 3.5 prints a generic Gate B breadcrumb and then an auto-apply-specific breadcrumb on the default path, causing duplicate step markers in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
