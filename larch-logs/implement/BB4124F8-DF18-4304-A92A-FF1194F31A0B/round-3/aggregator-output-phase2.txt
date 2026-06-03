Verifying cited code locations to normalize merged concerns accurately.
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

### FINDING_3: [OUT_OF_SCOPE] write-after rollback semantics documentation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: write-after rollback uses `write-cursor --value ROUND_NUM` with count decrement only on success. Pre-existing cursor/count semantics; the failure path warns but remains hard to reason about relative to the state machine.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_6: `apply_step3_6_handoff` lacks end-to-end coverage for `assess-failed`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver tests cover `assess-failed`, but `apply_step3_6_handoff` does not. Handoff/chat behavior for the degraded status is unverified end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: `assessor.md` omits new driver settlement UX paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `references/assessor.md` (33–40) omits `assess-failed` and `write-after-failed` operator UX alongside existing skip/0-assessor paths. Operators reading assessor.md miss the new driver settlement semantics; Step 3.6 non-prompt outcomes in SKILL.md also lack matching prose for `assess-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: `--timeout` not validated at driver argv parse and not passed from orchestrator
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-plan-quality-assessor.sh` (75–78) accepts `--timeout` without validating it as a positive integer before forwarding to `assess-plan-round.sh`; invalid strings fail deep in assess dispatch. `SKILL.md` (1072–1075) does not pass `--timeout` to the driver (defaults align at 1860 today, but contract is implicit).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: `LARCH_*_SH` overrides execute without path allowlisting
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_SNAPSHOT_PLAN_ROUND_SH` and `LARCH_ASSESS_PLAN_ROUND_SH` (103–104) select child scripts without path allowlisting. If a parent shell exports malicious `LARCH_*_SH` values before `/design`, the driver executes attacker-controlled code with session tmpdir access.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Step 3.6 result-env parser accepts embedded newlines in KV values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 env parser in `SKILL.md` (1094–1106) does not reject newline characters inside KV values. A writer of `.step3.6-assessor.env` in the session tmpdir can inject extra lines parsed as `ASSESSOR_STATUS`/`ASSESSOR_VERDICT` and spoof WORSE-gate routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
