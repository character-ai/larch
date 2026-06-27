# Review Round 1

- Mode: `diff`
- 3 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Stale counter and armed breaker state across sequential bg waits
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, codex-generalist, dyn-dyn-hook-correctness
- **Severity**: important
- **Concern**: Counter (`no-progress-turns.count`) and armed-flag (`no-progress-circuit-breaker-armed`) files persist in the shared session tmpdir when a bg wait ends or a new marker starts. A later wait in the same `$IMPLEMENT_TMPDIR` or `$DESIGN_TMPDIR` (e.g. `/implement` Step 5 after Step 3) can inherit stale breaker state and block on the first `UserPromptSubmit` even with zero no-progress turns in the new wait.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add reset_no_progress_state mirroring reset_probe_counter_for_step on sentinel present marker reap and new marker write; add sequential-wait harness test
  - From codex-specialist-correctness: Delete or reset the counter and armed flag when the marker becomes non-live, and initialize them fresh for each new live marker.
  - From cursor-specialist-edge-cases: Clear counter and armed files when marker is absent, step completed, or marker otherwise not live; mirror reset_probe_counter_for_step.
  - From codex-specialist-edge-cases: Remove both files on marker release or marker creation, and add a relaunch-in-same-tmpdir test.
  - From cursor-specialist-testing: Mirror hook-bg-poll-guard.sh cleanup: rm no-progress-turns.count and no-progress-circuit-breaker-armed on is_step_completed, kill -0 failure, and timeout expiry inside is_marker_live.
  - From codex-specialist-testing: Delete both files when a wait completes and when a new bg-wait marker is created, matching the reset pattern used for probe-clamp counters.
  - From codex-generalist: Scope `no-progress-turns.count` and `no-progress-circuit-breaker-armed` by marker instance, for example `STEP + PID + START_EPOCH`, or clear both files whenever a marker completes or a new marker is started. Add a regression that arms the breaker, removes/completes the first marker, starts a second marker in the same tmpdir, and asserts the second wait is not blocked until its own threshold is reached.
  - From dyn-dyn-hook-correctness: Scope counter/armed files by `STEP` (or marker generation), and clear them when a new `.bg-wait-active` is written or when `is_marker_live` transitions to not-live for that step. Add a harness case that arms during one step and asserts the next step's wait starts with a clean slate.


### FINDING_2: Step 3 completion omits step3-terminal-persisted-this-run sidecar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-hook-correctness
- **Severity**: important
- **Concern**: `is_step_completed` for `design-step3-review` treats a bare `.completed/step-3-terminal` as completion, but `hook-bg-poll-guard.sh` `marker_step_completed` also requires readable `.step3-terminal-persisted-this-run`. Sentinel without sidecar during an active wait can make the no-progress guard stop enforcing while probe-clamp remains active, or fail open on a stale sentinel while the wait is still live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Port sidecar gate from marker_step_completed or share one helper
  - From cursor-specialist-edge-cases: Align is_step_completed with marker_step_completed sentinel-plus-sidecar check.
  - From codex-specialist-edge-cases: Mirror the existing Step 3 sidecar predicate or reuse the shared helper, and add a stale-sentinel regression.
  - From codex-specialist-testing: Reuse the exact Step 3 release predicate from hook-bg-poll-guard.sh, including the sidecar check, before auto-disarming.
  - From dyn-dyn-hook-correctness: Port the Step 3 sidecar check from `marker_step_completed` into `is_step_completed`, and add a regression modeled on `test-hook-bg-poll-guard.sh` lines 407–411.


### FINDING_7: Armed breaker can block completion notification before sentinel exists
- **Reviewer(s)**: dyn-dyn-hook-correctness
- **Severity**: important
- **Concern**: Once armed, `UserPromptSubmit` blocks whenever any live marker remains and the armed file exists. Disarm relies on `is_step_completed` seeing the terminal sentinel first. For `/implement` and several `/design` paths, the sentinel is written in an EXIT trap after the background child finishes; notifications can arrive before the sentinel exists. In that window the hook can block the completion notification itself, contradicting the documented invariant that a genuine completion notification is never blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-correctness: Tie blocking to marker-scoped state that resets on real progress, or defer blocking until the same completion signals `hook-bg-poll-guard` uses (Step 3: sentinel **plus** sidecar). At minimum, clear the armed flag when the marker is removed or the background `PID` is no longer live, even if the sentinel is not yet on disk.


