### FINDING_1: Tier resolution drift across orchestrator, driver, and assess child
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: When `run-params.json` has conflicting `workflow_path` and `design_classification`, resolution is inconsistent: `design-plan-quality-assessor.sh` aligns to `design_classification` (lines 122–125), but Step 3.6 orchestrator breadcrumbs in `SKILL.md` (1051–1076) use `workflow_path` only, and `assess-plan-round.sh` still gates on raw `workflow_path`. Stale params such as `workflow_path=SIMPLE` + `design_classification=HARD` can print a SIMPLE skip breadcrumb while the driver runs write-after and invokes assess; assess may skip on SIMPLE while the inverse case can show a HARD banner but driver-skips. Operators see contradictory step state, wasted snapshot work, and possible post–Gate-B snapshot without the quality gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: write-after rollback leaves review-round-count elevated on write-cursor failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: In `design-plan-quality-assessor.sh` (251–260), write-after rollback decrements `review-round-count.txt` only when `write-cursor` succeeds. Legacy inline Step 3.6 always decremented the count first. On write-cursor failure after write-after failure, the count stays at `ROUND_NUM` instead of `ROUND_NUM-1`, diverging from prior cap semantics and the plan’s rollback promise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: `assess-failed` omitted from WORSE-gate skip lists and Step 3.6 completion-marker prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The driver emits `ASSESSOR_STATUS=assess-failed` and continues to Step 3b, but `SKILL.md` (1141, 1147) WORSE-gate no-prompt skip list and Step 3.6 success-boundary parenthetical omit `assess-failed` (and `driver skipped` where noted). Orchestrators following the prose literally may skip `.completed/step-3.6` on assess-failed paths, breaking pause/resume step tracking and creating contract drift vs driver settlement paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Stale result-env handoff tests skip on Linux CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: In `test-design-plan-quality-assessor.sh` (544–584), stale result-env write-failure tests use `chflags` and skip on Linux. Ubuntu CI never exercises `_assessor_force_stdout` handoff routing; stale-env regressions can ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: `assessor.md` omits new driver settlement UX paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `references/assessor.md` (33–40) omits `assess-failed` and `write-after-failed` operator UX alongside existing skip/0-assessor paths. Operators reading assessor.md miss the new driver settlement semantics; Step 3.6 non-prompt outcomes in SKILL.md also lack matching prose for `assess-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


