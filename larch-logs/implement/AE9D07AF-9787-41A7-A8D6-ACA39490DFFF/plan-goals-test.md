## Goal
Implement issue #5638: [IMPLEMENTING] [BUG] /implement has no premature-notification defense: add bg-wait marker, terminal….

## Implementation Plan
## Summary

`/implement` background-wait fences (Step 2 Codex/Cursor dispatch, Step 5 review-and-fix) have no defense against premature or spurious `<task-notification>` events. `AGENTS.md` already acknowledges the gap: "Implement remains notification-driven until real implement terminal sentinels and hook support exist." The observed worst case is committed run `BC8DDA64` (implementing #3678): a premature `{"status":"completed"}` notification fired while Codex kept running 20+ minutes, the orchestrator armed up to 7 Monitors (banned by `orchestrator-never.md`), and those Monitors then fired their own per-minute notifications. The transcript shows 204 turns, 42 harness notifications, ~40 "still waiting" turns. `hook-bg-poll-guard.sh` recognizes only `/design` markers and sentinels, so none of this was denied. Build the missing `/implement` defense layer: a bg-wait marker, terminal sentinels, a hook backstop that denies Monitor/Task* and progress polling during waits, and contract parity with `/design`.

## Original report

The operator reported repeated episodes where the `/design` (and possibly `/implement`) main agent went into a furious loop processing spurious task-notifications, each notification costing a turn and therefore money, with dozens to hundreds of turns before manual intervention. Forensic review of committed `/implement` transcripts confirmed the pattern occurs in `/implement` too, amplified by the orchestrator arming Monitors to watch a background job. This issue targets the `/implement` defense layer. The `/design` source fix is filed separately (eliminate `set -m`); the universal no-progress circuit-breaker backstop is the sibling item in this batch.

## Reproduction scenario

1. Run `/implement` (or `/im`) on a task whose Step 2 Codex/Cursor implementation or Step 5 review runs for many minutes (commonly 10-60+ minutes).
2. A background fence is launched with `run_in_background: true`. An inner wrapped subprocess completes and the harness fires a `{"status":"completed"}` notification while the outer step is still running.
3. The orchestrator re-engages on the premature notification. With no hook backstop and a weaker prompt contract than `/design`, it may arm Monitors to watch the log and narrate "still waiting" each turn.
4. Each armed Monitor fires its own notification per matched log event (e.g., once per minute), compounding the turn burn.

Cannot be deterministically triggered by one command; depends on vendor subprocess timing and orchestrator reaction.

## Expected behavior

A premature or spurious `/implement` notification costs at most one cheap no-tool-call turn. Monitor-arming and progress-polling during an active `/implement` background wait are denied by the hook. Repeated foreground sentinel probes are clamped. The wait releases on the real completion notification or a terminal sentinel.

## Observed behavior

Committed run `BC8DDA64-E769-4708-A842-AF54AA0417E9` (committed 2026-06-22): 204 turns, 42 harness notifications, 54 Monitor mentions, ~40 "still waiting" turns. Turn-by-turn: premature `completed` notification at t11 while Codex ran to ~t37 (20+ minutes); Monitors armed and grown to 7 across t22-t31; per-minute Monitor-event notifications at t32/t34/t36. No hook denied any of it.

## Root cause analysis

Four independent gaps:

1. No `/implement` bg-wait marker exists for `hook-bg-poll-guard.sh` to key on. The hook scans for `.bg-wait-active` markers whose `STEP` is one of `design-step3-review`, `design-step5c`, `design-step-final-summary`. `/implement` writes no such marker.
2. The hook only handles tool names `Read` and `Bash`. `Monitor` and `TaskOutput` tool calls during a wait are not denyable. The single biggest amplifier in `BC8DDA64` (arming Monitors) is therefore invisible to the hook.
3. The `/implement` prompt contract (orchestrator-never.md NEVER #8) is weaker than `/design`'s: it lacks the "empty output -> end turn with zero tool calls and no prose" rule and the identical-content notification fingerprint skip (#5418).
4. Arming a Monitor to watch a background job is banned by `orchestrator-never.md` and `AGENTS.md`, but nothing enforces the ban.

Implement waits are long (committed implement `timing-report.json`: review+checks median ~35 minutes), so the window for premature/spurious notifications is large and the accumulated cost is high.

## Evidence

- `scripts/hook-bg-poll-guard.sh`: `case "$tool_name" in Read|Bash) ;; *) exit 0 ;;` (tool coverage is Read/Bash only); `marker_step_completed` and `probe_sentinel_name` recognize only `step-3-terminal` / `step-5c-terminal` / `step-final-summary` (all `/design`).
- `AGENTS.md`: "Implement remains notification-driven until real implement terminal sentinels and hook support exist."
- `larch-logs/implement/BC8DDA64-E769-4708-A842-AF54AA0417E9/session-transcript.jsonl`: the storm transcript described above.
- Implement timing: committed `larch-logs/implement/*/timing-report.json` show review+checks steps with median ~35 minutes, well past any single-turn window.
- `/design`-side fixes that `/implement` lacks: #5478 (probe-clamp), #5418 (identical-content dedup), #5610 (empty-output silent yield), #4725 (background-waiter deny).

## Affected files

- `scripts/hook-bg-poll-guard.sh` and `scripts/test-hook-bg-poll-guard.sh` — add `Monitor` / `TaskOutput` to the handled tool set; recognize `/implement` markers and sentinels; deny progress polling and Monitor-arming during a live `/implement` wait.
- `skills/implement/SKILL.md` — write/remove the bg-wait marker and terminal sentinels around long fences; tighten the wait contract.
- `skills/shared/orchestrator-never.md` (NEVER #8) and `skills/shared/design-background-wait.md` if the contract is shared — bring `/implement` to `/design` parity (empty-output silent yield, identical-content fingerprint skip, explicit hook-enforced no-Monitor rule).
- implement marker/sentinel writer in `python/` (mirror the `/design` race-free sentinel pattern).
- `AGENTS.md` — update the "no implement terminal sentinels / hook support" statement once built.

## Suggested fix(es)

Defense-in-depth, enforcement-first:

1. Write an `/implement` bg-wait marker (mirror `/design`'s `.bg-wait-active`: `STEP=implement-step2-dispatch` / `implement-step5-review`, `PID`, `START_EPOCH`, `TIMEOUT_S`, `CLAUDE_PID`) when a long fence launches; remove it on completion. Set `TIMEOUT_S` large enough for multi-hour vendor runs.
2. Add `/implement` terminal sentinels (e.g. `.completed/step-2-terminal`, `.completed/step-5-terminal`) written race-free before the task process exits, so the hook can release on completion.
3. Extend `hook-bg-poll-guard.sh`: add `Monitor` and `TaskOutput` to the handled tool names and DENY them while an `/implement` bg-wait marker is live (this directly prevents the `BC8DDA64` Monitor-arming); deny progress-poll Bash/Read shapes against the `/implement` tmpdir; generalize the per-sentinel probe-clamp to `/implement` foreground sentinel probes.
4. Bring the `/implement` contract to `/design` parity: empty-output -> end turn with zero tool calls and no prose; identical-content notification fingerprint skip; explicit "NEVER arm Monitor/TaskOutput to watch a bg fence," now hook-enforced.

Honest limitation: a `PreToolUse` hook can only clamp denyable tool calls. A model that emits pure "still waiting" prose turns (no tool call) per notification is not catchable by this hook; that residual is addressed by the prompt contract and by the sibling circuit-breaker investigation in this batch.

## Open questions

- Exact set of `/implement` fences that need a marker/sentinel (Step 2 dispatch, Step 5 review; any others?).
- Can `/implement` terminal sentinels be written as race-free as `/design`'s (sentinel before task-process exit)?
- Does extending the hook's handled tool set to `Monitor`/`TaskOutput` have side effects on legitimate Monitor use elsewhere (the deny must be scoped to an active `/implement` wait only)?

## Test plan
(no test plan section in plan-file)
