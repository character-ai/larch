# hook-no-progress-guard.sh

## Purpose

Universal no-progress circuit breaker (#5639). Complements `hook-bg-poll-guard.sh`'s `PreToolUse`
probe-clamp by catching the class of no-progress turns that make **no tool calls** at all — pure
prose "still waiting" turns that are invisible to `PreToolUse` hooks.

Two event handlers in one script:

- **Stop handler**: counts consecutive turn-ends while any bg-wait marker is live. When the count
  reaches `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (default 5), arms a `no-progress-circuit-breaker-armed`
  flag in the marker directory.
- **UserPromptSubmit handler**: before each new turn, checks every live marker for an armed flag.
  If found, blocks the turn with an operator-visible message containing the count and threshold.

The circuit breaker auto-disarms when the bg task's terminal sentinel is written (or the marker is
removed by the EXIT trap), so a genuine completion notification is never blocked by the guard.

## Primary callers

- `hooks/hooks.json`: `Stop` event (counts turns) and `UserPromptSubmit` event (blocks when armed).

## Invariants

- Fails open on missing `jq`, malformed input, unreadable markers, or write errors.
- Uses the same marker-discovery logic (`marker_candidates`) as `hook-bg-poll-guard.sh` and
  respects the `LARCH_BG_POLL_GUARD_MARKER` test-override.
- Scopes live markers by their session tmpdir under `~/.cache/larch/sessions/` plus `kill -0` PID-liveness and marker age, not by `CLAUDE_PID` matching (#5684). The old `CLAUDE_PID` equality check rejected every marker in production (the hook's `PPID`/input never matched the stored value), so the breaker never armed. The marker still records `CLAUDE_PID` as debug metadata but the hook no longer reads it; as a result two concurrent larch sessions on one machine are no longer isolated from each other's live-marker counts.
- Checks `is_step_completed` (terminal sentinel present) before declaring a marker live, mirroring
  the release logic in `hook-bg-poll-guard.sh` (#4431, #4450 race-condition fix). It releases
  `implement-step8-ship` on root-level `.step-8-ship-handoff.rc` when the sidecar is a regular file,
  not a symlink.
- Counter (`no-progress-turns.count`) and breaker (`no-progress-circuit-breaker-armed`) files live
  in the marker directory and are cleaned up with the session tmpdir.
- Stop re-entry guard: exits immediately when `stop_hook_active=true` in the payload.
- Disabled entirely via `LARCH_NO_PROGRESS_GUARD_DISABLE=1`.
- Threshold configurable via `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (integer; default 5). Values that
  are empty or non-numeric fall back to 5.
- Block JSON is emitted via static `printf` (not `jq -cn`) so a `jq` runtime failure at the emit
  point cannot silently swallow the block signal (#5610 pattern).

## Threshold rationale

K=5 provides enough headroom for legitimate notification processing (typically 1–3 turns from
launch to real completion) while capping the documented worst-case storm (`BC8DDA64`: ~40 turns).

## Harness

Covered by `scripts/test-hook-no-progress-guard.sh`, wired through
`make test-hook-no-progress-guard` and `make lint`.

## Update triggers

Update this file when: the event types handled change, the counter/breaker file names or locations
change, the threshold default changes, or `is_step_completed` sentinel coverage changes.
