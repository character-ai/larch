### FINDING_1: Step 3 identity capture must happen after the new process group exists
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Step 3 is still capturing/publishing loop identity too early and too close to the Bash launcher, so the retained pgid can differ from the child’s real process-group identity and teardown can validate or signal the wrong target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a pinned write path (e.g. `plan-review write-loop-identity --design-tmpdir … --pid "$_loop_pid"`) implemented in Python via `process_identity.py`, called immediately after `_loop_pid=$!`; keep Bash to launch, wait, trap dispatch, and sidecar unlink only.
  - From Codex-Arch: Require the sidecar writer and teardown helper to accept only `pgid == pid == _loop_pid` for Step 3. If that is not true yet, do not publish a sidecar or signal; rely on the existing tmpdir-scoped fallback.
  - From Codex-Innovation: Write the Step 3 sidecar from `python/larch/review/plan_review.py` immediately after `_apply_new_process_group()` succeeds, or make the recorder refuse to publish until the child identity shows `pgid == pid`; add that file to the plan.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Live timeout cleanup must stay off the validated persisted-teardown path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Live `Popen` timeout cleanup should keep using the existing live-handle escalation path; if it is routed through the same identity-validated persisted-teardown helper, normal timeout termination can fail or regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split process_identity into validated persisted teardown versus live-handle teardown that only logs targets then reuses existing SIGTERM/SIGKILL escalation. State explicitly in dispatch_leg that timeout cleanup uses the live path only.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Active-leg JSON publish has no atomic-write step
- **Description**: Active-leg JSON publish has no atomic-write step. Scenario: The plan replaces `.active-leg-pgid` with JSON but does not require `_write_text_atomic` (already used elsewhere in implement dispatch). A torn write is likely handled as malformed and unlinked without signaling, but concurrent `_run_leg_with_timeout` callers can still last-writer-win the single slot and leave the on-disk owner/pgid detached from a still-running leg until identity-validated cleanup runs.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_leg.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Fence could skip kill-active-leg when no active-leg artifact exists
- **Description**: [OUT_OF_SCOPE] Fence could skip kill-active-leg when no active-leg artifact exists. Scenario: Owner-token gating fixes cross-invocation friendly fire, but every .py larch-run exit still spawns a Python cleanup process even when no leg was published. That is extra churn on hot paths like checks and normalize-status.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:167-177
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Loop identity could be captured inside plan-review run at setsid
- **Description**: [OUT_OF_SCOPE] Loop identity could be captured inside plan-review run at setsid. Scenario: The Bash sidecar plus separate teardown verb adds two new artifacts and wrapper calls. The loop already enters plan-review run --new-process-group, which is the natural point to snapshot pid/pgid/start/cmd before any child work.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review.py:320-357
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Active-leg JSON publish has no atomic-write step
- **Description**: [OUT_OF_SCOPE] Active-leg JSON publish has no atomic-write step. Scenario: Concurrent leg publishers can leave a partial JSON file; owner-token consume paths fail closed, so this is hardening rather than a demonstrated kill vector.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_leg.py:86-93
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

