# Review Round 1

- Mode: `diff`
- 20 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 5b prepare wrapper lacks state-machine handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step5b-prepare.sh` stops after `file-design-oos.sh prepare`. It does not parse prepare status, emit `STEP5B_*` handoff KVs, log failures, or write `.completed/step-5b` on terminal continue paths. Step 5c can then run without durable OOS completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_10: Step 5c validator autofix handoff bypasses the wrapper invariant
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still directs the validator autofix success path to re-invoke `design-publish.sh` instead of `design-step5c.sh --skip-validate`. Autofix or override success can bypass wrapper guards or re-hit validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Structure harness no longer enforces key wrapper and fence contracts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` dropped broad contract enforcement without equivalent wrapper-level checks. Consecutive script-call fences, pause ordering, sentinel placement, postplan branching, publish guards, Gate B bypass, route pause integration, and Step 0 boundaries can regress while CI passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_12: Sketch collector uses fixed output paths instead of launched slots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step2a3-collect.sh` passes hard-coded sketch output paths rather than the paths for actually launched slots. Degraded or one-tool-down runs can wait on skipped external outputs or treat intentional omissions as failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Step 0 degraded wrapper requires DESIGN_TMPDIR before rehydration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step0-degraded.sh` validates `DESIGN_TMPDIR` before sourcing the session env. A fresh `/design` run can fail immediately after session setup because the new Bash process has not rehydrated the variable yet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Step 0 parsed issue and session state is not durably handed off
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 0 parse output is printed but not reliably persisted or reloaded by later wrappers. Issue binding, flags, tier selection, title, and body can be lost across phase wrappers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Validator autofix wrapper relies on prompt-side shell variables
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step-validator-autofix.sh` depends on shell variables that `SKILL.md` does not pass. Validator-defect paths can invoke autofix with an empty plan file or missing log/count arguments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Step 3 orchestrator fence harness was not retargeted to the wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` still mirrors the old inline handoff instead of invoking `design-step3-review.sh`. The wrapper’s KV, fallback, and normalization contract can drift undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Abort cleanup wrapper is missing or untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The planned `design-step0-abort-cleanup.sh` wrapper is absent or not wired into harness coverage. Abort cleanup behavior can regress without structural pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Step 6 prelude writes step-5d before cleanup eligibility is known
- **Reviewer(s)**: dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step6-prelude.sh` writes `.completed/step-5d` before validating `.design-step5c-status.env` and cleanup eligibility. A failed or ambiguous publish can still advance Step 5d completion state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_19: Step 1d.5 completion sentinel remains prompt-side
- **Reviewer(s)**: dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still instructs the orchestrator to write `.completed/step-1d.5` in prose after brainstorm work. The sentinel is not protected by a wrapper boundary, so pause/resume can miss completion state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_2: Step 5b annotate wrapper skips env, pause, status, and sentinel handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step5b-annotate.sh` can call `file-design-oos.sh annotate` without sourcing session env, validating `DESIGN_TMPDIR`, honoring `.pause-requested`, emitting status KVs, or writing `.completed/step-5b`. Pauses and incomplete OOS annotation can be lost before publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_20: Step 4 completion sentinel remains prompt-side
- **Reviewer(s)**: dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still writes `.completed/step-4` between Step 4 prose and Step 4b, while the Step 4 wrappers do not own that sentinel. Pause handling and wrapper-only sentinel ordering can be bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_21: Step 3b skip and architectural branches mutate files before pause-check
- **Reviewer(s)**: dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step3b-entry.sh` performs diagram cleanup or skipped-file mutations before checking pause in `--mode skip` and `--mode architectural`. A pause at the Step 3b boundary can leave partial mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_3: Step 5c can publish without Step 5b completion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step5c.sh` does not fail closed when `.completed/step-5b` is absent. Publish can mark an issue DESIGNED even when OOS prepare or annotation was skipped, interrupted, or incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_4: Step 5c publish and validator result contract is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-regression-coverage-gap-output.txt
- **Severity**: important
- **Concern**: `design-step5c.sh` does not emit or persist the full publish and validator KV contract. Validator rc 4 can fall through without a repair handoff, publish rc and validator keys can be unavailable to the orchestrator, and the sidecar omits cleanup-critical fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-regression-coverage-gap-output.txt: Address the concern above.


### FINDING_5: Step 6 cleanup validates publish status too late and fails open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `design-step6-cleanup.sh` writes `.completed/step-6` before validating `.design-step5c-status.env` and defaults missing `PUBLISH_OK` to success. Failed, missing, or malformed publish status can still mark cleanup complete or delete the recovery tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt, dyn-pause-sentinel-ordering-output.txt: Address the concern above.


### FINDING_6: Step 3 review wrapper does not emit normalized routing KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-step3-review.sh` normalizes loop status internally but does not print or persist the normalized `STEP3_REVIEW_LOOP_STATUS` and `LOOP_STATUS` handoff. Gate B, Step 3.5, and terminal-loop routing can receive empty or legacy statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Step 3 bypass and continuation paths still call the internal helper directly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still routes Gate B bypass and auto-continuation through `design-step3-state.sh` instead of wrapper-only entry points. Those paths can skip source, pause, sentinel, and terminal-loop protections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-regression-coverage-gap-output.txt: Address the concern above.


### FINDING_8: Postplan wrapper ignores site-specific snapshot behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-regression-coverage-gap-output.txt
- **Severity**: important
- **Concern**: `design-step2b-postplan.sh` parses `--site` but always passes `--snapshot-original` and can write Step 2b sentinels for non-Step-2b sites. Gate B and discussion round 2 can reseed drift baselines or take wrong postplan branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-regression-coverage-gap-output.txt: Address the concern above.


