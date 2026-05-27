# Review Round 5

- Mode: `diff`
- 4 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_12: Step 3.5 emits duplicate Gate B breadcrumbs on default path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 3.5 prints a generic Gate B breadcrumb and then an auto-apply-specific breadcrumb on the default path, causing duplicate step markers in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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


### FINDING_5: Manual Gate B path can run the shared post-apply pipeline twice
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Manual Gate B documentation duplicates the shared post-apply pipeline in option-specific text and the after-iteration block. An orchestrator following both normative blocks may run dedup-sweep, EMIT_PLAN validation, validator, and Step 2b.5 twice during one Gate B pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


