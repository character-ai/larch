### FINDING_11: Missing-plan coder skip harness is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover repo-available direct coder-phase behavior when `PLAN_FILE`/`plan.txt` is absent, so regressions could populate coder state or emit coder breadcrumbs incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: Dirty-tree resume can re-probe and change coder selection
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree resume re-runs `phase_coder_select` with fresh probes, so the selected coder can change across resume without repeating waterfall warnings or documenting re-probe semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Bootstrap docs omit feature-description gate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md` documents the `PLAN_FILE` gate but omits the `feature-description.txt` early-return condition in `phase_coder_select`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Dirty-tree recovery contract is incomplete and not self-contained
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery was reduced to a separate fence that calls functions from a prior Bash invocation, lacks the full operator clean-tree gate/resume semantics, and may drop argv or never reach `implement-bootstrap.sh --resume-plan-tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Step 2.4 fallback/drift messaging is inconsistent with actual coder routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2.4 messaging does not accurately cover implicit Codex selection, Cursor drift exit-2 behavior, or missing `claude_fallback` branches, so operators can miss the actual routing outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Bootstrap coder test labels diverge from planned numbering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Coder tests are labeled `B5-coder-*` instead of planned `B11-B17`, creating harness/doc traceability drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: Resume-tail fence lacks CLAUDE_PLUGIN_ROOT recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The dirty-tree resume fence does not recover `CLAUDE_PLUGIN_ROOT`, so degraded sessions can fail before bootstrap or child scripts run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


