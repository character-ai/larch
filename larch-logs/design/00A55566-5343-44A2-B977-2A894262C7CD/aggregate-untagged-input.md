### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:Step 18b / python/larch/report/final_report.py:895-923
- **Concern**: Step 18b must not always suppress chat emit when a cached Step 17 body exists. Scenario: The plan tells the orchestrator to cache Step 17 markers, pass `--step17-emitted true`, and always suppress Step 18 chat emit before emitting the Step 17 cache last. `step18b_final_report()` still flips `EMIT_BODY=true` when `write_final_report()` changes `summary-final.md` after the sentinel exists (`should_emit_updated_body`), and `step-18.sh` then prints fresh markers into composite stdout. Blindly emitting the Step 17 cache would show stale cost/timing/Gantt data and undo today’s refresh path.
- **Proposed resolution**: In `skills/implement/SKILL.md` Step 18b (and `skills/shared/final-summary-emit.md` implement bindings), add precedence: when composite/finalize stdout has valid markers and `EMIT_BODY=true`, terminal emit must use that post-step18b body even if a Step 17 cache exists; emit the Step 17 cache only when `EMIT_BODY=false`. Optionally narrow `should_emit_updated_body` or document that orchestrator precedence is authoritative.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/shared/final-summary-emit.md:60-66
- **Concern**: `/design` file-only cancel profile still mandates immediate emit. Scenario: The shared file-only profile still says Read `FINAL_SUMMARY_PATH` and emit immediately. Step 0b `cancel-title-filter` / `cancel-reentry-guard` use that profile today, which is the same mid-turn emit bug on early exits. The plan updates the Read-always profile and `SKILL.md` Final summary block but does not explicitly rewrite the file-only profile to Read/cache now and defer plain-chat emit until after any required operator line, with zero following tool calls.
- **Proposed resolution**: Extend the planned `skills/shared/final-summary-emit.md` update to the file-only profile: cache on Read, defer emission via the shared terminal-placement / deferred-emit procedure, and point Step 0b cancel routes at that contract instead of immediate emit.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md Step 18b
- **Concern**: Deferred Step 17 cache must not override refreshed Step 18 markers when EMIT_BODY=true. Scenario: `final_report.step18b_final_report` sets `emit_body=false` when `.step17-emitted` exists, then can flip `EMIT_BODY=true` via `should_emit_updated_body` after `write_final_report` refreshes `summary-final.md`. The plan tells the orchestrator to always suppress Step 18 chat emit and emit the Step 17 cache when a pending body exists. On the green path that can show a stale report (old outcome or cost line) even though Step 18 refreshed the on-disk summary.
- **Proposed resolution**: Add a branch: when a Step 17 body is cached and finalize stdout has `EMIT_BODY=true` with valid markers, terminal emit must use the Step 18 marker body from captured stdout, not the Step 17 cache. Use the Step 17 cache only when `EMIT_BODY=false`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-18.md
- **Concern**: `--step17-emitted` wrapper contract is only MAY_UPDATE but semantics change is firm. Scenario: The plan redefines `--step17-emitted true` as cached-not-yet-emitted and moves chat emission after teardown. `step-18.md` still says the flag exists so `EMIT_BODY` sees prompt-side Step 17 emission, and Marker body handoff still describes pre-teardown emission as the deliverable. Leaving it MAY_UPDATE risks a prompt-only SKILL change with stale wrapper docs that still describe the old contract.
- **Proposed resolution**: Promote `skills/implement/scripts/step-18.md` to `### UPDATED:` and sync lines 44-45 and Marker body handoff: wrapper stdout markers are cache input only; orchestrator owns terminal chat emit after teardown; `--step17-emitted true` means deferred cache pending, not already shown in chat.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/final-summary-emit.md:60-66
- **Concern**: File-only profile still mandates immediate emit on Read. Scenario: The Step 0b cancel-title-filter and cancel-reentry-guard routes bind the file-only profile, which still says Read then emit verbatim. Those exits never reach the Final summary block bgjob procedure, so title-filter cancels keep mid-turn emission and stay hidden on turn-final harnesses.
- **Proposed resolution**: Split the file-only profile like Read-always: Read/cache only, defer plain-chat emission to terminal placement after any route-local operator text, with no following tool call.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-800
- **Concern**: Green-path finalize-done must not rerun standalone finalize. Scenario: The composite step-18-gate-finalize already runs step-18.sh --phase finalize and tears down $IMPLEMENT_TMPDIR before NEXT_ACTION=finalize-done, but Step 18b still exposes an unconditional standalone finalize fence. Anti-halt fence execution can rerun finalize on a deleted tmpdir and leave no terminal report to emit.
- **Proposed resolution**: On finalize-done, parse markers and teardown tail from captured composite stdout only; run warnings and tail relay; emit the cached body last. Restrict the standalone step-18.sh --phase finalize fence to stall-recovery breakout and pin that branch in test-implement-structure.sh.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:752-804
- **Concern**: Terminal emit must prefer refreshed Step 18 body over Step 17 cache. Scenario: final-report step18b can refresh summary-final.md after Step 17 capture; when .step17-emitted is preset, EMIT_BODY can become true and composite stdout carries updated markers. The plan always emits the cached Step 17 body on finalize-done with a pending Step 17 body, so operators can see stale costs or timing after Step 18 refresh.
- **Proposed resolution**: On finalize-done, if composite stdout has EMIT_BODY=true with a valid marker body, terminal chat emit must use that refreshed Step 18 body; emit the cached Step 17 body only when Step 18 markers are suppressed (EMIT_BODY=false).

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:21
- **Concern**: Step 17 anti-halt boundary still permits pre-cleanup emission. Scenario: The plan rewrites Step 17 and Step 18 to cache the marker body until teardown, but the file-level anti-halt terminal boundary is not called out and currently still says to emit the extracted marker body before continuing to Step 18. If left in place, the orchestrator has a direct conflicting instruction on the green /implement path and can still hide the report.
- **Proposed resolution**: Add a firm skills/implement/SKILL.md plan bullet to rewrite that anti-halt terminal boundary so Step 16-17 only captures a pending body, Step 18 runs cleanup/teardown/tail relay, and the cached body is emitted last with no following tool call; pin removal of the old emit-then-continue wording in scripts/test-implement-structure.sh.
