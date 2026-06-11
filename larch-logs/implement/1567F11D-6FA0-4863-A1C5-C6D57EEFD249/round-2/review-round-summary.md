# Review Round 2

- Mode: `diff`
- 15 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Collect wrapper builds sketch paths before session env rehydration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step2a3-collect.sh` derives launched-slot availability and output paths before sourcing the session env. Normal HARD runs can skip sketch collection with `COLLECT_STATUS=skipped-no-launched-slots` even when Codex or Cursor slots launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Expected cancel routes exit nonzero
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step0-route.sh` exits 1 for expected cancel routes such as title-filter and reentry-guard cancellations. That prevents final-summary emission and prompt-side abort handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Fence-shape harness does not require mandatory wrapper arguments
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-regex-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` allows wrapper fences with no flags. It does not require `--session-env-path` on wrappers or `--claude-pid "$PPID"` for Step 0 and Step 5c paths, so session rehydration regressions can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-regex-fidelity-output.txt: Address the concern above.


### FINDING_12: Structure harness lost wrapper contract, pause, sentinel, and branch coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-contract-migration-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` replaced deep structural guards with shallow substring checks. Pause-before-work, sentinel ordering, env-before-work, publish gating, route/pause smoke coverage, postplan arms, degraded-tool branches, Gate B bypass branches, and Step 3b routing can regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-contract-migration-output.txt: Address the concern above.


### FINDING_14: Gate B bypass and continuation entry wrappers lack SKILL fence templates
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate B bypass and continuation-entry scripts lack SKILL.md bash fence templates. The orchestrator may omit required wrapper calls or call them with wrong argv on legacy paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Postplan wrapper swallows validator and size exit states
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-step2b-postplan.sh` swallows rc `10`, `12`, and `13` without emitting `POSTPLAN_RC`. Validator failures or hard plan-size triggers can continue into Step 3 without the required prompt or repair path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Step 3 review wrapper drops allowlisted handoff keys
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-step3-review.sh` does not re-emit the full Step 3 result contract. Main-agent vote and re-tally branches can lose `SCOPE_ANCHOR_FILE`, `TALLY_PLAN_REVIEW_STATUS`, and round state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Step 3 review harnesses do not exercise the wrapper contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-contract-migration-output.txt
- **Severity**: important
- **Concern**: Step 3 tests grep prose or reimplement handoff logic instead of invoking `design-step3-review.sh` hermetically. Wrapper rc handling, launcher delegation, allowlist emission, and fallback behavior can drift from tested behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-contract-migration-output.txt: Address the concern above.


### FINDING_2: Step 4 completion sentinel is written by the wrong wrapper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-migration-output.txt
- **Severity**: important
- **Concern**: `design-step4.sh` writes `.completed/step-4`, while the migrated contract expects the Gate C or Step 4b boundary to own that sentinel. The harness also pins the wrong owner. A pause can mark Step 4 complete before required rejected-findings or Gate C work is no longer skippable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-migration-output.txt: Address the concern above.


### FINDING_20: Step 0 degraded wrapper does not emit degraded-decision contract
- **Reviewer(s)**: dyn-contract-migration-output.txt
- **Severity**: important
- **Concern**: `design-step0-degraded.sh` only rehydrates env and calls `degraded-tools-gate.sh`. It does not emit the planned degraded KVs or wrapper-level branches for `BOTH_DOWN`, `needs-degraded-decision`, or non-interactive auto-proceed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-migration-output.txt: Address the concern above.


### FINDING_3: Step 6 prelude writes `step-5d` without publish and cleanup eligibility
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step6-prelude.sh` writes `.completed/step-5d` after `PLAN_WRITE_OK` only. A failed publish can leave `step-5d` set while cleanup refuses to run, creating inconsistent resume state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Consecutive executable SKILL fence lint is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-regex-fidelity-output.txt, dyn-contract-migration-output.txt
- **Severity**: important
- **Concern**: The required `assert_no_consecutive_executable_script_call_fences` check is absent. `skills/design/SKILL.md` still has adjacent executable wrapper fences separated only by prose, so the D3 turn-reduction invariant is unenforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-harness-regression-output.txt, dyn-regex-fidelity-output.txt, dyn-contract-migration-output.txt: Address the concern above.


### FINDING_7: Step 0 route wrapper lacks issue binding and issue fetch setup
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step0-route.sh` does not bind numeric positional input to `ISSUE_NUMBER`, does not handle verbal issue creation or resume state, and does not fetch issue title/body/labels before calling `design-route.sh`. Normal `/design 123` can reach routing with empty issue data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Parsed argv sidecar writes unquoted shell values
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-step0-parse.sh` reserializes parsed argv values without shell quoting. Verbal input with spaces, newlines, `name=value`, or shell syntax can corrupt or execute during later `source`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Step 0 init loses parsed classification and router flags
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step0-init.sh` does not reload parsed state or derive `design_classification`. `/design --hard 123` can pass an empty classification or lose hard, brainstorm, and router semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


