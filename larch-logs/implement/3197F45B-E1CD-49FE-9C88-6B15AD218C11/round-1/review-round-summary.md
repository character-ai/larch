# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Shell Step 3 re-arm does not clear the new sidecars
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-hook-state
- **Severity**: major
- **Concern**: `skills/design/scripts/design-step3-review.sh` re-arms the Step 3 bg-wait marker without clearing `no-progress-stop-block-emitted` or the `bg-poll-guard-task-output-read.*.count` clamp sidecars. If a prior wait already tripped the breaker in the same `$DESIGN_TMPDIR`, the next Step 3 wait can inherit stale stop-emitted/clamp state, so the one-shot Stop direct-block and the expected classification-read recovery never fire again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-hook-state: Extend every Bash bg-wait marker writer (`design_bg_wait_marker_start`, `design-step3b-tail.sh:100`, `skills/implement/scripts/run-step-checks.sh:64`, `step-5-review.sh:170`, `step-6-entry.sh:49`, `step-8-ship.sh:103`) to remove `no-progress-stop-block-emitted` and glob-clear `bg-poll-guard-task-output-read.*.count` before writing `.bg-wait-active`, matching `_clear_no_progress_sidecars` / `_clear_probe_clamp_counter`.


### FINDING_2: Shell Step 4 tail re-arm carries stale sidecars forward
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `skills/design/scripts/design-step3b-tail.sh` arms the Step 4 tail wait without clearing the new stop-emitted and task-output-read clamp sidecars. That lets stale Step 3 breaker/clamp state leak into the Step 4 background wait in the same design session, so the direct Stop block can fail to reappear when the tail wait is retried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_7: Implement shell bg-wait writers still omit `no-progress-stop-block-emitted`
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: The implement shell bg-wait writers still clear only the older no-progress sidecars, not `no-progress-stop-block-emitted`. After one breaker fires, later waits in the same tmpdir can skip the direct Stop block entirely and repeat the notification loop instead of recovering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Step 3 shell re-arm still lacks a regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The plan-required re-arm reset test still covers only the Python bg-wait helpers, not the production `design-step3-review.sh` shell arm path. CI can therefore pass while stale sidecars persist across Step 3 shell re-arms in the same tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test-design-step3-review or hook harness case that re-arms via design_bg_wait_marker_start with a seeded stale sidecar


