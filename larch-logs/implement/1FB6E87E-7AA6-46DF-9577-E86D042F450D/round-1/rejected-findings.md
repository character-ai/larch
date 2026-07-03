### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Step 3/5 probe resolver is not clone-local
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The unassigned Step 3/5 probe resolver is not filtering by clone locality tightly enough. A foreign live marker can make a valid local recovery probe deny, or let a nonmatching local step slip through the carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Filter no-assignment candidates through `bash_probe_target_dir_plausible "$dir" "$cwd_canon"` and bind to the single plausible matching marker for the current cwd; add a regression with a foreign matching Step 5 marker plus a local nonmatching Step 6 marker.
  - From codex-specialist-edge-cases: In the unassigned branch, count only markers that both match `expected_step` and pass `bash_probe_target_dir_plausible "$dir" "$cwd_canon"`, preserving the explicit `IMPLEMENT_TMPDIR=<abs>;` path for disambiguation. Then add a same-step foreign-marker regression test.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Implement symlink-sentinel denial is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The new implement harness does not exercise symlinked Step 3 or Step 5 sentinels. A future regression in the probe classifier could silently reopen forged-symlink probes on the recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add implement Step 3 and Step 5 harness cases mirroring the existing design/Step 8 symlink denial tests.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Clamp-denial copy still points to the wrong recovery path
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: important
- **Concern**: The clamp-denial message still tells the orchestrator to wait for another notification. That does not match the new implement contract after a genuine completion notification and can reintroduce the stall mode the change is trying to remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Either split deny copy for implement Step 3/5 clamps (directing to stall/failure handling, not another notification) or clear implement probe counters on wrapper launch so the post-genuine-notification recovery probe cannot hit the clamp on a fresh wait.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Late sentinel visibility can still false-stall
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: important
- **Concern**: The recovery contract still lacks a bounded follow-up read when the completion notification is genuine but the sentinel lands late. A same-session visibility lag can therefore false-stall instead of self-healing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Document and implement a bounded follow-up (for example, one additional output read on the next turn when the prior probe was absent but the completion notification was exit-code-bearing, without sleep loops or extra sentinel probes), or add a single guarded re-check in `marker_step_completed()` if the plan allows revisiting that decision.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

