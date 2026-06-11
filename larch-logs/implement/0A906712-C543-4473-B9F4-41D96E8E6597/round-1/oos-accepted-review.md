### OOS_1: [OUT_OF_SCOPE] Step 8 continuation paths can revert to foreground shipping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-background-migration-parity-output.txt, dyn-background-resume-state-output.txt
- **Severity**: important
- **Concern**: Step 8 initially uses the backgrounded `step-8-ship.sh` wrapper, but OOS, retry, CI-fix, conflict recovery, and exit-matrix continuation prose still references foreground ship re-entry. Those paths can reintroduce blocking ship behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace foreground re-invoke prose with step-8-ship.sh plus run_in_background true and timeout 21600000.
  - From codex-specialist-testing-output.txt: Update the exit matrix continuations to use the same immediate-background Step 8 contract and pin it with a grep-style test.
  - From dyn-background-migration-parity-output.txt: Normalize Step 8+ prose to “backgrounded `step-8-ship.sh` wrapper” everywhere, including OOS re-entry and Exit 6 retry instructions, and pin the foreground/background contract in `test-step-8-ship.sh` or fence-shape tests.
  - From dyn-background-resume-state-output.txt: Replace “foreground fence” in the OOS checkpoint with the same Immediate-background `step-8-ship.sh` contract used at initial Step 8 entry, and align any sibling references (`skills/implement/references/ship-pr-exit-matrix.md`) in the same change set.


### OOS_2: [OUT_OF_SCOPE] Step 2 dispatch remains foreground despite long implementer runtime
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-background-migration-parity-output.txt, dyn-timeout-tier-calibration-output.txt, dyn-background-resume-state-output.txt
- **Severity**: important
- **Concern**: Step 2 still requires foreground `run-step2-dispatch.sh` or `step2-implement.sh` execution even though implementer runs can take many minutes. This conflicts with the new immediate-background policy and leaves one of the longest paths on the old blocking model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add immediate-background to the run-step2-dispatch fence with a timeout at least matching the dispatcher wall clock, or document a deliberate foreground carve-out.
  - From cursor-specialist-correctness-output.txt: Update or remove the step2-implement.md pointer and align that contract with NEVER #8.
  - From codex-specialist-correctness-output.txt: Change Step 2 dispatch and Q/A redispatch to require run_in_background: true with an appropriate timeout and rely on task notification before parsing KV stdout.
  - From codex-specialist-edge-cases-output.txt: Mark Step 2 dispatch and Q/A redispatch as run_in_background: true with a timeout aligned to the launcher cap, and update the step2-implement wait contract.
  - From cursor-specialist-testing-output.txt: Add run_in_background: true and timeout to Step 2.1 dispatch; update step2-implement.md orchestrator wait contract to match.
  - From cursor-specialist-testing-output.txt: Reconcile Step 2 with NEVER #8; include run-step2-dispatch in the NEVER #8 example list.
  - From codex-specialist-testing-output.txt: Mark the Step 2 dispatch fence as immediate-background with an explicit timeout, and update the wait text to rely on task notification before parsing stdout.
  - From dyn-background-migration-parity-output.txt: Either exempt Step 2 explicitly in NEVER #8 with rationale (edit-authority / envelope contract) and remove the `step2-implement.md` pointer from the background list, or extend Step 2 to the same immediate-background + task-notification pattern and update `step2-implement.md` accordingly.
  - From dyn-timeout-tier-calibration-output.txt: Add Step 2 to the immediate-background set with a tier sized for external implementer wall-clock (observed runs suggest ≥10800000 ms), or explicitly document why Step 2 must remain foreground and keep harness auto-background there.
  - From dyn-background-resume-state-output.txt: Either background Step 2 dispatch with the same `<task-notification>` contract (and document Q/A redispatch resume), or narrow NEVER #8’s script list and issue #3997 acceptance criteria to explicitly exclude Step 2 with rationale.


### OOS_3: [OUT_OF_SCOPE] Design Step 2b drafter lacks immediate-background guidance
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-background-migration-parity-output.txt
- **Severity**: important
- **Concern**: The design Step 2b drafter has a long timeout but no immediate-background directive. Long drafting can still run foreground or depend on delayed harness auto-backgrounding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add Immediate-background required with run_in_background true on the design-step2b-drafter fence.
  - From cursor-specialist-testing-output.txt: Background drafter fence or document explicit exclusion with run-log evidence.
  - From dyn-background-migration-parity-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] CI does not pin immediate-background fence shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-background-resume-state-output.txt
- **Severity**: important
- **Concern**: Structural tests do not consistently assert the new immediate-background banners or `run_in_background` contracts. Prompt-only regressions from background to foreground may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-design-structure.sh or add a grep harness asserting immediate-background at Step 3/5/7a/8 (implement) and Step 3 (design).
  - From cursor-specialist-testing-output.txt: Extend harness to pin immediate-background wording alongside script invocation.
  - From dyn-background-resume-state-output.txt: Address the concern above.


