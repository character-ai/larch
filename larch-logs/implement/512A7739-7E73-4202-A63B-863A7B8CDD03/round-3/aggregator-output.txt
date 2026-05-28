### FINDING_1: [OUT_OF_SCOPE] Session Setup still exceeds line-budget target
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` Session Setup remains roughly 130 lines, above the planned ~80±20% target, so Step 0 still carries too much inline prose and lacks a durable budget guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Cross-Skill Presence Propagation anchor was removed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `### Cross-Skill Presence Propagation` heading/contract disappeared from Step 0 even though later steps and plan traceability still refer to that propagation surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Dirty-tree recovery contract is incomplete and not self-contained
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery was reduced to a separate fence that calls functions from a prior Bash invocation, lacks the full operator clean-tree gate/resume semantics, and may drop argv or never reach `implement-bootstrap.sh --resume-plan-tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Session Setup structural pins are too broad
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh` still pins a broad Step 0 span instead of narrowed Session Setup anchors and resume-tail literals, so regressions inside the subsection can pass structure checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Step 2.4 fallback/drift messaging is inconsistent with actual coder routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2.4 messaging does not accurately cover implicit Codex selection, Cursor drift exit-2 behavior, or missing `claude_fallback` branches, so operators can miss the actual routing outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Duplicate coder/all phase wiring in bootstrap main
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.sh` duplicates `coder` and `all` phase wiring in `main()`, increasing the chance future phase edits update only one branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_9: Step 2.4 cannot distinguish explicit and implicit Claude routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 2.4 does not preserve or branch on explicit `--coder=claude`, so intentional main-agent selection receives the same generic messaging as implicit fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Invalid --coder argv lacks behavioral coverage and prompt-side fail-fast
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Invalid `--coder` values are only bounded by bootstrap internals; prompt-side parsing does not fail fast and no harness asserts the expected exit-2 usage path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Missing-plan coder skip harness is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover repo-available direct coder-phase behavior when `PLAN_FILE`/`plan.txt` is absent, so regressions could populate coder state or emit coder breadcrumbs incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Deprecated --codex-available can bypass bootstrap routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Direct `step2-implement.sh` callers can still use legacy `--codex-available` flags to select an implementer without the Step 0 bootstrap waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Bootstrap harness documentation omits implemented coder cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-implement-bootstrap.md` does not list several implemented `B5-coder` and edge breadcrumb cases, making the test inventory misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Cursor-first omitted --coder default broadens the default write surface
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Omitting `--coder` now prefers Cursor over Codex when both are available, changing the default implementation surface to `cursor agent -p --force --trust` without clearly documenting opt-in/pinning guidance or confirming the intended security tradeoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Codex dispatch lacks presence-drift symmetry
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `run-step2-dispatch.sh` fail-closes on Cursor drift but does not similarly check `CODEX_PRESENT=false` before dispatching Codex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_18: [OUT_OF_SCOPE] Changelog may conflict with Cursor-first default
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `CHANGELOG.md` may still describe a Codex-first implement default, conflicting with updated security/operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: SECURITY.md lacks planned Phase 4 adjacency wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` does not include the planned Phase 4 / #2738 / #2756 adjacency sentence clarifying the narrow scope of the Cursor-first reversal versus fixer paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
