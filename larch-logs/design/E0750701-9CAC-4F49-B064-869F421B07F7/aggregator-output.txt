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

### FINDING_3: Detached-marker age must be pinned to a fixed field
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Orphan-timeout logic is underspecified unless both Step 3 and Step 5 read a stable age field from the detached-marker KV file; relying on mtime or an incomplete key set can drift across rewrite/reattach and fire early or late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror Step 3 _step3_review_write_detached_marker fields in the Step 5 helper and document that Python reads DETACHED_AT_EPOCH first with mtime fallback in both plan_review.py and review_and_fix.py.
  - From Cursor-Pragmatic: Pin orphan checks to parse `DETACHED_AT_EPOCH=` from the detached-marker KV file (fallback to mtime only when the field is absent); require Step 5’s detached-marker writer to emit the same KV shape as Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`).
  - From Cursor-Requirements: Specify the Step 5 detached-marker write/read contract to match Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`), have Python orphan checks prefer `DETACHED_AT_EPOCH`, and add a harness assertion for the field.

### FINDING_4: Step 5 background launch needs stderr quarantine
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The background Step 5 launch path can leak reviewer stderr into the task output unless stderr is redirected separately, which risks breaking status parsing and reintroducing spurious notification churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add 2>"$IMPLEMENT_TMPDIR/implement-step5-loop-stderr.log" (or the config constant) to the fresh and reattach launch paths in step-5-review.sh and step-5-review.md.
  - From Cursor-Pragmatic: Add 2>"$IMPLEMENT_TMPDIR/implement-step5-loop-stderr.log" (or equivalent config constant) on the background launch for both fresh and reattach paths; document it in `step-5-review.md` and assert it in `test-step-5-review.sh`.

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

### FINDING_9: `.bg-wait-active` lifecycle needs explicit detach handling
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 5’s detach/reattach path needs explicit `.bg-wait-active` rules on both entry and cleanup, or stale markers can mislead the poll guard and block orchestrator reads after detach.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Mirror Step 3 ordering: write/refresh `.bg-wait-active` before any reattach wait and before fresh launch; in signal cleanup always `rm -f .bg-wait-active` before writing the detached marker or exiting; extend `test-step-5-review.sh` to assert detach leaves no terminal sentinel and no stale bg-wait marker.
