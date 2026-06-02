### FINDING_11: Fenced or non-footer exact Closes line can suppress real footer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-python-closes-output.txt
- **Severity**: latent
- **Concern**: Because the idempotency check scans the whole body for an exact `Closes #N` line, an example inside a fenced block or other non-footer context can prevent appending the real trailing footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-python-closes-output.txt: Address the concern above.


### FINDING_13: Stall-recovery keyless-file contract contradicts helper behavior
- **Reviewer(s)**: dyn-bash-state-output.txt, dyn-final-report-flow-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` says empty/comment-only `ship-pr-state.sh` exits with `CLEARED=false` and remains unchanged, but `clear-stall` rewrites those files with `STALL_TRACKING=false` and emits `CLEARED=true`; orchestrators following the prose can mis-route recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.
  - From dyn-final-report-flow-output.txt: Address the concern above.


### FINDING_14: Absent state file clear path can force terminal routing
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: When `ship-pr-state.sh` is absent, `clear-stall` emits `CLEARED=false` and creates no file, unlike the old inline path that wrote `STALL_TRACKING=false`; a memory/session-only stall may therefore fail the success-path disk clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.


### FINDING_16: Step 18b snapshot-failure contract disagrees with script and tests
- **Reviewer(s)**: dyn-final-report-flow-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `step-18b-final-report.md` says `SNAPSHOT_OK=false` must not promote `emit_body`, but the shell and harness intentionally fail open and emit when `write-final-report.sh` succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-final-report-flow-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


