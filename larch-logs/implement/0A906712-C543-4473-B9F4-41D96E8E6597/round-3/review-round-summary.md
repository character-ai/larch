# Review Round 3

- Mode: `diff`
- 4 accepted, 9 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Ship-pr conflict recovery bypasses the step-8 immediate-background wrapper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/references/conflict-resolution.md` still routes post-conflict ship re-entry through direct foreground ship-pr commands instead of `step-8-ship.sh`, bypassing the immediate-background and task-notification contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update conflict-resolution.md lines 5 15 and 107 to re-invoke step-8-ship.sh with run_in_background true timeout 21600000 and task-notification wait matching ship-pr-exit-matrix.md.
  - From codex-specialist-correctness-output.txt: Update the reference to re-invoke skills/implement/scripts/step-8-ship.sh with run_in_background true, timeout 21600000, and a task-notification wait.
  - From codex-specialist-testing-output.txt: Update the reference to use skills/implement/scripts/step-8-ship.sh with run_in_background true, timeout 21600000, and task-notification wait; add a structure test forbidding direct foreground ship re-entry prose.


### FINDING_17: Gate B resume sites bypass the shared STEP3_RESUME_ROUND binding
- **Reviewer(s)**: dyn-cross-doc-resume-consistency-output.txt
- **Severity**: important
- **Concern**: Gate B idempotency and post-Gate B settled paths still use inline fallback expressions instead of the guarded `STEP3_RESUME_ROUND`, so they can resume with a different or unvalidated round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-resume-consistency-output.txt: Extend the `STEP3_RESUME_ROUND` binding rule to all Step 3 resume sites (including Gate B idempotency and post–Gate B settled paths). Replace every inline fallback with `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` and reference the immediate-background resume fence at lines 836–847.


### FINDING_18: Approval-gates post-apply pipeline can re-enter legacy Step 3 continuation
- **Reviewer(s)**: dyn-cross-doc-resume-consistency-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` steps 9-10 still route Gate B post-apply flow through the heuristic multi-round continuation path instead of branching loop-mode bail-outs back through the `design-step3-review.sh` resume fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-resume-consistency-output.txt: Branch steps 9–10 on whether `STEP3_REVIEW_LOOP_STATUS` is set. Loop mode: bind `STEP3_RESUME_ROUND`, write `.step3-round-$STEP3_RESUME_ROUND.phase` as `awaiting-continuation`, then resume through `design-step3-review.sh` per `SKILL.md`. Legacy single mode only: keep the heuristic continuation check and describe internal `run-step3-review.sh` behavior without implying a direct orchestrator launcher call.


### FINDING_19: Approval-gates zero-findings short-circuit ignores loop-mode resume
- **Reviewer(s)**: dyn-cross-doc-resume-consistency-output.txt
- **Severity**: important
- **Concern**: The zero-findings Gate B short-circuit unconditionally routes to heuristic continuation, conflicting with loop-mode phase-marker resume requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-resume-consistency-output.txt: Add an explicit branch: when `STEP3_REVIEW_LOOP_STATUS` is set, write the appropriate `.step3-round-$STEP3_RESUME_ROUND.phase` marker and resume through `design-step3-review.sh`; reserve the heuristic continuation check for unset loop envelope (`--mode single` harness callers).


