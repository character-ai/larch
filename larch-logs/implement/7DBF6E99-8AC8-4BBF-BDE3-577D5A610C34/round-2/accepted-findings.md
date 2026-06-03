### FINDING_15: Quiet-mode FD-3 production capture is not adequately tested
- **Reviewer(s)**: dyn-fd-quiet-output.txt
- **Severity**: latent
- **Concern**: The assessor harness mostly disables quiet mode or captures via redirects, while production uses command substitution with quiet routing enabled. The markdown contract also claims quiet-mode rc=10 fallback coverage that the shell harness does not fully pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-quiet-output.txt: Add a harness case that leaves quiet enabled, captures with `out=$(…)` (matching the SKILL fence), and asserts banner/WORSE/trailer content on `out` while proving incidental `printf` KV lines written only to `larch-quiet-*.log` are absent from `out`.
  - From dyn-fd-quiet-output.txt: Either add the missing quiet + `$(…)` + rc=10 tests (display present, trailers present in capture, FD-1 log lacks user-facing lines) or narrow the markdown contract to match what is actually pinned.

### FINDING_4: Pause/resume harness lacks Step 3.6 and Gate-B-bypass coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-pause-resume.sh` was not extended for registry Step 3.6 or Gate-B-bypass sentinel behavior. Resume regressions can therefore ship without harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-state-output.txt: Add cases: (1) 3.5 complete, 3.6 incomplete → pause saves `STEP=3.6`, resume hits assessor fence; (2) bypass with only `step-3` → pause saves `STEP=3.5` (fails today); (3) bypass after triple touch → later pause resumes at `3b`.


### FINDING_6: Step 3.6 handoff harness omits pause-before-SIMPLE and ordering behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `apply_step3_6_handoff()` does not fully mirror the production Step 3.6 prelude: pause-before-classification, SIMPLE skip sentinel behavior, and timing ordering are under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-state-output.txt: Align `apply_step3_6_handoff` with the full fence (pause → timing mark stub → classification → SIMPLE skip with sentinel), and add a test with `.pause-requested` + `design_classification=SIMPLE` expecting pause-save without calling the assessor driver.


