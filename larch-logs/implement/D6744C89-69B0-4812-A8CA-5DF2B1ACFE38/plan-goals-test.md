## Goal
Implement issue #5639: [IMPLEMENTING] [BUG] Universal no-progress circuit breaker: hard-cap consecutive no-progress….

## Implementation Plan
## Summary

Even after the `/design` source fix and the `/implement` defense layer, there is no hard cap on consecutive no-progress orchestrator turns during a background wait. The existing backstop in `hook-bg-poll-guard.sh` (#5478 probe-clamp) only catches specific foreground probe tool-call shapes against `/design` sentinels. It cannot catch a model that emits a pure "still waiting" prose turn (no tool call) on each notification, and it does not cover `/implement`. Over multi-hour waits (committed `/design` plan-review median ~1 hour, max 2:26:02; `/implement` review+checks median ~35 minutes), any residual notification leak or non-probe reaction can still burn dozens of turns, which is the money-burning trap the operator hit. Investigate and build a universal backstop that hard-caps consecutive no-progress turns regardless of tool-call shape or skill.

## Original report

The operator observed dozens to hundreds of turns burned on spurious notification re-engagement before manually intervening, and asked whether anything beyond the merged mitigation can prevent recurrence. The source fix (eliminate `set -m`) and the `/implement` defense layer are filed separately. This item is the ultimate backstop: a deterministic cap so that no failure of the other layers can produce an unbounded turn loop again.

## Reproduction scenario

1. Any background wait where the harness re-invokes the orchestrator repeatedly: spurious empty-output notifications, identical-content re-delivery, or Monitor events.
2. The orchestrator responds with a no-progress turn that makes no denyable tool call (for example a plain "still waiting" prose turn, which is exactly what the `/design` empty-output contract now asks for).
3. No existing hook denies a prose-only turn, so each notification still costs one full-context turn for the entire duration of the wait.

## Expected behavior

After K consecutive no-progress turns under an active bg-wait marker, a deterministic mechanism caps the worst case: force a yield, hard-stop with an operator-visible message, or otherwise break the loop, so cost is bounded at roughly K turns instead of unbounded.

## Observed behavior

Today the only backstop is the `PreToolUse` probe-clamp, which is `/design`-sentinel-specific and tool-call-shape-specific. Pure-prose no-progress turns and all `/implement` waits are uncapped. `BC8DDA64` shows ~40 uncapped waiting turns in a single run.

## Root cause analysis

`PreToolUse` hooks fire only when the orchestrator makes a tool call. A no-progress turn that makes no tool call is invisible to a `PreToolUse` hook. There is no per-turn or `Stop`-event mechanism that counts consecutive no-progress notification turns and forces termination. The `#5478` clamp counts foreground probe tool calls per absent sentinel, but it cannot see a turn that probes nothing.

## Evidence

- `scripts/hook-bg-poll-guard.sh` probe-clamp (`terminal_sentinel_probe_clamp`, `probe_counter_*`) is gated on `bash_is_terminal_sentinel_foreground_probe` matching a `/design` sentinel probe shape; a prose-only turn never reaches it.
- `skills/shared/design-background-wait.md` and `orchestrator-never.md` rely on prompt compliance for prose-only turns ("end the turn silently: call no tool ... print no prose").
- Timing data: committed `/design` plan-review median ~1h (max 2:26:02), `/implement` review+checks median ~35m, so the worst-case uncapped turn count over a wait is large.

## Affected files

- Investigation of the available Claude Code hook surface (does a `Notification`-event hook or `Stop`-event hook exist that can observe repeated notifications and emit a deny/stop signal?).
- `scripts/hook-bg-poll-guard.sh` — if a tool call is made each turn, generalize the probe-clamp into a marker-scoped consecutive-no-progress counter that denies after K, covering both skills.
- `skills/shared/orchestrator-never.md` and `skills/shared/design-background-wait.md` — document the backstop and its threshold.

## Suggested fix(es)

Framed as an investigation plus implementation, because feasibility depends on which hook events fire on notification re-invocations:

1. Determine whether a `Notification`-event or `Stop`-event hook can observe consecutive spurious notifications under a live bg-wait marker and emit a deny or stop signal.
2. If each no-progress turn makes a denyable tool call, generalize the existing `#5478` probe-clamp into a marker-scoped consecutive-no-progress counter that denies after a small K and clears on real progress, covering both `/design` and `/implement`.
3. As a floor, define a turn-budget that hard-stops the run with an operator-visible message after K no-progress turns under a live bg-wait marker.
4. Distinguish a healthy long wait (roughly one real completion notification) from a storm (many no-progress turns) so legitimate hour-long reviews are never killed.

State uncertainty plainly: a pure-prose no-progress turn may not be interceptable by current hook events. Part of this issue is a spike to determine feasibility before committing to a mechanism.

## Open questions

- Which Claude Code hook events fire when the harness re-invokes the orchestrator on a `<task-notification>`? Can any of them force a yield or stop?
- What is an acceptable K (consecutive no-progress turns) that bounds cost without killing healthy multi-hour waits?
- Should the breaker hard-stop the run, force a single yield, or escalate to the operator?

## Test plan
(no test plan section in plan-file)
