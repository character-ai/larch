### FINDING_1: Step 0b still forwards removed `--manual-requested` and aborts fresh runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-drift-guard-output.txt, dyn-flag-schema-output.txt
- **Severity**: important
- **Concern**: Step 0-pre no longer binds `manual_requested`, but Step 0b still passes `--manual-requested "$manual_requested"` to `design-init-runparams.sh`. Fresh `ROUTE=proceed` runs pass an empty value, fail bool validation, and abort before `run-params.json` is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-drift-guard-output.txt: Address the concern above.
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_10: Router flag recovery harness still pins removed manual Gate B semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-flag-schema-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` still tests `manual_gate_b` flip/recovery and `--manual-requested`, so CI can preserve obsolete manual-mode behavior and mask incomplete removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_11: Prompt invariant harness not updated for manual removal / Gate B pins
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-prompt-template-invariants.sh` still needs updates for the removed manual surface and always-explicit Gate B contract, so prompt regressions may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_12: Step 2b drift sentinel is written before operator cancel path resolves
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The Step 2b rc=14 branch writes `.completed/step-2b` before the drift `AskUserQuestion`. If the operator cancels, resume can treat Step 2b as complete and skip re-emit/drift prompting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Step 3 orchestrator fence harness still allow-lists removed loop statuses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-review-loop-output.txt, dyn-drift-guard-output.txt
- **Severity**: latent
- **Concern**: `test-step3-orchestrator-fence.sh` still accepts removed statuses such as `converged`, `cap-hit`, `plan-size-trigger`, and `revision-failed`, while production now uses the reduced enum and normalizes unknowns to `panel-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-review-loop-output.txt: Address the concern above.
  - From dyn-drift-guard-output.txt: Address the concern above.


### FINDING_16: Partial `drift-baseline.env` parse can silently disable one drift axis
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: If one `BASELINE_*` key is corrupt/missing, `check-plan-size.sh` can leave that baseline at the current plan size, disabling that axis of the OR drift guard for the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-drift-guard-output.txt: Address the concern above.


### FINDING_18: Drift baseline can be seeded after plan expansion instead of initial Step 2b snapshot
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: Baseline seeding can occur only after validator success or after an override/fix path, allowing plan growth before `drift-baseline.env` exists and anchoring comparisons to an already-expanded plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-drift-guard-output.txt: Address the concern above.


### FINDING_2: `design-init-runparams.sh` still requires, forwards, and merges removed manual Gate B state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-flag-schema-output.txt
- **Severity**: important
- **Concern**: The init driver still documents/parses/validates `--manual-requested`, forwards it as `--manual-gate-b`, and jq-merges `manual_gate_b`, conflicting with the planned removal and always-explicit Gate B contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_20: `design-postplan-emit.md` omits drift exit/status contract
- **Reviewer(s)**: dyn-drift-guard-output.txt
- **Severity**: latent
- **Concern**: The contract doc lists exit codes only through 13 and omits drift result KVs, while the script emits drift KVs and exits 14.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-guard-output.txt: Address the concern above.


### FINDING_21: `check-plan-size.md` omits drift output and baseline semantics
- **Reviewer(s)**: dyn-drift-guard-output.txt
- **Severity**: latent
- **Concern**: The normative doc still describes only hard/soft gates and does not document drift KVs, write-once baseline behavior, zero-baseline handling, OR threshold semantics, or precedence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-guard-output.txt: Address the concern above.


### FINDING_23: `design-init-runparams.md` still documents removed manual flag
- **Reviewer(s)**: dyn-flag-schema-output.txt
- **Severity**: latent
- **Concern**: The script contract doc still lists the legacy manual request flag as required and mentions manual-only env refresh, conflicting with `flags.md` and the trimmed Gate B model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_24: Structure harness pins dead manual merge guard
- **Reviewer(s)**: dyn-flag-schema-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` still pins a jq recovery guard containing `"$MANUAL_REQUESTED" == true`, forcing retention of dead manual-merge logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_25: Skill flag signature lint fixture still expects `--manual-gate-b`
- **Reviewer(s)**: dyn-flag-schema-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lint-skill-md-flag-signature.sh` still expects `write-run-params.sh` signatures to include `--manual-gate-b`, which will block or regress cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_26: Gate-B-bypass sentinel enforcement is test-only / prompt-side
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: Bypass paths rely on prompt-side prose to write `step-3`, `step-3.5`, and `step-3.6`; production lacks a shared executable fence, and structure self-tests for these sentinels are stubbed. Pause/resume can re-enter Gate B on paths meant to skip it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.


### FINDING_27: `.step3-reentry` marker can survive pause/resume with stale routing
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: `.step3-reentry` is written prompt-side and not represented in pause-state step calculation. Pausing after marker creation but before Step 3 entry can resume to an earlier step with stale marker/sentinels still present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.


### FINDING_3: `write-run-params.sh` still emits removed `manual_gate_b`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flag-schema-output.txt
- **Severity**: important
- **Concern**: `scripts/write-run-params.sh` still accepts `--manual-gate-b` and writes `manual_gate_b` into schema v3 JSON while docs/tests assume the key was removed. New runs can persist stale manual Gate B state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-flag-schema-output.txt: Address the concern above.


### FINDING_4: Gate B documentation contradicts always-explicit approval
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-log-boundary-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still mixes always-explicit Gate B prompting with stale manual-mode / auto-apply wording. An orchestrator could skip `AskUserQuestion` or apply reviewer findings without explicit operator approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-log-boundary-output.txt: Address the concern above.


### FINDING_5: `approval-gates.md` contains a duplicate/malformed post-apply section
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: A bad merge left duplicate/malformed Shared post-apply pipeline text and a broken header, so reference readers see conflicting iteration guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: Stale `lib-plan-optional-trailers` integration map
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` still cites removed/currently-stale consumers such as `plan-review-loop` and `revise-plan-with-waterfall`, misleading maintainers after the single-pass change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: Tally helper failures can fall through instead of surfacing `tally-error`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-review-loop-output.txt
- **Severity**: important
- **Concern**: When `tally-plan-review.sh` exits nonzero without a stdout status KV, `plan-review-loop.sh` sets `TALLY_PLAN_REVIEW_STATUS=tally-error` but not `TALLY_PLAN_REVIEW_FATAL=true`. The terminal mapper can emit success/degraded statuses instead of `LOOP_STATUS=tally-error`, risking incorrect Gate B entry and skipped rollback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-review-loop-output.txt: Address the concern above.


