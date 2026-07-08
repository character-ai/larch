---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: File-only cancel profile still emits immediately
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The file-only final-summary profile used by Step 0b cancel routes still says to Read and emit immediately, so those early exits can still push the summary mid-turn instead of deferring it to terminal placement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the planned `skills/shared/final-summary-emit.md` update to the file-only profile: cache on Read, defer emission via the shared terminal-placement / deferred-emit procedure, and point Step 0b cancel routes at that contract instead of immediate emit.
  - From Cursor-Requirements: Split the file-only profile like Read-always: Read/cache only, defer plain-chat emission to terminal placement after any route-local operator text, with no following tool call.


### [Plan Review] FINDING_3

### FINDING_3: `--step17-emitted` wrapper docs lag the new contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The `--step17-emitted` wrapper prose still describes prompt-side Step 17 emission, but the proposed semantic change makes it a deferred cache marker, so the wrapper docs can mislead callers and leave stale contract text in `step-18.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Promote `skills/implement/scripts/step-18.md` to `### UPDATED:` and sync lines 44-45 and Marker body handoff: wrapper stdout markers are cache input only; orchestrator owns terminal chat emit after teardown; `--step17-emitted true` means deferred cache pending, not already shown in chat.


### [Plan Review] FINDING_4

### FINDING_4: Finalize-done can rerun standalone finalize
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The finalize-done path still has a standalone finalize fence that can rerun finalize after `$IMPLEMENT_TMPDIR` teardown, so the terminal report may never be produced from the captured composite stdout alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: On finalize-done, parse markers and teardown tail from captured composite stdout only; run warnings and tail relay; emit the cached body last. Restrict the standalone step-18.sh --phase finalize fence to stall-recovery breakout and pin that branch in test-implement-structure.sh.


---LARCH-REJECTED-END---
