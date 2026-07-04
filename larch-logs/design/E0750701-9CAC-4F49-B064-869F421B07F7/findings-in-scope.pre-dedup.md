### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:34,67,105-106; python/larch/core/process_identity.py:451-453
- **Concern**: Reattach handshake removes the marker that await still requires. Scenario: On Step 3 or Step 5 continuation, the wrapper removes `.step*-wrapper-detached` before calling `await-loop-identity`, but the await contract still requires the detached marker to exist; await returns non-zero, so the wrapper exits instead of normalizing the captured envelope and writing the terminal sentinel
- **Proposed resolution**: Make the claim and await contracts consistent: either teach `await-loop-identity` to accept a claimed reattach state that disables the orphan cap without requiring the detached marker, or atomically rename the marker to a regular claim file and teach await and orphan checks about that state; update the Step 3 and Step 5 tests accordingly



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh:reattach-handshake
- **Concern**: Finding 11 removes the detached marker before await but does not define non-signal failure recovery. Scenario: After marker removal, await-loop-identity or normalize-status can fail without TERM/HUP/INT. The loop may still be running, but no detached marker means no reattach entry and no orphan cap (plan says absent marker means attached). Vendor spend can continue untracked.
- **Proposed resolution**: On reattach abort after marker removal, restore the detached marker from saved PID/STDOUT_FILE/SIGNAL or call teardown-loop-identity before exit. Apply the same rule to design-step3-review.sh _step3_review_reattach_detached_loop.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh:detached-marker-write
- **Concern**: Step 5 detached-marker KV shape is not pinned for orphan age reads. Scenario: Plan says orphan checks read marker age but does not require DETACHED_AT_EPOCH in the Step 5 write helper. Step 3 already writes PID/SIGNAL/STDOUT_FILE/DETACHED_AT_EPOCH. Drift breaks orphan-timeout in review_and_fix.py.
- **Proposed resolution**: Mirror Step 3 _step3_review_write_detached_marker fields in the Step 5 helper and document that Python reads DETACHED_AT_EPOCH first with mtime fallback in both plan_review.py and review_and_fix.py.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh:background-launch
- **Concern**: Step 5 loop stderr redirect is only in Approach, not the firm wrapper contract. Scenario: Step 3 backgrounds plan-review with stdout and stderr redirected. Step 5 will background review-and-fix with stdout capture only in the UPDATED section. Reviewer stderr can land in the immediate-background task output and break STEP5_REVIEW_STATUS parsing.
- **Proposed resolution**: Add 2>"$IMPLEMENT_TMPDIR/implement-step5-loop-stderr.log" (or the config constant) to the fresh and reattach launch paths in step-5-review.sh and step-5-review.md.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh:trap-order
- **Concern**: TERM/HUP/INT trap registration order is unspecified relative to reattach entry. Scenario: design-step3-review.sh arms traps before _step3_review_reattach_detached_loop. The Step 5 plan lists traps and reattach separately without ordering. Traps installed only after a failed reattach or only before fresh launch would leave the reattach await path without the Finding 11 rewrite-on-signal behavior.
- **Proposed resolution**: State explicitly: register EXIT plus TERM/HUP/INT traps before the detached-marker entry check and before any await-loop-identity call, matching Step 3 lines 536-541.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/core/process_identity.py
- **Concern**: Finding 11 reattach handshake conflicts with await-loop-identity detached-marker gate. Scenario: The plan removes `.step5-wrapper-detached` / `.step3-wrapper-detached` before `await-loop-identity`, but still requires a regular detached marker inside `await_step5_loop_identity_main` (and Step 3 `await_loop_identity_main` already hard-fails without one). Reattach always fails, or the handshake is skipped and orphan-timeout can fire during the wait.
- **Proposed resolution**: Add an explicit reattach mode: e.g. `await-loop-identity --reattach` (or a `.step5-reattach-active` sidecar) that skips the detached-marker prerequisite while the wrapper holds the trap-protected reattach window; teach orphan checks to pause when that sidecar exists; apply the same Step 3 await change when updating `design-step3-review.sh`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py
- **Concern**: Step 5 reattach cites nonexistent `session kill-background-processes --implement-tmpdir`. Scenario: `kill_background_processes_main` only accepts `--design-tmpdir`, validates `claude-design-*`, and errors on implement tmpdirs. The planned optional reattach cleanup call always fails, leaving detached vendor children running after rejoin (the round-1 concern FINDING_2 targeted).
- **Proposed resolution**: Either extend `kill-background-processes` with a validated `--implement-tmpdir` path (mirroring implement tmpdir allowlisting) or add a dedicated implement-scoped cleanup helper; make Step 5 reattach run that cleanup mandatorily after successful await, matching Step 3’s `_step3_review_kill_tmpdir_processes` ordering before `normalize-status`.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py
- **Concern**: Orphan-timeout age source is unspecified for Step 3 and Step 5. Scenario: The plan says loops should read detached-marker age at boundaries but does not pin the field. Step 3’s shell writer already emits `DETACHED_AT_EPOCH`; using marker mtime alone drifts across rewrite/reattach and can fire early/late relative to the 7200s cap.
- **Proposed resolution**: Pin orphan checks to parse `DETACHED_AT_EPOCH=` from the detached-marker KV file (fallback to mtime only when the field is absent); require Step 5’s detached-marker writer to emit the same KV shape as Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`).



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh
- **Concern**: Background Step 5 launch omits dedicated stderr quarantine. Scenario: The Approach says capture stdout and stderr separately, but the `step-5-review.sh` firm section only describes stdout capture. Step 3 redirects loop stderr to `plan-review-loop-stderr.log` to keep bash/job-control noise out of task output (#5240). A background `review-and-fix` loop without the same redirect can reintroduce spurious `<task-notification>` churn on detach/reattach.
- **Proposed resolution**: Add `2>"$IMPLEMENT_TMPDIR/implement-step5-loop-stderr.log"` (or equivalent config constant) on the background launch for both fresh and reattach paths; document it in `step-5-review.md` and assert it in `test-step-5-review.sh`.



### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/process_identity.py:451-453
- **Concern**: The reattach handshake removes the detached marker before await, but the await contract still requires that marker. Scenario: The plan removes .step5-wrapper-detached and .step3-wrapper-detached before await to pause the orphan cap, while process_identity.py rejects await when the detached marker is absent and the plan also says Step 5 await requires the marker. A detached Step 3 or Step 5 loop would fail reattach immediately instead of recovering.
- **Proposed resolution**: Make the handshake and await contract consistent. Use a separate reattach-in-progress sidecar that does not count for the orphan cap, or update both Step 3 and Step 5 await to accept a validated reattach state after marker removal while still re-writing the detached marker on another signal.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/process_identity.py:477-480
- **Concern**: Pre-identity Step 5 signal cleanup still lacks a sidecar-free kill contract. Scenario: The plan says a signal before identity publication calls teardown-loop-identity to terminate the just-launched process group, but the existing teardown shape returns without a sidecar. If the Step 5 wrapper is killed between launch and identity write, the child process group can keep running untracked.
- **Proposed resolution**: Specify that Step 5 teardown handles the pre-identity pid by capturing and validating a stable pgid equals pid with the expected signature, then terminating it. Add the wrapper harness assertion that the fake pre-identity child is actually killed, not only that marker and terminal sentinel are absent.



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:479
- **Concern**: Failed Step 5 reattach can be re-invoked forever because the plan keeps the detached marker after await or normalize failure. Scenario: The plan adds the detached-marker carve-out before the preflight-failure branch, but also says the wrapper clears the marker only after successful normalize and exits on await or normalize failure. If the loop exits without a STEP5_REVIEW_STATUS envelope, the next notification still sees marker present and terminal absent, so the orchestrator re-runs the same failed reattach instead of routing to Step 18.
- **Proposed resolution**: Define a terminal failure path for reattach failure. Emit a Step 5 stall or preflight envelope and terminal sentinel, or clear or rename the detached marker before exiting nonzero so the existing preflight-failure branch runs. Add a wrapper harness assertion for this path.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/cli.py:684-691
- **Concern**: New review-and-fix normalize-status stdout path is not planned for machine-stdout routing. Scenario: Step 5 reattach depends on python/cli.py review-and-fix normalize-status replaying STEP5_REVIEW_STATUS to wrapper stdout. The plan adds registry assertions only. If the new review_and_fix entry follows the file's existing quiet_init pattern, cli.py will not set LARCH_QUIET_DISABLE for that verb and the replayed envelope can be routed to the quiet log instead of stdout.
- **Proposed resolution**: Add ("review-and-fix", "normalize-status") to _MACHINE_STDOUT_KEYS with a focused dispatch test, or explicitly specify that this entry point must not call quiet_init and must write its replay directly to stdout.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/core/process_identity.py:451-453
- **Concern**: FINDING 11 reattach removes the detached marker before await-loop-identity, but await still requires that marker. Scenario: The plan tells both Step 3 and Step 5 wrappers to delete `.step3-wrapper-detached` / `.step5-wrapper-detached` before `await-loop-identity`, yet it also requires Step 5 await to succeed only when the detached marker exists and says to preserve existing Step 3 `plan-review await-loop-identity` behavior. Current `await_loop_identity_main` hard-fails when the marker is absent, so the accepted reattach handshake cannot work as written.
- **Proposed resolution**: Drop the detached-marker presence gate from await during reattach (for example `--reattach` on both await verbs, or read PID/STDOUT from wrapper state instead), pause orphan checks while the marker is intentionally removed, and update the planned Step 3/5 process_identity tests so they no longer require a present marker on the reattach path.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh
- **Concern**: Step 5 detached-marker KV shape is underspecified for orphan age. Scenario: The plan reads only `PID` and `STDOUT_FILE` from `.step5-wrapper-detached` and says orphan checks use marker age, but it never requires the Step 3 `DETACHED_AT_EPOCH` (and `SIGNAL`) fields that `design-step3-review.sh` already writes. Without pinning that shared shape, Step 5 orphan timeout can drift to mtime heuristics or disagree with Step 3.
- **Proposed resolution**: Specify the Step 5 detached-marker write/read contract to match Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`), have Python orphan checks prefer `DETACHED_AT_EPOCH`, and add a harness assertion for the field.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh
- **Concern**: Step 5 detach/reattach paths omit `.bg-wait-active` lifecycle rules. Scenario: The plan only says to remove `.bg-wait-active` after successful normalize on reattach. It does not require arming the marker before reattach wait (Step 3 calls `design_bg_wait_marker_start` before `_step3_review_reattach_detached_loop`) or clearing it on signal-induced detach. Stale `STEP=implement-step5-review` markers can block orchestrator reads or mislead `hook-bg-poll-guard.sh` after detach, matching the accepted Step 3 bg-wait regression.
- **Proposed resolution**: Mirror Step 3 ordering: write/refresh `.bg-wait-active` before any reattach wait and before fresh launch; in signal cleanup always `rm -f .bg-wait-active` before writing the detached marker or exiting; extend `test-step-5-review.sh` to assert detach leaves no terminal sentinel and no stale bg-wait marker.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh
- **Concern**: Reattach should run tmpdir vendor cleanup before normalize-status, not optionally. Scenario: The Step 5 reattach bullets call `session kill-background-processes` only optionally after await, while Step 3 `_step3_review_reattach_detached_loop` always runs `_step3_review_kill_tmpdir_processes` before normalize. Detached reviewer children can keep running after rejoin and race normalize/terminal-sentinel writes.
- **Proposed resolution**: Make `python/cli.py session kill-background-processes --implement-tmpdir ...` mandatory on the Step 5 reattach path immediately before `review-and-fix normalize-status`, matching Step 3 ordering.



### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:34-106; python/larch/core/process_identity.py:451-453
- **Concern**: Reattach removes the detached marker before an await contract that still requires it. Scenario: On Step 5 reentry, the wrapper deletes `.step5-wrapper-detached` to pause the orphan cap, then `await-loop-identity` fails because the planned and current await contract requires that marker. The wrapper exits fail-closed and never normalizes the finished review. The same conflict applies to Step 3.
- **Proposed resolution**: Change the plan so await uses a validated reattach lease or a wrapper-prevalidated marker snapshot after marker removal, or keep a non-orphan-counted reattach marker that await accepts. Cover both Step 3 and Step 5 await tests.



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:35-39; python/larch/core/process_identity.py:469-480
- **Concern**: Prior accepted launch-to-identity fix is incomplete: pre-identity cleanup still calls a sidecar-backed teardown. Scenario: If TERM lands after Step 5 launches `review-and-fix` but before identity publication succeeds, no `.step5-loop-identity.json` exists. A sidecar-backed teardown can no-op, leaving the new process group running without a detached marker or completion sentinel.
- **Proposed resolution**: Specify a sidecarless pre-identity teardown path that captures and validates the just-launched pid and pgid with expected signature `review-and-fix step5` before signaling, or block signal cleanup until identity publication can use the normal path. Make the pre-identity harness assert the fake child process group exits.



