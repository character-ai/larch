# Review Round 2

- Mode: `diff`
- 11 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Dirty-tree recovery bootstrap does not preserve full recovery semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery in `skills/implement/SKILL.md` was collapsed too far. The resume-tail bootstrap omits required recovery behavior including operator gating, sentinel/env handling, clean re-check, `CLAUDE_PLUGIN_ROOT` recovery, full argv forwarding such as `--coder`, fork flags, and `--caller-env`, plus KV re-parse/export after recovery. This can cause resumed runs to keep stale dirty-tree state, lose explicit coder selection, or target the wrong repository/plugin root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: feature-description gate in phase_coder_select is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `feature-description.txt` gate in `phase_coder_select` lacks harness coverage. A path with `plan.txt` but no `feature-description.txt` could diverge from the SKILL routing table without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Missing explicit Codex binary-not-found unavailable case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a symmetric `--coder=codex` plus `CODEX_BINARY_FOUND=false` unavailable case, so Codex-specific binary-missing warning text could regress while cursor unavailable tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Dirty-tree resume tests do not cover resume through coder phase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree resume tests stop at `--up-to-phase plan`, while the SKILL resumes through coder phase. Resume-tail plus `phase_coder_select` regressions could avoid offline detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Waterfall order pin targets the wrong contract file
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-step2-routing.sh` still pins waterfall order against `SKILL.md` instead of `scripts/implement-bootstrap.md`, so the canonical script-side contract could drift while lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Cross-Skill Presence Propagation heading was removed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The `### Cross-Skill Presence Propagation` heading was removed from the Step 0 span despite the plan requiring that anchor to remain. This hurts traceability and may affect tooling keyed on the heading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: SECURITY.md lacks planned #2738/#2756 migration callout
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The planned SECURITY.md adjacency sentence for #2738/#2756 migration guidance was not added, leaving operators without the explicit Codex-first migration callout required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Missing missing-plan coder-selection harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The bootstrap harness lacks the plan-required missing-plan coder-selection case. Only repo-unavailable skip is covered, so a regression could allow `phase_coder_select` to emit `coder=` when `PLAN_FILE` or `plan.txt` is absent on a non-`REPO_UNAVAILABLE` path, breaking Step 2 dispatch silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Structural pins are incomplete or too broad
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` does not fully pin the planned structure. Existing checks scan too broad a Step 0 range and miss narrowed Session Setup bootstrap counts, in-fence foreground comment coverage, not-yet-implemented phase stubs, coder fallback KV parsing, and bootstrap breadcrumb literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Missing explicit --coder=claude happy-path harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The bootstrap harness does not separately test explicit `--coder=claude` with empty `coder_fallback`. A regression could incorrectly mark explicit Claude selection as fallback while implicit-to-Claude coverage still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: B4-all does not assert coder breadcrumb emission
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `B4-all` test does not assert the coder breadcrumb under `LARCH_QUIET_BREADCRUMBS=1`, so runs could omit the expected fifth `step0` coder breadcrumb while still passing KV assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


