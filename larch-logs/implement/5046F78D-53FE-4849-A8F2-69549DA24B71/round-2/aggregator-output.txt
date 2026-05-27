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

### FINDING_3: Step 2.4 Claude messaging does not distinguish explicit Claude from fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 2.4 messaging lacks a reliable explicit-argv signal for `--coder=claude`, so explicit Claude selection and implicit fallback-to-Claude paths can produce indistinct or misleading operator messaging. The implicit Codex-unavailable path may also miss the expected warning text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Session Setup subsection exceeds line-count acceptance target
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Session Setup subsection in `skills/implement/SKILL.md` remains above the planned collapse target of roughly 80 lines plus or minus 20 percent. This misses the acceptance criterion even if the functional behavior is otherwise correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Coder harness labels do not match planned B11-B17 range
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Coder tests use `B5-coder-*` labels instead of the plan-specified contiguous `B11`-`B17` range, which can make issue and harness cross-references drift from actual test names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] phase_coder_select re-reads unused presence keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `phase_coder_select` re-reads `CODEX_PRESENT` and `CURSOR_PRESENT` but does not use those locals for routing. This creates clarity drift and may mislead future maintainers about which values drive coder selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
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

### FINDING_10: feature-description gate in phase_coder_select is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `feature-description.txt` gate in `phase_coder_select` lacks harness coverage. A path with `plan.txt` but no `feature-description.txt` could diverge from the SKILL routing table without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Explicit coder-unavailable tests do not assert breadcrumb suppression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Explicit coder-unavailable harness cases do not verify that coder breadcrumbs are suppressed when `LARCH_QUIET_BREADCRUMBS=1`. A coder-unavailable bail could still emit `step0: coder=` and confuse breadcrumb-count expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Missing explicit Codex binary-not-found unavailable case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a symmetric `--coder=codex` plus `CODEX_BINARY_FOUND=false` unavailable case, so Codex-specific binary-missing warning text could regress while cursor unavailable tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Cursor-first implicit default changes security posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The implicit omitted-coder default is now Cursor-first, selecting a higher-trust Cursor path when both external tools are available. Operators who relied on Codex-first sandboxing may unexpectedly get Cursor full-trust writes unless they explicitly pass `--coder=codex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: SECURITY.md no longer documents Step 2 mechanical guards clearly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Condensed security documentation removed visibility into Step 2 mechanical guards that still exist in code. Reviewers or operators may incorrectly infer that submodule, path, or commit backstops were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Deferred runs may reach coder selection before tracking metadata is published
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Widened `should_run_post_tracking_phase` lets deferred `POSTED=false` paths run `phase_coder_select`, so Step 2 can receive `coder=` before tracking metadata is fully published. This weakens the audit trail unless intentional and documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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
