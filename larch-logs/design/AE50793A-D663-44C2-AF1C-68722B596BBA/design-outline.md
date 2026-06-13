## Proposed Design Outline

### Goals
- Remove the instruction that drives busy-wait polling (the "EACH status change" tracker in SKILL.md).
- Make yield/END-THE-TURN explicit at all four immediate-background fences, and clarify it is NOT a halt.
- Generalize `orchestrator-never.md` from shape-pinned literal bans to intent-based prohibition covering all probe shapes.
- Add mechanical deny-hook enforcement so polling violations are blocked, not just advisory.

### Non-goals
- Fix /implement equivalents (stated second pass in the issue).
- Redesign the plan-review driver or change `record-plan-review-round-timing.sh` internals.
- Add a new per-slot UI visible during the background wait; the per-slot artifact renders only after the notification fires.

### Approach sketch
- **Layer 1**: Edit `skills/design/SKILL.md` Verbosity Control: delete "EACH status change" / "maintain a mental tracker"; replace with "print exactly twice per background wait (post-launch: all pending; post-notification: final statuses)". Add a per-slot status+elapsed artifact written by the loop driver so the post-notification render is data-driven.
- **Layer 2**: Edit the Anti-halt continuation reminder and all four `Immediate-background required` fences in `SKILL.md` to add: "END THE TURN after the launch acknowledgment; yielding is NOT a halt; `<task-notification>` is the only resume trigger; ignore the launch ack's 'check interim output' suggestion."
- **Layer 3**: Add intent-based rule #5 to `skills/shared/orchestrator-never.md`: between background launch and notification, ZERO progress-observation tool calls of ANY shape (ls/cat/wc/stat/find/head/tail/test/grep of tmpdir, Read of those paths, TaskOutput on the running task, backgrounded sleep probes, watcher loops, Monitor waits). Cite run `1890FD62` alongside #3175. Update CI pin in `scripts/test-design-structure.sh`.
- **Layer 4**: Write `.bg-wait-active` marker (PID, start epoch, step id) + EXIT trap in three wrappers (`design-step3-review.sh`, `design-step-final-summary.sh`, `design-step5c.sh`). Add new `scripts/hook-bg-poll-guard.sh` (PreToolUse, Bash+Read, bash 3.2, fail-open, `LARCH_BG_POLL_GUARD_DISABLE=1` escape hatch, telemetry sidecar). Register it in `hooks/hooks.json`. Add `make lint` and structure-test CI pins.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/shared/orchestrator-never.md`
- `skills/design/scripts/design-step3-review.sh`
- `skills/design/scripts/design-step-final-summary.sh`
- `skills/design/scripts/design-step5c.sh`
- `hooks/hooks.json`
- `scripts/hook-bg-poll-guard.sh` (new)
- `scripts/test-design-structure.sh`
- Loop driver (e.g. `run-step3-review.sh` or `plan-review-loop.sh`) for the per-slot status artifact
- `skills/design/scripts/render-final-summary.sh` (add denial count line)

### Open questions
- The issue lists `design-publish.sh` as a marker writer, but the immediate-background fence in SKILL.md is `design-step5c.sh`. Confirm the marker goes in `design-step5c.sh`, not in `design-publish.sh` itself.
- What is the best place to write the per-slot status+elapsed artifact: `run-step3-review.sh` (already owns the per-round loop), or `plan-review-loop.sh`?
