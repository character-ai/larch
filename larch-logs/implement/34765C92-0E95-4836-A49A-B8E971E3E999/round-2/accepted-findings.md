### FINDING_1: Implement SKILL Step 2 prose misaligned with `run-step2-dispatch` (plan path, workflow, session-env)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 2 documentation still implies `run-step2-dispatch` derives `PLAN_FILE` and workflow from `session-env.sh`, while the launcher now uses `IMPLEMENT_TMPDIR/plan.txt` and a fixed HARD workflow. That mis-trains orchestrators on wrong env vs tmpdir sources for Step 2 debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_11: `skills/design/scripts/design-driver.sh` deprecated `CLASSIFY` action handled as passthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `ACTION=CLASSIFY` lines become `ACTION_PASSTHROUGH` instead of failing closed, so stale transcripts or automation can skip tier/router work silently without a failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: `scripts/run-step5-review.md` vs `scripts/run-step5-review.sh` empty-plan policy mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Markdown claims a non-empty plan requirement while the script only checks `-f`, so a zero-byte `plan.txt` can pass the launcher and confuse downstream review behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: `skills/implement/SKILL.md` Step 5 orchestrator prose vs fixed Step 5 round-cap behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Prose still suggests mirroring workflow mapping into `round_cap` while `run-step5-review.sh` uses a fixed base round cap (plus degraded inflation), risking future desync between prompt-side gates/banners and the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: `scripts/test-design-structure.sh` duplicate harness labels after CLASSIFY pin removal
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Duplicate `(14b)`-style labels make CI failures point at the wrong check id; distinct checks should have unique ids.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: `scripts/ship-pr.sh` `resolve_plan_file` drops valid conventional plan when `PLAN_FILE` is outside `IMPLEMENT_TMPDIR`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `resolve_plan_file` can return empty when `session-env` `PLAN_FILE` points outside `IMPLEMENT_TMPDIR` (legacy or hand-edited), even when `IMPLEMENT_TMPDIR/plan.txt` exists. PR-body / forwarding paths then lose issue-anchored plan context despite a valid conventional plan on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: `scripts/test-run-step5-review.sh` misleading SIMPLE vs HARD labels after unified Step 5
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Section titles and assert labels still refer to SIMPLE vs HARD workflows though `run-step5-review.sh` no longer branches on `POST_PLAN_WORKFLOW_PATH`, so duplicate cases can exercise the same path under misleading names—risking wrong “fixes,” false expectations, or masked regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: `scripts/test-write-run-params.sh` trivial-case JSON assertions weaker than main happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The trivial-case `jq` assertion omits `design_classification_source` (and `workflow_path`) compared to stricter primary checks, weakening the enum / field cutover guarantee for that preset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


