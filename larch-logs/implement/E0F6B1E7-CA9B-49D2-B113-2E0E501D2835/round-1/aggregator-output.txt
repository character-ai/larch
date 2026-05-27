### FINDING_1: Gate A See-full-plan contract lacks structural pins
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate A rename and See-full-plan drop-on-re-fire behavior is not pinned by `scripts/test-design-structure.sh`, so future Gate-A-only drift could pass while Gate C pins still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Gate C Step 4b prose duplicates branch-handler details
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` Step 4b has a very long line duplicating `approval-gates.md` branch-handler semantics, increasing drift risk for See-full-plan and Other behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Gate C plan-display semantics are repeated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Gate C See-full-plan and Other-path contracts are repeated across several `approval-gates.md` sections, creating pre-existing normative redundancy and future drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Gate C missing-plan pick path is underspecified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate C does not define pick-time handling when `plan.txt` is missing or empty after the presentation warning-only path, so selecting See full plan can show nothing and then reduce the menu without an explicit recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Gate C drop-on-re-fire state is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate C See-full-plan drop-on-re-fire behavior has no session marker or behavioral test, so compaction or executor reset could re-offer four options or fail to drop See full plan within the same loop entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Step 3 and Gate C full-plan discovery differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3 and Gate C use different full-plan discovery paths; operators see summary wording at Step 3 but a structured option only at Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Branch includes unrelated commits
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch includes unrelated version-bump and Codex-interactive fix commits, widening the PR diff beyond the See-full-plan feature scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] AskUserQuestion behavior depends on prose compliance
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` AskUserQuestion option shape is prose-only, so runtime behavior depends on executor compliance; this is a pre-existing architectural pattern accepted by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
