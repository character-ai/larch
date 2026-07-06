### FINDING_1: Arm-time cleanup missing for no-progress stop sidecar
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Re-arming a `/design` wait in the same tmpdir can leave `no-progress-stop-block-emitted` behind, so later waits never emit a fresh Stop block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the existing arm-time `rm -f` lists in `design_bg_wait_marker_start`, `design-step3b-tail.sh`, `bg_wait.py`, and implement marker writers to delete `no-progress-stop-block-emitted`; add harness coverage for marker re-arm in the same tmpdir.
  - From Cursor-Innovation: List the marker arm sites explicitly (`design-step3-review.sh`, `design-step3b-tail.sh`, implement `run-step-checks.sh` / `step-5-review.sh` / `step-6-entry.sh` / `step-8-ship.sh`, `python/larch/implement/bg_wait.py`, and any Python Step 5c/final-summary marker writers) and clear the new sidecars there using the same glob/rm pattern already used for `bg-poll-guard-probe-denials.*.count`; add harness coverage that re-arm after a prior wait starts with empty clamp/breaker state.
  - From Cursor-Pragmatic: List every writer in `python/larch/lint/lint_bg_wait_writer_parity.py` under `### UPDATED:` and clear `no-progress-stop-block-emitted` alongside `no-progress-turns.count` and `no-progress-circuit-breaker-armed` at marker arm. Extend `python/larch/implement/bg_wait.py::_clear_no_progress_sidecars` and `python/larch/design/design_core.py::_bg_wait_marker_context` the same way. Pin writer parity in tests.
  - From Codex-Requirements: Add firm updates for each bg-wait marker arm path that reuses the tmpdir. Clear `no-progress-stop-block-emitted` where existing writers clear `no-progress-turns.count` and `no-progress-circuit-breaker-armed`, and clear the new design task-output Read clamp state in `design_bg_wait_marker_start`, `design_step4_tail_marker`, and `_bg_wait_marker_context` before marker write. Cover at least one real marker-writer arm-time reset, not only hook-local helper state.

### FINDING_2: Task-output Read clamp needs arm-time reset
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Re-arming a `/design` wait in the same tmpdir can leave task-output Read clamp sidecars behind, so the first legitimate post-rearm classification Read can be denied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A new wait in the same tmpdir can inherit a saturated clamp and deny the first legitimate classification Read after real completion. Mirror the probe-clamp arm pattern: clear task-output Read sidecars in `design_bg_wait_marker_start`, `design-step3b-tail.sh`, `_bg_wait_marker_context`, and implement arm helpers; add an arm-time re-use test in `scripts/test-hook-bg-poll-guard.sh`.
  - From Cursor-Pragmatic: Add arm-time clearing in the same bg-wait writers (glob the new per-task sidecars under the marker dir) and a `test-hook-bg-poll-guard.sh` case that re-arms a marker in the same tmpdir and expects the first classification Read allowed.

### FINDING_3: PostToolUse reminder leaks on second classification Read
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `handle_task_output_poll` can still emit `additionalContext` on the second Read of the same `tasks/*.output` within 600s, so the second lawful classification Read can surface prose despite the silent-yield contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Exempt lawful `/design` classification Reads while a live same-clone `design-step*` marker exists (or suppress task-output reminders when `hook-bg-poll-guard.sh` would allow/deny under the new clamp), and pin the behavior in `test-hook-anti-read-poll.sh`.
  - From Cursor-Innovation: Add `### UPDATED: scripts/hook-anti-read-poll.sh` (and `scripts/test-hook-anti-read-poll.sh`) to skip task-output poll reminders while a live same-clone `design-step*` `.bg-wait-active` marker exists, mirroring the new clamp scope; alternatively lower the clamp default to 1 so the second Read is denied before PostToolUse runs.
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/hook-anti-read-poll.sh` to suppress task-output PostToolUse reminders while a same-clone live `design-step*` `.bg-wait-active` marker exists (or skip `handle_task_output_poll` for Read-tool `tasks/*.output` paths in that state). Update `scripts/test-hook-anti-read-poll.sh` expectations and make `scripts/test-hook-anti-read-poll.sh` a firm plan file, not `MAY_UPDATE`.

### FINDING_4: Multiple live markers make clamp ownership ambiguous
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: When more than one live same-clone design-step marker exists, the clamp may attach to the wrong marker or wrong step context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When more than one eligible live dir matches, fail open or deterministically select the dir whose `.bg-wait-active` STEP matches the tightest wait class (prefer the marker whose `tasks/<id>.output` Read is being classified); document and test the multi-marker case instead of silently picking the first `live_dirs_file` row.

### FINDING_5: Clamp must apply before the path gate
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The clamp has to run before the `path_under_dir` gate, or absolute `tasks/*.output` Reads bypass it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly in the `hook-bg-poll-guard.sh` plan step that the clamp is a top-level Read branch on tail `tasks/[A-Za-z0-9._-]+.output` when any live same-clone `design-step*` marker exists, before the `path_under_dir` loop, and add a harness Read whose path is outside the tmpdir tree.
