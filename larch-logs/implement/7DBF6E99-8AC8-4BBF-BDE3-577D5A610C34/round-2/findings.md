### FINDING_1: [OUT_OF_SCOPE] Stale assessor docs still describe the removed fat orchestrator handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-bash-fence-output.txt, dyn-fd-quiet-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: Multiple docs still describe obsolete fat-fence behavior for Step 3.6: orchestrator-side workflow/classification resolution, file-first `.step3.6-assessor.env` parsing, `ASSESSOR_STATUS=paused` routing, incomplete `0/2` exit tables, and stale Stop/security prose. This contradicts the implemented thin-fence contract with rc `0/2/10/11`, driver-owned display, trailer-only Stop round control, and orchestrator rc branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-bash-fence-output.txt: Rewrite `design-plan-quality-assessor.md` Orchestrator handoff to match the thin-fence block in `SKILL.md` (and `lib-phase-driver.md` Thin orchestrator fence); drop symlink/mandatory-key/stdout-fallback steps.
  - From dyn-fd-quiet-output.txt: Replace §Orchestrator handoff with the thin shape from `design-plan-quality-assessor.md:92-96` / `lib-phase-driver.md:42-48` and drop stdout-fallback routing prose.
  - From dyn-resume-state-output.txt: Replace §Orchestrator handoff with the thin shape (pause guard → classification gate → capture → trailer filter → `case $rc`), delete obsolete symlink/mandatory-key steps, and cross-link `lib-phase-driver.md`.

### FINDING_2: [OUT_OF_SCOPE] Gate-B-bypass paths do not stamp Step 3, 3.5, and 3.6 completion sentinels before Step 3b
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-fd-quiet-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass branches skip Gate B and Step 3.6 but do not reliably write `.completed/step-3`, `.completed/step-3.5`, and `.completed/step-3.6` before routing to Step 3b. A later pause/resume can therefore re-enter Step 3, Step 3.5, or Step 3.6 despite the bypass being intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-quiet-output.txt: Address the concern above.
  - From dyn-bash-fence-output.txt: In each Gate-B-bypass branch (and in a small shared bash snippet if needed), `mkdir -p "$DESIGN_TMPDIR/.completed"` and touch `step-3`, `step-3.5`, and `step-3.6` before routing to Step 3b; add the `test-design-pause-resume.sh` bypass coverage described in the plan.
  - From dyn-resume-state-output.txt: Before every bypass→3b route (matrix bullets and the `cap-reached` block), add an explicit orchestrator action—ideally a small shared bash snippet—to `mkdir -p "$DESIGN_TMPDIR/.completed"` and touch `.completed/step-3`, `.completed/step-3.5`, and `.completed/step-3.6` together; pin it in `scripts/test-design-structure.sh` and extend `skills/design/scripts/test-design-pause-resume.sh` with bypass→pause→resume cases.
  - From dyn-resume-state-output.txt: Move the triple-sentinel write (or at minimum `step-3`) into each bypass branch *before* the jump to 3b, or add a single mandatory “Gate-B-bypass completion block” placed immediately after the post-loop matrix and before any short-circuit to 3b.

### FINDING_3: [OUT_OF_SCOPE] Structural tests lack thin-fence and bypass-sentinel guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-fd-quiet-output.txt, dyn-resume-state-output.txt, dyn-trailer-spoofing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` lacks the planned `assert_thin_fence` helper and bypass-specific sentinel assertions. Current pins are mostly positive string checks, so CI may miss regressions back to fat-fence parsing or missing Step 3/3.5/3.6 bypass sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-fence-output.txt, dyn-resume-state-output.txt, dyn-trailer-spoofing-output.txt: Address the concern above.
  - From dyn-fd-quiet-output.txt: Implement `assert_thin_fence` per the plan and apply it between `<!-- step:3.6` and `<!-- step:3b` so FD/display routing cannot drift back to file-first parse loops.

### FINDING_4: Pause/resume harness lacks Step 3.6 and Gate-B-bypass coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-pause-resume.sh` was not extended for registry Step 3.6 or Gate-B-bypass sentinel behavior. Resume regressions can therefore ship without harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-state-output.txt: Add cases: (1) 3.5 complete, 3.6 incomplete → pause saves `STEP=3.6`, resume hits assessor fence; (2) bypass with only `step-3` → pause saves `STEP=3.5` (fails today); (3) bypass after triple touch → later pause resumes at `3b`.

