### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:147-154
- **Concern**: Arm-time cleanup for `no-progress-stop-block-emitted` is missing from bg-wait marker writers. Scenario: The plan adds `no-progress-stop-block-emitted` and calls arm-time reset critical in Failure modes, but only extends `reset_no_progress_state` inside `hook-no-progress-guard.sh`. Today arm-time clears live in `design_bg_wait_marker_start` and `_clear_no_progress_sidecars` (`python/larch/implement/bg_wait.py:11-14`, plus implement shell wrappers). Reusing a tmpdir after a prior Stop direct-block leaves the emitted sidecar in place, so later waits never emit a new Stop block even when stuck.
- **Proposed resolution**: Extend the existing arm-time `rm -f` lists in `design_bg_wait_marker_start`, `design-step3b-tail.sh`, `bg_wait.py`, and implement marker writers to delete `no-progress-stop-block-emitted`; add harness coverage for marker re-arm in the same tmpdir.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:147-154 / python/larch/design/design_core.py:167-169
- **Concern**: Task-output Read clamp lacks the symmetric arm-time cleanup FINDING_3 required. Scenario: The edge case requires stale task-output Read sidecars to clear at arm time. Release-path `reset_task_output_read_state` in `hook-bg-poll-guard.sh` is not enough. `design_bg_wait_marker_start` already clears probe-clamp counters per step at arm (lines 150-153), and `_bg_wait_marker_context` clears probe clamps at arm (line 169); the plan omits the parallel arm-time wipe for new task-output Read state.
- **Proposed resolution**: A new wait in the same tmpdir can inherit a saturated clamp and deny the first legitimate classification Read after real completion. Mirror the probe-clamp arm pattern: clear task-output Read sidecars in `design_bg_wait_marker_start`, `design-step3b-tail.sh`, `_bg_wait_marker_context`, and implement arm helpers; add an arm-time re-use test in `scripts/test-hook-bg-poll-guard.sh`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-anti-read-poll.sh:346-348
- **Concern**: PostToolUse task-output reminders still break zero-prose silent yield (accepted FINDING_1 incomplete). Scenario: The plan reinforces zero prose after classification Reads but only MAY_UPDATES `test-hook-anti-read-poll.sh`. `handle_task_output_poll` still emits `additionalContext` on the 2nd Read of the same `tasks/*.output` within 600s. With the planned read-clamp default of 2, turns 1-2 still perform successful classification Reads, so turn 2 can surface hook reminder text during a spurious-notification loop.
- **Proposed resolution**: Exempt lawful `/design` classification Reads while a live same-clone `design-step*` marker exists (or suppress task-output reminders when `hook-bg-poll-guard.sh` would allow/deny under the new clamp), and pin the behavior in `test-hook-anti-read-poll.sh`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:303-348
- **Concern**: PostToolUse task-output poll reminder still fires on the second mandated classification Read. Scenario: The plan's bg-poll clamp defaults to allowing two unchanged `tasks/*.output` Reads before denying the third, but `hook-anti-read-poll.sh` emits `additionalContext` on the second Read of the same task output within 600s. On spurious notification turn 2 the classification Read still succeeds and the PostToolUse hook injects a poll reminder, which can drive orchestrator prose and violates Fix 4 silent-yield even when PreToolUse has not denied yet.
- **Proposed resolution**: Add `### UPDATED: scripts/hook-anti-read-poll.sh` (and `scripts/test-hook-anti-read-poll.sh`) to skip task-output poll reminders while a live same-clone `design-step*` `.bg-wait-active` marker exists, mirroring the new clamp scope; alternatively lower the clamp default to 1 so the second Read is denied before PostToolUse runs.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:147-170
- **Concern**: Arm-time sidecar cleanup is specified but marker writers are not in the change set. Scenario: The plan's edge case and failure mode require clearing `no-progress-stop-block-emitted` and new task-output Read sidecars when a wait is re-armed in the same tmpdir, but only extends hook-side `reset_*` on release. Production arming happens in `design_bg_wait_marker_start`, `design_step4_tail_marker`, implement wrappers, and `python/larch/implement/bg_wait.py`, which today rm only `no-progress-turns.count` / `no-progress-circuit-breaker-armed` (and selective probe counters). Without matching arm-time deletes, a second Step 3 wait can inherit a tripped `no-progress-stop-block-emitted` (breaker never blocks again) or stale Read-clamp state (wrong deny on the first post-rearm classification Read).
- **Proposed resolution**: List the marker arm sites explicitly (`design-step3-review.sh`, `design-step3b-tail.sh`, implement `run-step-checks.sh` / `step-5-review.sh` / `step-6-entry.sh` / `step-8-ship.sh`, `python/larch/implement/bg_wait.py`, and any Python Step 5c/final-summary marker writers) and clear the new sidecars there using the same glob/rm pattern already used for `bg-poll-guard-probe-denials.*.count`; add harness coverage that re-arm after a prior wait starts with empty clamp/breaker state.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-bg-poll-guard.sh:1121-1143
- **Concern**: Read-clamp binding when multiple live design-step markers exist is still undefined. Scenario: The plan binds clamp state to retained live same-clone design-step marker dirs but does not say which dir owns state when two such markers are live (e.g., overlapping tmpdir misuse or a stale marker plus a new wait). Clamp telemetry could attach to the wrong marker, leaving another wait unclamped or denying Reads against the wrong STEP context.
- **Proposed resolution**: When more than one eligible live dir matches, fail open or deterministically select the dir whose `.bg-wait-active` STEP matches the tightest wait class (prefer the marker whose `tasks/<id>.output` Read is being classified); document and test the multi-marker case instead of silently picking the first `live_dirs_file` row.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:303-348
- **Concern**: PostToolUse task-output reminders still fire on lawful /design classification Reads (prior FINDING_1 fix incomplete). Scenario: `handle_task_output_poll` emits `additionalContext` on the 2nd Read of the same `tasks/<id>.output` within 600s. The new PreToolUse clamp allows two unchanged Reads before deny, so turn 2 still gets a system reminder after a successful classification Read. That violates the reinforced silent-yield contract (zero prose after classification) and can pull the orchestrator back into visible narration on spurious-notification turns.
- **Proposed resolution**: Add `### UPDATED: scripts/hook-anti-read-poll.sh` to suppress task-output PostToolUse reminders while a same-clone live `design-step*` `.bg-wait-active` marker exists (or skip `handle_task_output_poll` for Read-tool `tasks/*.output` paths in that state). Update `scripts/test-hook-anti-read-poll.sh` expectations and make `scripts/test-hook-anti-read-poll.sh` a firm plan file, not `MAY_UPDATE`.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:149,python/larch/design/design_core.py:163-169,python/larch/implement/bg_wait.py:11-14
- **Concern**: `no-progress-stop-block-emitted` arm-time reset is not wired into bg-wait marker writers. Scenario: The plan adds the sidecar and extends `reset_no_progress_state`, but arm-time clearing today lives in the eight bg-wait writers (shell `rm -f` lists and Python `_clear_no_progress_sidecars` / `_bg_wait_marker_context`). None are listed for update. Failure mode says stale `no-progress-stop-block-emitted` prevents a later block in the same tmpdir; `design_core.py` already does not clear existing no-progress files at arm.
- **Proposed resolution**: List every writer in `python/larch/lint/lint_bg_wait_writer_parity.py` under `### UPDATED:` and clear `no-progress-stop-block-emitted` alongside `no-progress-turns.count` and `no-progress-circuit-breaker-armed` at marker arm. Extend `python/larch/implement/bg_wait.py::_clear_no_progress_sidecars` and `python/larch/design/design_core.py::_bg_wait_marker_context` the same way. Pin writer parity in tests.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-bg-poll-guard.sh:256-275,skills/design/scripts/design-step3-review.sh:147-154,python/larch/design/design_core.py:147-169
- **Concern**: Task-output Read clamp lacks symmetric arm-time cleanup (prior FINDING_3 fix incomplete). Scenario: Edge cases require stale task-output Read sidecars to clear at arm time. The plan only adds `reset_task_output_read_state` on marker release inside `marker_is_live`, mirroring `reset_probe_counter_for_step`. Probe-clamp counters are already cleared at arm in `design_bg_wait_marker_start` and `_clear_probe_clamp_counter`; task-output clamp state has no equivalent writer hook or harness test. A reused tmpdir can deny the first legitimate post-rearm classification Read.
- **Proposed resolution**: Add arm-time clearing in the same bg-wait writers (glob the new per-task sidecars under the marker dir) and a `test-hook-bg-poll-guard.sh` case that re-arms a marker in the same tmpdir and expects the first classification Read allowed.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-bg-poll-guard.sh:1121-1142
- **Concern**: Classification Read clamp must sit outside the `path_under_dir` gate. Scenario: Classification Reads use absolute `tasks/<id>.output` paths outside `$DESIGN_TMPDIR`. Current Read handling only enters `deny_if_needed` when `path_under_dir` or known-result basename matches; `tasks/*.output` otherwise exits allow. If the clamp is inserted only inside that loop, unchanged-output Reads stay unlimited and the new breaker never fires.
- **Proposed resolution**: State explicitly in the `hook-bg-poll-guard.sh` plan step that the clamp is a top-level Read branch on tail `tasks/[A-Za-z0-9._-]+.output` when any live same-clone `design-step*` marker exists, before the `path_under_dir` loop, and add a harness Read whose path is outside the tmpdir tree.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:147-169; skills/design/scripts/design-step3b-tail.sh:97-110; python/larch/design/design_core.py:162-184
- **Concern**: Prior accepted sidecar-cleanup fix is incomplete: the plan requires arm-time cleanup, but does not add the marker-writer paths that can actually clear new `no-progress-stop-block-emitted` and task-output Read clamp sidecars before a reused tmpdir writes `.bg-wait-active`.. Scenario: If a wait hits the Stop block or Read clamp, then the wrapper removes `.bg-wait-active` before a hook sees a release path, stale sidecars can survive into the next `/design` wait in the same `DESIGN_TMPDIR`. The next wait can suppress the one-shot Stop block or deny the first classification Read before its threshold.
- **Proposed resolution**: Add firm updates for each bg-wait marker arm path that reuses the tmpdir. Clear `no-progress-stop-block-emitted` where existing writers clear `no-progress-turns.count` and `no-progress-circuit-breaker-armed`, and clear the new design task-output Read clamp state in `design_bg_wait_marker_start`, `design_step4_tail_marker`, and `_bg_wait_marker_context` before marker write. Cover at least one real marker-writer arm-time reset, not only hook-local helper state.
