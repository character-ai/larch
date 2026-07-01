# hook-no-progress-guard.sh

## Purpose

Universal no-progress circuit breaker (#5639). Complements `hook-bg-poll-guard.sh`'s `PreToolUse`
probe-clamp by catching the class of no-progress turns that make **no tool calls** at all — pure
prose "still waiting" turns that are invisible to `PreToolUse` hooks.

Two event handlers in one script:

- **Stop handler**: counts consecutive turn-ends while any bg-wait marker is live. When the count
  reaches `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (default 5), arms a `no-progress-circuit-breaker-armed`
  flag in the marker directory.
- **UserPromptSubmit handler**: before each new turn, checks every live marker for an armed flag
  that cannot be proven to belong to a different repo clone. If found, blocks the turn with an
  operator-visible message containing the count, threshold, and marker path.

The circuit breaker auto-disarms when the bg task's terminal sentinel is written (or the marker is
removed by the EXIT trap), so a genuine completion notification is never blocked by the guard.

## Primary callers

- `hooks/hooks.json`: `Stop` event (counts turns) and `UserPromptSubmit` event (blocks when armed).

## Invariants

- Fails open on missing `jq`, malformed input, unreadable markers, or write errors.
- Uses the same marker-discovery logic (`marker_candidates`) as `hook-bg-poll-guard.sh` and
  respects the `LARCH_BG_POLL_GUARD_MARKER` test-override.
- The `$TMPDIR` branch of `marker_candidates` scans only `larch-*`, `claude-design-*`, and `claude-implement-*`
  prefixed dirs under `$TMPDIR` (maxdepth 2 within each), not the full TMPDIR tree. This
  avoids the macOS per-user `$TMPDIR` timeout issue (#5868): the full tree can reach 77k+
  dirs and exceed the hook's timeout under concurrent load. The `~/.cache/larch/sessions`
  branch is unaffected.
- Scopes live markers by their session tmpdir under `~/.cache/larch/sessions/` plus `kill -0` PID-liveness and marker age, not by `CLAUDE_PID` matching (#5684). The old `CLAUDE_PID` equality check rejected every marker in production (the hook's `PPID`/input never matched the stored value), so the breaker never armed. The marker still records `CLAUDE_PID` as debug metadata but the hook no longer reads it.
- `UserPromptSubmit` blocking is scoped by repo-clone identity when it is knowable (#5927): it reads the candidate marker's sibling `.larch-keepalive` `CLONE_PATH=` value (the same identity file `session_env.py` writes at bootstrap) and skips that marker only when its canonicalized `CLONE_PATH` is not the same clone tree as the current session's canonicalized `cwd` (also read from the hook's own JSON input, mirroring `hook-bg-poll-guard.sh`). Same-clone means exact path match or either path is a subdirectory of the other, so a prompt from `/repo/docs` still matches a marker whose `CLONE_PATH` is `/repo`. A marker with no readable `CLONE_PATH`, or a current invocation with no readable `cwd`, is treated as same-clone and still blocks — unknown identity never introduces a new false negative, it only preserves the pre-fix global-blocking behavior. The `Stop` handler's turn counting remains global and unscoped; only the `UserPromptSubmit` block decision is clone-scoped.
- Checks `is_step_completed` (terminal sentinel present) before declaring a marker live, mirroring
  the release logic in `hook-bg-poll-guard.sh` (#4431, #4450 race-condition fix). It covers
  design Step 3, Step 4 tail, Step 5c, and final-summary markers, plus implement Step 3 checks,
  Step 5 review, Step 5 resume, Step 5 self-review, Step 6 checks, Step 7a, and Step 8 ship
  markers. It releases `implement-step8-ship` on root-level `.step-8-ship-handoff.rc`; every
  completion sentinel must be a regular file, not a symlink.
- Counter (`no-progress-turns.count`) and breaker (`no-progress-circuit-breaker-armed`) files live
  in the marker directory and are cleaned up with the session tmpdir.
- Stop re-entry guard: exits immediately when `stop_hook_active=true` in the payload.
- Disabled entirely via `LARCH_NO_PROGRESS_GUARD_DISABLE=1`.
- Threshold configurable via `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (integer; default 5). Values that
  are empty or non-numeric fall back to 5.
- Block JSON is emitted via static `printf` (not `jq -cn`) so a `jq` runtime failure at the emit
  point cannot silently swallow the block signal (#5610 pattern). The message includes the exact
  marker path (`<dir>/.bg-wait-active`) and the two recovery sidecar paths
  (`<dir>/no-progress-circuit-breaker-armed`, `<dir>/no-progress-turns.count`) so the operator does
  not have to guess the offending tmpdir (#5927).

## Threshold rationale

K=5 provides enough headroom for legitimate notification processing (typically 1–3 turns from
launch to real completion) while capping the documented worst-case storm (`BC8DDA64`: ~40 turns).

## Harness

Covered by `scripts/test-hook-no-progress-guard.sh`, wired through
`make test-hook-no-progress-guard` and `make lint`.

## Update triggers

Update this file when: the event types handled change, the counter/breaker file names or locations
change, the threshold default changes, `is_step_completed` sentinel coverage changes, or the
clone-scoping identity source (`.larch-keepalive` `CLONE_PATH`) changes.