### FINDING_5: Classification resolver parses merged stdout and stderr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` resolves classification via `2>&1 | tail -n 1`, so extra stdout/stderr lines could misclassify `SIMPLE` versus `HARD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Step 3.6 handoff harness omits pause-before-SIMPLE and ordering behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `apply_step3_6_handoff()` does not fully mirror the production Step 3.6 prelude: pause-before-classification, SIMPLE skip sentinel behavior, and timing ordering are under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-state-output.txt: Align `apply_step3_6_handoff` with the full fence (pause → timing mark stub → classification → SIMPLE skip with sentinel), and add a test with `.pause-requested` + `design_classification=SIMPLE` expecting pause-save without calling the assessor driver.

### FINDING_7: Assessor summary rendering may expand model-written shell syntax
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_emit_worse_display` reads `QUALIFICATIONS_SUMMARY` from a model-written sidecar and renders it with a here-string pattern the reviewer says can expand embedded shell syntax, allowing command execution during WORSE-majority display.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: rc=10 trailer parsing uses an unsafe heredoc shape
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-fence-output.txt, dyn-trailer-spoofing-output.txt
- **Severity**: important
- **Concern**: The production `SKILL.md` rc=10 trailer loop feeds `_assessor_trailers` through an unquoted heredoc, diverging from the safer harness mirror and risking expansion or delimiter-injection behavior if trailer/display bytes become attacker-controlled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-bash-fence-output.txt: Replace the heredoc with the same quoted form as the harness, e.g. `while IFS= read -r _assessor_trailer_line || [ -n "$_assessor_trailer_line" ]; do ... done <<<"$_assessor_trailers"`, or pipe from `printf '%s\n' "$_assessor_trailers"` without expansion.
  - From dyn-trailer-spoofing-output.txt: Replace the heredoc with `done <<<"$_assessor_trailers"` (same as the test handoff).

### FINDING_9: [OUT_OF_SCOPE] Misleading `workflow_path` variable name remains after refactor
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.sh` still uses a variable named `workflow_path` for design classification, which is misleading even though behavior matches the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: WARN/display emissions are not consistently neutralized
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt
- **Severity**: important
- **Concern**: `_emit_warn_lines` can emit WARN text on FD 3 without the same neutralization applied to WORSE/qualification lines, allowing spoof-like machine lines to appear near validated trailer output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt: Run every user-visible `emit` through `_neutralize_assessor_display_line` (or a single `_emit_display` helper), including WARN, banner, and paused note.

### FINDING_11: [OUT_OF_SCOPE] Stop-round and pause-delegation hardening observations
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt, dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: Reviewers noted positive/out-of-scope hardening: Stop round control now uses the validated post-marker trailer rather than `.step3.6-assessor.env`, and rc=11 pause delegation appears correctly owned by the driver/orchestrator split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt, dyn-resume-state-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Driver-side spoof resistance positive observation
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted positive/out-of-scope spoof-resistance properties: confined sidecar paths, fixed-key reads, no `source`/`eval`, neutralized WORSE prose, numeric trailer validation, and related harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Additional planned harness gaps remain for trailer and summary edge cases
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt
- **Severity**: latent
- **Concern**: Reviewer identified planned harness gaps not treated as branch regressions: no handoff test for rc=10 with no marker, no explicit `QUALIFICATIONS_SUMMARY` shell-metachar execution test, and no `assert_thin_fence` helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Some handoff tests still encode stale fat-fence assumptions
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt, dyn-fd-quiet-output.txt
- **Severity**: latent
- **Concern**: Some tests still treat symlink refusal, stdout fallback, and handoff display as orchestrator/fat-fence behavior even though the thin fence no longer reads `.step3.6-assessor.env` or merges stdout KVs into chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt: Address the concern above.
  - From dyn-fd-quiet-output.txt: Drop or rewrite fat-handoff cases to assert driver `emit` output in `handoff-driver.stdout`, trailer filtering in `chat.out`, and result-env-only machine state; keep symlink tests driver-side only (`phase_driver_write_result_env`).

### FINDING_15: Quiet-mode FD-3 production capture is not adequately tested
- **Reviewer(s)**: dyn-fd-quiet-output.txt
- **Severity**: latent
- **Concern**: The assessor harness mostly disables quiet mode or captures via redirects, while production uses command substitution with quiet routing enabled. The markdown contract also claims quiet-mode rc=10 fallback coverage that the shell harness does not fully pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-quiet-output.txt: Add a harness case that leaves quiet enabled, captures with `out=$(…)` (matching the SKILL fence), and asserts banner/WORSE/trailer content on `out` while proving incidental `printf` KV lines written only to `larch-quiet-*.log` are absent from `out`.
  - From dyn-fd-quiet-output.txt: Either add the missing quiet + `$(…)` + rc=10 tests (display present, trailers present in capture, FD-1 log lacks user-facing lines) or narrow the markdown contract to match what is actually pinned.
