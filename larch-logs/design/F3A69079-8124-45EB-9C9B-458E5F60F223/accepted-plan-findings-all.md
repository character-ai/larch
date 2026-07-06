### FINDING_1: Silent-yield contract is not honored after denied classification Reads
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Repeated unchanged or whitespace-only `tasks/*.output` classification Reads need to collapse into silent yield, but the live-task reminder and denial path can still surface prose or retries on later notification turns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a narrow carve-out (mirror live same-clone `.bg-wait-active` discovery): suppress task-output poll reminders while an immediate-background marker is live, or raise the task-output threshold above the Read-clamp deny point during that window; pin the behavior in `scripts/test-hook-anti-read-poll.sh`.
  - From Cursor-Innovation: Add to design-background-wait.md and skills/design/SKILL.md: when PreToolUse denies tasks/*.output Read as unchanged or whitespace-only under a live wait, treat it as silent yield; do not retry Read, parse, or emit status prose in that turn
  - From Cursor-Pragmatic: Add explicit contract: when the bg-poll guard denies a tasks/*.output Read for unchanged/empty clamp, treat it as the same silent yield (zero prose, zero further tools, no retry)
  - From Cursor-Requirements: Add one sentence: after threshold, a denied classification Read of tasks/*.output means immediate silent yield (zero prose, zero further tools); do not retry Read until output changes or the marker releases


### FINDING_3: Task-output Read clamp sidecars need both arm-time cleanup and release hooks
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Hook Lifecycle, Codex-dyn-Hook Lifecycle
- **Severity**: major
- **Concern**: The new per-task Read clamp can survive across waits unless it is cleared both when a bg-wait marker is armed and when that marker later releases, times out, or dies. Without symmetric cleanup, stale clamp state can deny the first legitimate post-completion Read or leak into the next wait in the same tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `hook-bg-poll-guard.sh`, add a `reset_task_output_read_state` helper and invoke it from the same `marker_is_live` release branches that already call `reset_probe_counter_for_step` (terminal sentinel, dead PID, timeout, marker removal).
  - From Cursor-Innovation: Add ### UPDATED entries for design_core._bg_wait_marker_context, bg_wait._clear_no_progress_sidecars, and every bg-wait writer in lint_bg_wait_writer_parity WRITERS to clear no-progress-stop-block-emitted plus task-output Read clamp files at marker arm, mirroring existing probe-denial clears in design_bg_wait_marker_start
  - From Cursor-Pragmatic: Extend `reset_probe_counter_for_step` (or a sibling reset) to delete per-task task-output Read clamp files and invoke it from every marker_is_live release path that already calls `reset_probe_counter_for_step`
  - From Cursor-Requirements: Add no-progress-stop-block-emitted to every existing pre-arm no-progress reset (design_bg_wait_marker_start, design-step3b-tail, step-5/6/8 wrappers, run-step-checks.sh, bg_wait._clear_no_progress_sidecars) and glob-clear new task-output Read clamp sidecars the same way probe-denials.*.count is cleared
  - From Codex-Requirements: Add `no-progress-stop-block-emitted` to every existing no-progress sidecar cleanup at marker start, including design and implement shell marker writers and `python/larch/implement/bg_wait.py`; extend the focused hook tests to cover relaunch after a Stop block.
  - From Cursor-dyn-Hook Lifecycle: Wire a reset_task_output_read_state(dir, step) helper into the same marker_is_live branches that call reset_probe_counter_for_step (sentinel present, kill -0 failure, timeout) and document the sidecar basename in hook-bg-poll-guard.md.
  - From Cursor-dyn-Hook Lifecycle: Add parallel tests: dead PID removes marker and clears the task-output Read sidecar; aged marker timeout does the same, matching the probe-clamp regression pattern.
  - From Codex-dyn-Hook Lifecycle: Add the new no-progress-stop-block-emitted file and the task-output Read sidecar pattern to every bg-wait marker start/reset helper that already clears no-progress or probe sidecars, including design shell wrappers, implement shell wrappers, and Python bg-wait helpers; add same-tmpdir relaunch coverage with stale sidecars present.


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-Hook Lifecycle
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-bg-poll-guard.sh:1121-1142
- **Concern**: [SCOPE-REDUCTION] Read clamp is global while docs scope it to /design. Scenario: Plan text limits the clamp to /design notification recovery, but implementation binds to any live same-clone marker (including implement-step3-checks and implement-step5-review). That adds hook surface and can deny implement diagnostic Reads without an implement silent-yield contract.
- **Proposed resolution**: Restrict the clamp to design STEP values (or design-* marker steps only) unless implement classification Reads are explicitly in scope; keep implement on probe-clamp plus notification-only prose.


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


