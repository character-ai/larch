# hook-no-progress-guard.sh

## Purpose

Universal no-progress circuit breaker (#5639). Complements `hook-bg-poll-guard.sh`'s `PreToolUse`
probe-clamp by catching the class of no-progress turns that make **no tool calls** at all — pure
prose "still waiting" turns that are invisible to `PreToolUse` hooks.

Two event handlers in one script:

- **Stop handler**: counts consecutive turn-ends while any bg-wait marker owned by the current repo
  clone is live. When the count reaches `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (default 3), arms a
  `no-progress-circuit-breaker-armed` flag in the marker directory and emits a one-shot
  Stop block directly from the hook.
- **UserPromptSubmit handler**: fallback path before each new turn. It checks every live marker
  for an armed flag that cannot be proven to belong to a different repo clone. If found, it
  blocks the turn with an operator-visible message containing the count, threshold, and marker
  path.

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
  branch is unaffected. The matched dirs are collected and passed to a single `find`
  invocation (multiple start-paths) rather than spawning one `find` subprocess per dir
  (#5943 recurrence of #5868): with the accumulated `larch-*`/`claude-design-*`/`claude-implement-*`
  dir count unbounded, per-dir subprocess spawn overhead alone could exceed the hook's
  timeout even though each individual `find` was already depth-scoped.
- Scopes live markers by their session tmpdir under `~/.cache/larch/sessions/` plus `kill -0` PID-liveness and marker age, not by `CLAUDE_PID` matching (#5684). The old `CLAUDE_PID` equality check rejected every marker in production (the hook's `PPID`/input never matched the stored value), so the breaker never armed. The marker still records `CLAUDE_PID` as debug metadata but the hook no longer reads it.
- Both handlers are scoped by repo-clone identity when it is knowable (#5927 and its follow-up): they read the candidate marker's marker-local `CLONE_PATH=` stamp first, then fall back to the sibling `.larch-keepalive` `CLONE_PATH=` value (the same identity file `session_env.py` writes at bootstrap) via `marker_foreign_clone`. They skip that marker only when the canonicalized identity is not the same clone tree as the current session's canonicalized `cwd` (also read from the hook's own JSON input, mirroring `hook-bg-poll-guard.sh`). Same-clone means exact path match or either path is a subdirectory of the other, so a prompt from `/repo/docs` still matches a marker whose `CLONE_PATH` is `/repo`. `UserPromptSubmit` skips the block for a foreign-clone marker; `Stop` skips the turn count for a foreign-clone marker, so an unrelated clone's slow-but-live wait neither arms nor consumes this marker's breaker and cannot make the owning clone block its own next prompt. A marker with no readable marker-local or keepalive `CLONE_PATH`, or an invocation with no readable `cwd`, is treated as same-clone and still counts/blocks — unknown identity never introduces a new false negative, it only preserves the pre-fix global behavior.
- Checks `is_step_completed` (terminal sentinel present) before declaring a marker live, mirroring
  the release logic in `hook-bg-poll-guard.sh` (#4431, #4450 race-condition fix). It covers
  design Step 3, Step 4 tail, Step 5c, and final-summary markers, plus implement Step 3 checks,
  Step 5 review, Step 5 resume, Step 5 self-review, Step 6 checks, Step 7a, and Step 8 ship
  markers. It releases `implement-step8-ship` on root-level `.step-8-ship-handoff.rc`; every
  completion sentinel must be a regular file, not a symlink.
- Counter (`no-progress-turns.count`), breaker (`no-progress-circuit-breaker-armed`), and
  one-shot Stop emission (`no-progress-stop-block-emitted`) files live in the marker directory
  and are cleaned up with the session tmpdir.
- Stop re-entry guard: exits immediately when `stop_hook_active=true` in the payload.
- Disabled entirely via `LARCH_NO_PROGRESS_GUARD_DISABLE=1`.
- Threshold configurable via `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (integer; default 3). Values that
  are empty or non-numeric fall back to 3.
- Block JSON is emitted via static `printf` (not `jq -cn`) so a `jq` runtime failure at the emit
  point cannot silently swallow the block signal (#5610 pattern). The Stop handler emits the
  first block directly when the threshold is reached, then writes
  `no-progress-stop-block-emitted`, resets `no-progress-turns.count`, and exits 0 without
  processing more markers. `UserPromptSubmit` remains a fallback for already armed markers. The
  message includes the exact marker path (`<dir>/.bg-wait-active`) and all three recovery sidecar
  paths (`<dir>/no-progress-circuit-breaker-armed`, `<dir>/no-progress-turns.count`, and
  `<dir>/no-progress-stop-block-emitted`) so the operator does not have to guess the offending
  tmpdir (#5927).

## Threshold rationale

K=3 allows one or two spurious notification turns for legitimate recovery, then blocks before
users see the repeated empty-output loop as a visible storm.

## Harness

Covered by `scripts/test-hook-no-progress-guard.sh`, wired through
`make test-hook-no-progress-guard` and `make lint`.

## Update triggers

Update this file when: the event types handled change, the counter/breaker file names or locations
change, the threshold default changes, `is_step_completed` sentinel coverage changes, or the
clone-scoping identity sources (marker-local `CLONE_PATH`, fallback `.larch-keepalive`
`CLONE_PATH`) or the set of handlers that apply them changes.
