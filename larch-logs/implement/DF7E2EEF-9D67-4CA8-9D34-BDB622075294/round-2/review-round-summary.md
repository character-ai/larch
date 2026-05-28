# Review Round 2

- Mode: `diff`
- 10 accepted, 8 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Revise artifact allowlist does not match production filenames
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The revise artifact allowlist and tests/docs reference filenames such as `revise-prompt.md` and `patch.diff`, while `revise-plan-with-waterfall.sh` produces `prompt.txt` and candidate patch files. Snapshot/publish can delete or reject real revise artifacts, losing prompt/patch forensics and making tests pass against non-production basenames.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Legacy mode with env-only round cap lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test asserts legacy behavior when `LARCH_DESIGN_ROUND_CAP` is set but `--round-cap` is omitted, so argv/env gating could accidentally enable multi-round mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Step 3 LOOP_STATUS allowlist omits emit-plan-failed
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `emit-plan-failed` is emitted by the loop and appears in branch-matrix expectations, but Step 3 validation omits it from the `LOOP_STATUS` allowlist. A mid-loop `EMIT_PLAN` failure can be coerced to `panel-failed`, skipping documented Gate B manual recovery while the plan may be partially revised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: Multi-round docs omit plan-validator-defects routing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `plan-review.md` does not document the mid-loop `plan-validator-defects` exit and Step 3 handoff behavior, leaving operators without a normative reference for that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Loop status docs omit emit-plan-failed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.md` does not list `emit-plan-failed` in the documented status values or exit-code table, so docs disagree with a real terminal status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Post-apply pipeline skips planned dedup sweep
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_run_post_apply_pipeline` does not run the documented regex/best-effort dedup sweep or emit the expected breadcrumb before `EMIT_PLAN`, so auto-applied plans can carry duplicate lines or sections into later review rounds while docs say dedup runs in-loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Publish tests use synthetic revise patch filenames
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The publish happy path seeds `patch.diff`, which is not produced by the revise waterfall, so CI can miss real failures involving `prompt.txt` and candidate patch filenames.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Unit harness misses required multi-round scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-plan-review-loop.sh` covers only part of the planned multi-round acceptance matrix, leaving convergence streaks, cap hits, revise exit handling, dedup resets, severity defaults, OOS accumulation, and result-env assertions without targeted CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Multi-round integration harness misses acceptance scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-design-multi-round-integration.sh` omits planned SKILL Step 3 parsing, Gate B mode stubs, cross-entry cleanup, revision-failed behavior, and multi-round convergence scenarios, so those flows can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Post-apply validator and size failure paths lack harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test stubs exercise `invoke-plan-validator` or `check-plan-size` failures in the post-apply pipeline, so `plan-validator-defects` and `plan-size-trigger` routing can break undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


