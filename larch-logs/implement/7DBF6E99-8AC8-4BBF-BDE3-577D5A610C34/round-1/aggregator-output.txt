### FINDING_1: Step 3.6 handoff test mirror still implements the legacy fat fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-plan-quality-assessor.sh` still mirrors legacy env/result parsing, workflow-path gating, SIMPLE driver invocation, and `ASSESSOR_STATUS=paused` routing instead of the production rc-only thin fence with classification gating, trailer filtering/validation, and rc=11 pause handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Missing structural `assert_thin_fence` guard for Step 3.6
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` only pins positive strings and lacks the planned helper/anti-shape assertions that would prevent reintroducing file-first env parsing, `phase_driver_read_result_env`, or other fat-fence logic into the Step 3.6 SKILL block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Gate-B-bypass paths do not write Step 3.5/3.6 completion sentinels
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass branches in `skills/design/SKILL.md` skip Step 3.5/3.6 but do not consistently write `.completed/step-3`, `.completed/step-3.5`, and `.completed/step-3.6` before Step 3b, so pause/resume can re-enter intentionally skipped work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Pause/resume harness lacks Step 3.6 and bypass-sentinel coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-pause-resume.sh` does not cover resume at Step 3.6 or Gate-B-bypass triple-sentinel behavior, so resume routing can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Plan-quality-assessor contract docs still describe fat handoff semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-plan-quality-assessor.md` still documents workflow-path gating, env-file parsing, `ASSESSOR_STATUS=paused`, old pause/exit behavior, or split/contradictory exit tables instead of the thin-fence rc/trailer contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_6: Missing trailer spoofing, invalid-trailer, neutralization, quiet-mode, and sidecar-injection tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: Planned security/regression harness cases for rc=10 trailers, spoofed markers, invalid trailer fail-closed behavior, display neutralization, quiet capture, and sidecar injection are absent or only partially covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_7: Test harness markdown still advertises obsolete or missing coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-plan-quality-assessor.md` still lists stale fat-handoff pins or claims trailer/spoof/rc=11 coverage that the shell harness does not implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Legacy `workflow_path` variable names persist after classification refactor
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-classification-gate-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.sh` stores design classification in a variable still named `workflow_path`, preserving a legacy mental model that may invite future misuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-classification-gate-output.txt: Address the concern above.

### FINDING_9: Handoff test pre-prints an orchestrator banner not emitted by the thin SKILL fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Handoff test 19b prints an orchestrator banner itself, which can mask double-banner or missing-driver-banner behavior relative to production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Missing shared thin-fence harness for future phase migrations
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no Step-3.6-specific shared thin-fence harness beyond markdown guidance, so later phase migrations may repeat the same fence drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: `_emit_worse_display` may re-expand model-derived summary text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_emit_worse_display` is reported to process model-derived `QUALIFICATIONS_SUMMARY` through a here-string pattern that reviewers believe could execute embedded command substitutions during WORSE display rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: rc=10 trailer parsing uses an unquoted heredoc on captured trailer text
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-fence-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` feeds `_assessor_trailers` through an unquoted heredoc, which reviewers flag as shell-expansion risk if trailer bytes contain command substitution syntax.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-bash-fence-output.txt: Address the concern above.

### FINDING_13: Assessor verdict/env paths are not confined to `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-fence-output.txt
- **Severity**: latent
- **Concern**: `ASSESSOR_VERDICT_FILE` and `ASSESSOR_VERDICT_ENV` paths parsed from child output are checked for symlinks but not canonicalized and constrained under `DESIGN_TMPDIR`, allowing a poisoned path to expose arbitrary readable file content in operator-visible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-bash-fence-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Broader captured-output here-string hardening remains pre-existing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `parse_kv_from_output` is reported to use `<<<` on child stdout text, a pre-existing pattern reviewers want hardened alongside summary handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Classification resolution captures stderr with stdout via `2>&1 | tail -n 1`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` classification resolution can be confused by warning/diagnostic lines on the merged stream, potentially causing unintended HARD defaulting or parsing errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] `SECURITY.md` omits several thin-fence control details
- **Reviewer(s)**: dyn-bash-fence-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` documents sidecar parsing and display neutralization at a high level but omits parser-only trailers, post-marker numeric trailer sourcing, fail-closed invalid-trailer abort, and related control details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fence-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] SIMPLE classification skip discards diagnostics
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: The Step 3.6 cheap classification gate discards `read-design-classification.sh` stderr on SIMPLE skip, so operators may not see classification warnings in skip-only runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.

### FINDING_18: `assess-plan-round.md` still documents workflow-path gating
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/assess-plan-round.md` still says HARD gating reads `workflow_path`, rather than documenting `design_classification` / `read-design-classification.sh` fail-closed HARD semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `design-postplan-emit` still uses or documents legacy workflow-path terminology
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: nit
- **Concern**: `design-postplan-emit.sh` and/or its markdown retain `WORKFLOW_PATH` / `workflow_path` terminology even though runtime gating now uses design classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.

### FINDING_20: `lib-phase-driver.md` under-documents quiet FD capture mechanics
- **Reviewer(s)**: dyn-trailer-protocol-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/lib-phase-driver.md` says FD 3 emit output is captured but does not explain the quiet-mode capture mechanism or debugging pattern, so adopters may capture FD 1 and miss display output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-protocol-output.txt: Address the concern above.
