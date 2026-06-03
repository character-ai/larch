### FINDING_1: Step 3.6 handoff test mirror still implements the legacy fat fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-plan-quality-assessor.sh` still mirrors legacy env/result parsing, workflow-path gating, SIMPLE driver invocation, and `ASSESSOR_STATUS=paused` routing instead of the production rc-only thin fence with classification gating, trailer filtering/validation, and rc=11 pause handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-classification-gate-output.txt, dyn-trailer-protocol-output.txt: Address the concern above.


### FINDING_13: Assessor verdict/env paths are not confined to `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-fence-output.txt
- **Severity**: latent
- **Concern**: `ASSESSOR_VERDICT_FILE` and `ASSESSOR_VERDICT_ENV` paths parsed from child output are checked for symlinks but not canonicalized and constrained under `DESIGN_TMPDIR`, allowing a poisoned path to expose arbitrary readable file content in operator-visible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-bash-fence-output.txt: Address the concern above.


### FINDING_18: `assess-plan-round.md` still documents workflow-path gating
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/assess-plan-round.md` still says HARD gating reads `workflow_path`, rather than documenting `design_classification` / `read-design-classification.sh` fail-closed HARD semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


### FINDING_20: `lib-phase-driver.md` under-documents quiet FD capture mechanics
- **Reviewer(s)**: dyn-trailer-protocol-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/lib-phase-driver.md` says FD 3 emit output is captured but does not explain the quiet-mode capture mechanism or debugging pattern, so adopters may capture FD 1 and miss display output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-protocol-output.txt: Address the concern above.

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


### FINDING_9: Handoff test pre-prints an orchestrator banner not emitted by the thin SKILL fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Handoff test 19b prints an orchestrator banner itself, which can mask double-banner or missing-driver-banner behavior relative to production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


