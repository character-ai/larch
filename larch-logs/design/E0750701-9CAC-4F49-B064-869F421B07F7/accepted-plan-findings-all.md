### FINDING_1: Step 5 signal-detach must re-enter, not fall through to preflight failure
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Signal Lifecycle Reviewer
- **Severity**: blocking
- **Concern**: After an external `SIGTERM`/`HUP`/`INT`, a Step 5 wrapper exit without `STEP5_REVIEW_STATUS` still falls into the preflight-failure branch and skips the detached-loop reattach path instead of re-entering `step-5-review.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit carve-out before the preflight-failure path: when a regular non-symlink `.step5-wrapper-detached` exists and `.completed/step-5-terminal` is absent, immediately re-run the same Step 5 launcher fence (background + notification wait) and do not set `STALL_STEP=5`; pair with a NEVER #8 note that absent `step-5-terminal` with a detached marker is expected detach, not hook inconsistency
  - From Codex-Arch: Change the planned SKILL.md update to branch on a regular non-symlink $IMPLEMENT_TMPDIR/.step5-wrapper-detached before the preflight-failure rule: relaunch step-5-review.sh with the same immediate-background wait to reattach and parse normalized stdout; only use the existing preflight failure path when no detached marker is present.
  - From Cursor-Pragmatic: Add Step 5 notification routing: when `.step5-wrapper-detached` exists and `step-5-terminal` is absent immediately re-invoke the same immediate-background `step-5-review.sh` fence in the same turn; carve this path out of the preflight-failure and absent-sentinel stall branches; require `step-5-terminal` before parsing `STEP5_REVIEW_STATUS` (mirror design Step 3 terminal-plus-envelope gate).
  - From Codex-Pragmatic: Add a distinct signal-detached wrapper stdout contract or equivalent durable route, and update Step 5 prose to treat that case as not terminal and re-enter the wrapper without polling or advancing to Step 18.
  - From Cursor-Requirements: Before the preflight-failure branch, add detach recovery: when `.step5-wrapper-detached` is a regular file or the wrapper exited 129/130/143 without the terminal sentinel, re-launch the same `step-5-review.sh` immediate-background fence and yield; do not route to Step 18. Update NEVER #8 carve-out so absent sentinel after those exits means re-invoke, not tool/hook failure handling
  - From Codex-Requirements: Add a Step 5 post-notification branch for missing `STEP5_REVIEW_STATUS` plus a regular non-symlink $IMPLEMENT_TMPDIR/.step5-wrapper-detached: re-run the same step-5-review.sh launcher once in immediate-background mode to reattach and normalize output; only use the preflight-failure path when no detached marker exists or reattach fails.
  - From Cursor-dyn-Signal Lifecycle Reviewer: Before the line-479 preflight-failure branch add a detach gate: when a regular `.step5-wrapper-detached` exists re-launch `step-5-review.sh` (same background fence) and wait again; only stall when the marker is absent


### FINDING_6: Step 5 reattach must be fail-closed and ordered before stale cleanup
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Signal Lifecycle Reviewer
- **Severity**: important
- **Concern**: The reattach entry sequence is not fail-closed: detached-marker detection must happen before stale-sentinel cleanup and fresh-launch setup, and failed reattach must not spawn another loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror design-step3-review.sh entry order: detect a regular non-symlink .step5-wrapper-detached first; on reattach success exit from normalize output; skip stale step-5-terminal removal and fresh background launch when the detached marker is present; only clear stale sentinels on non-reattach paths.
  - From Cursor-dyn-Signal Lifecycle Reviewer: Extend the Step 5 reattach bullets to: await-loop-identity then optional `session kill-background-processes`; run `review-and-fix normalize-status`; write `.completed/step-5-terminal` and remove `.bg-wait-active`; clear marker and identity sidecar only after normalize succeeds; add harness assertions for terminal sentinel and bg-wait clearance on reattach
  - From Cursor-dyn-Signal Lifecycle Reviewer: Add explicit Step 5 wrapper text: when reattach returns non-zero exit immediately without dispatching a fresh loop; extend `test-step-5-review.sh` to assert round count stays 1 after failed reattach like `skills/design/scripts/test-design-step3-review.sh:580`


### FINDING_7: Step 3 orphan-timeout normalization route is under-specified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Signal Lifecycle Reviewer
- **Severity**: important
- **Concern**: Step 3 orphan-timeout normalization is underspecified: the terminal status, `LOOP_STATUS`, and `NEXT_ACTION` mapping are not pinned, so the cap can route into the wrong phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When the orphan cap fires, persist and emit STEP3_REVIEW_LOOP_STATUS=panel-failed (or another _STEP3_SYNTHESIS_STATUSES member), LOOP_STATUS=panel-failed, and REASON=orphan-timeout; add a normalize test asserting NEXT_ACTION=step3b-bypass and no Gate B entry.
  - From Cursor-Requirements: Pin a terminal mapping in `plan_review_normalize.py`, e.g. `LOOP_STATUS=panel-failed` with `NEXT_ACTION=step3b-bypass` (or `final-summary:failed-judge-panel`), keep it out of `_STEP3_INTERACTIVE_STATUSES`, and extend `test-design-step3-review.sh` / `test_plan_review.py` to assert the normalized envelope
  - From Cursor-dyn-Signal Lifecycle Reviewer: Pin orphan handling to `STEP3_REVIEW_LOOP_STATUS=panel-failed` `LOOP_STATUS=panel-failed` `REASON=orphan-timeout` `NEXT_ACTION=step3b-bypass`; add the Python-level assertion called out in `test-design-step3-review.sh`


### FINDING_10: Step 5 signal cleanup must cover the launch-to-identity window
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-Signal Lifecycle Reviewer
- **Severity**: important
- **Concern**: A TERM/HUP/INT between Step 5 launch and identity publication can leave an untracked process group unless cleanup tears down the loop identity or publishes a validated detached marker first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Close the launch-to-identity window: on pre-identity signal or identity publication failure, either publish a validated identity plus detached marker or synchronously terminate the just-launched loop before exiting. Add a targeted harness case for signal between launch and identity-ready.
  - From Cursor-dyn-Signal Lifecycle Reviewer: Wire `review-and-fix teardown-loop-identity` into the Step 5 cleanup trap mirroring Step 3 including the detach-marker write-failure fallback; add a static guard in `scripts/test-implement-structure.sh`


### FINDING_11: Orphan timeout must pause while a wrapper is actively reattached
- **Reviewer(s)**: Codex-dyn-Signal Lifecycle Reviewer
- **Severity**: important
- **Concern**: The orphan cap can still fire while a wrapper is actively reattached, because the detached marker stays authoritative during the wait.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Signal Lifecycle Reviewer: Add a reattach handshake to the plan. After marker and identity validation, mark the loop as attached or disable the orphan marker under trap protection before await. On TERM/HUP/INT during that attached wait, re-write the detached marker so a true orphan still reaches the cap. Apply the same rule to Step 3 and Step 5.


### FINDING_1: Reattach cannot succeed while await still requires the detached marker
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The planned reattach flow removes the detached marker before `await-loop-identity`, but the await contract still treats that marker as required, so the Step 3/Step 5 reattach handshake cannot complete safely as written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the claim and await contracts consistent: either teach `await-loop-identity` to accept a claimed reattach state that disables the orphan cap without requiring the detached marker, or atomically rename the marker to a regular claim file and teach await and orphan checks about that state; update the Step 3 and Step 5 tests accordingly
  - From Cursor-Pragmatic: Add an explicit reattach mode: e.g. `await-loop-identity --reattach` (or a `.step5-reattach-active` sidecar) that skips the detached-marker prerequisite while the wrapper holds the trap-protected reattach window; teach orphan checks to pause when that sidecar exists; apply the same Step 3 await change when updating `design-step3-review.sh`.
  - From Codex-Pragmatic: Make the handshake and await contract consistent. Use a separate reattach-in-progress sidecar that does not count for the orphan cap, or update both Step 3 and Step 5 await to accept a validated reattach state after marker removal while still re-writing the detached marker on another signal.
  - From Cursor-Requirements: Drop the detached-marker presence gate from await during reattach (for example `--reattach` on both await verbs, or read PID/STDOUT from wrapper state instead), pause orphan checks while the marker is intentionally removed, and update the planned Step 3/5 process_identity tests so they no longer require a present marker on the reattach path.
  - From Codex-Requirements: Change the plan so await uses a validated reattach lease or a wrapper-prevalidated marker snapshot after marker removal, or keep a non-orphan-counted reattach marker that await accepts. Cover both Step 3 and Step 5 await tests.


### FINDING_2: Reattach failure needs a deterministic terminal state
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: After the detached marker is removed, a failed await or normalize step can leave the loop in an inconsistent state: either still running with no reattach entry/orphan cap, or stuck in a retry loop because the marker remains present and the orchestrator keeps re-invoking the same failed reattach.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: On reattach abort after marker removal, restore the detached marker from saved PID/STDOUT_FILE/SIGNAL or call teardown-loop-identity before exit. Apply the same rule to design-step3-review.sh _step3_review_reattach_detached_loop.
  - From Codex-Pragmatic: Define a terminal failure path for reattach failure. Emit a Step 5 stall or preflight envelope and terminal sentinel, or clear or rename the detached marker before exiting nonzero so the existing preflight-failure branch runs. Add a wrapper harness assertion for this path.


### FINDING_5: Trap registration order must precede reattach await
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan does not pin trap registration before the detached-marker check and `await-loop-identity`, so a reattach path could run without the signal-aware behavior that Step 3 already relies on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly: register EXIT plus TERM/HUP/INT traps before the detached-marker entry check and before any await-loop-identity call, matching Step 3 lines 536-541.


### FINDING_6: Step 5 tmpdir cleanup must be mandatory before normalize-status
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Reattach cleanup is only safe if vendor-process cleanup is mandatory and uses the implement tmpdir path; otherwise detached children can keep running after rejoin and race normalize-status or terminal-sentinel writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either extend `kill-background-processes` with a validated `--implement-tmpdir` path (mirroring implement tmpdir allowlisting) or add a dedicated implement-scoped cleanup helper; make Step 5 reattach run that cleanup mandatorily after successful await, matching Step 3’s `_step3_review_kill_tmpdir_processes` ordering before `normalize-status`.
  - From Cursor-Requirements: Make `python/cli.py session kill-background-processes --implement-tmpdir ...` mandatory on the Step 5 reattach path immediately before `review-and-fix normalize-status`, matching Step 3 ordering.


### FINDING_7: Pre-identity signal cleanup needs a sidecarless kill contract
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: If a signal arrives after Step 5 launches `review-and-fix` but before identity publication, the teardown path needs a way to validate and kill the just-launched process group without relying on a missing sidecar/identity file; otherwise the child can keep running untracked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify that Step 5 teardown handles the pre-identity pid by capturing and validating a stable pgid equals pid with the expected signature, then terminating it. Add the wrapper harness assertion that the fake pre-identity child is actually killed, not only that marker and terminal sentinel are absent.
  - From Codex-Requirements: Specify a sidecarless pre-identity teardown path that captures and validates the just-launched pid and pgid with expected signature `review-and-fix step5` before signaling, or block signal cleanup until identity publication can use the normal path. Make the pre-identity harness assert the fake child process group exits.


### FINDING_8: `normalize-status` needs explicit machine-stdout routing
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The new `review-and-fix normalize-status` entry point may inherit the quiet-init path and replay its envelope to a quiet log instead of stdout, which would break the Step 5 wrapper’s status handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add ("review-and-fix", "normalize-status") to _MACHINE_STDOUT_KEYS with a focused dispatch test, or explicitly specify that this entry point must not call quiet_init and must write its replay directly to stdout.


