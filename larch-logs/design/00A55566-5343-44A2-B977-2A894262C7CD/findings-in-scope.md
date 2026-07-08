### FINDING_1: Final report emit ordering still allows stale or pre-cleanup output
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The green `/implement` path still has conflicting terminal-report ownership rules: Step 18b, finalize-done handling, and the anti-halt boundary disagree about whether a cached Step 17 body or refreshed Step 18 markers should own the final emit. That can either show stale cost/timing data or keep the report from being the last visible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` Step 18b (and `skills/shared/final-summary-emit.md` implement bindings), add precedence: when composite/finalize stdout has valid markers and `EMIT_BODY=true`, terminal emit must use that post-step18b body even if a Step 17 cache exists; emit the Step 17 cache only when `EMIT_BODY=false`. Optionally narrow `should_emit_updated_body` or document that orchestrator precedence is authoritative.
  - From Cursor-Pragmatic: Add a branch: when a Step 17 body is cached and finalize stdout has `EMIT_BODY=true` with valid markers, terminal emit must use the Step 18 marker body from captured stdout, not the Step 17 cache. Use the Step 17 cache only when `EMIT_BODY=false`.
  - From Cursor-Requirements: On finalize-done, if composite stdout has `EMIT_BODY=true` with a valid marker body, terminal chat emit must use that refreshed Step 18 body; emit the cached Step 17 body only when Step 18 markers are suppressed (`EMIT_BODY=false`).
  - From Codex-Requirements: Add a firm skills/implement/SKILL.md plan bullet to rewrite that anti-halt terminal boundary so Step 16-17 only captures a pending body, Step 18 runs cleanup/teardown/tail relay, and the cached body is emitted last with no following tool call; pin removal of the old emit-then-continue wording in scripts/test-implement-structure.sh.

### FINDING_2: File-only cancel profile still emits immediately
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The file-only final-summary profile used by Step 0b cancel routes still says to Read and emit immediately, so those early exits can still push the summary mid-turn instead of deferring it to terminal placement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the planned `skills/shared/final-summary-emit.md` update to the file-only profile: cache on Read, defer emission via the shared terminal-placement / deferred-emit procedure, and point Step 0b cancel routes at that contract instead of immediate emit.
  - From Cursor-Requirements: Split the file-only profile like Read-always: Read/cache only, defer plain-chat emission to terminal placement after any route-local operator text, with no following tool call.

### FINDING_3: `--step17-emitted` wrapper docs lag the new contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The `--step17-emitted` wrapper prose still describes prompt-side Step 17 emission, but the proposed semantic change makes it a deferred cache marker, so the wrapper docs can mislead callers and leave stale contract text in `step-18.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Promote `skills/implement/scripts/step-18.md` to `### UPDATED:` and sync lines 44-45 and Marker body handoff: wrapper stdout markers are cache input only; orchestrator owns terminal chat emit after teardown; `--step17-emitted true` means deferred cache pending, not already shown in chat.

### FINDING_4: Finalize-done can rerun standalone finalize
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The finalize-done path still has a standalone finalize fence that can rerun finalize after `$IMPLEMENT_TMPDIR` teardown, so the terminal report may never be produced from the captured composite stdout alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: On finalize-done, parse markers and teardown tail from captured composite stdout only; run warnings and tail relay; emit the cached body last. Restrict the standalone step-18.sh --phase finalize fence to stall-recovery breakout and pin that branch in test-implement-structure.sh.
