## Goal
Implement issue #5448: [IMPLEMENTING] [BUG] dispatch_voters: cursor voter 1 blocks voters 2+3 — all three should launch in parallel.

## Implementation Plan
## Summary

In `python/agent_voters.py`, `dispatch_voters()` serializes Cursor voter 1 ahead of Codex voters 2 and 3 whenever Cursor is available. `_launch_voter1_cursor_only()` calls `proc.run()` — a blocking/synchronous call — so voter 1 must complete before the code reaches the waterfall dispatch that launches voters 2 and 3. All three voters are supposed to run in parallel, which is what happens correctly when Cursor is *unavailable* (the Claude fallback path uses `subprocess.Popen()` and is non-blocking). The wall-clock cost of voter 1's full execution (89s in round 1, 52s in round 2 in observed runs) is wasted latency added to every review round when Cursor is present.

## Original report

Gantt chart from two consecutive review rounds shows `cursor/validity-vote` always running solo first, and both codex voters launching simultaneously at exactly the moment cursor exits — across both rounds. The user correctly identified that this is a dependency, not latency: the two codex voters start at precisely the tick cursor/validity-vote completes, reproducibly.

## Reproduction scenario

1. Run `/implement` on any issue with both Cursor and Codex available.
2. Inspect the per-round Gantt timing chart in the final summary.
3. Observe `cursor/validity-vote` bar ending before `codex/plan-fidelity-vote` and `codex/pragmatism-vote` bars begin. Both codex bars start at the same tick, which equals the end tick of the cursor bar.

Alternatively: add timing instrumentation around lines 498–520 in `python/agent_voters.py` and confirm `_launch_voter1_cursor_only` returns before `_dispatch_waterfall` is called.

## Expected behavior

All three voters (cursor/validity-vote, codex/plan-fidelity-vote, codex/pragmatism-vote) launch concurrently and run in parallel. Total voter wall-clock time equals the slowest single voter, not voter-1-time + max(voter-2-time, voter-3-time).

## Observed behavior

When Cursor is available:
1. Voter 1 (cursor/validity-vote) launches and blocks until complete.
2. Only then do voters 2 and 3 (codex/plan-fidelity-vote and codex/pragmatism-vote) launch together.

When Cursor is unavailable (Claude fallback):
1. Voter 1 (Claude) launches asynchronously via `subprocess.Popen()`.
2. Voters 2 and 3 launch immediately after.
3. All three run in parallel correctly.

## Root cause analysis

`_launch_voter1_cursor_only()` (line 222, `python/agent_voters.py`) uses `proc.run()`, which blocks until the subprocess exits and returns an `int` rc. By contrast, `_launch_claude_voter()` (line 188) uses `subprocess.Popen()`, which is non-blocking and returns a `Popen` object.

In `dispatch_voters()` (line 481):
- Cursor path (line 498–501): calls `_launch_voter1_cursor_only()` → blocks → sets `voter1_process = None`.
- Voters 2+3 dispatch (line 518–520): only reached *after* voter 1 returns.
- Claude path (line 503–507): calls `_launch_claude_voter()` → returns immediately → voters 2+3 launch in parallel → voter 1 is waited on at line 534–535 after all are in flight.

The asymmetry is purely in the Cursor vs Claude launch function: one uses `proc.run()` (blocking), the other `subprocess.Popen()` (non-blocking).

## Evidence

- `python/agent_voters.py` line 225: `result = proc.run(...)` in `_launch_voter1_cursor_only` — synchronous.
- `python/agent_voters.py` line 191: `return subprocess.Popen(...)` in `_launch_claude_voter` — asynchronous.
- `python/agent_voters.py` lines 498–501: cursor path assigns `voter1_rc` (int) directly from the blocking call and sets `voter1_process = None`.
- `python/agent_voters.py` lines 503–507: Claude path assigns `voter1_process` (Popen) and sets `voter1_rc = -1` (to be filled later at line 534–535).
- `python/agent_voters.py` line 518: voters 2+3 waterfall dispatch runs unconditionally after the voter-1 launch block, meaning it only starts after voter 1 has already completed on the Cursor path.
- Gantt charts from two observed review rounds: cursor/validity-vote bar ends at the exact pixel where codex/plan-fidelity-vote and codex/pragmatism-vote bars begin, reproducibly.

## Affected files

- `python/agent_voters.py` — `_launch_voter1_cursor_only()` and `dispatch_voters()` contain the root cause.
- `python/test_agent_voters.py` — tests may need updating to cover the parallel-launch contract on the Cursor path.

## Suggested fix(es)

Change `_launch_voter1_cursor_only()` to be non-blocking: use `subprocess.Popen()` instead of `proc.run()` and return a `Popen[bytes]` object (same signature as `_launch_claude_voter()`). In `dispatch_voters()`, unify the two voter-1 launch branches so both assign a `Popen` object to `voter1_process`. Move the waterfall dispatch for voters 2+3 to immediately after voter 1 is *launched* (not after it completes), then wait for all three at the existing `_wait_sentinels` call. The existing `voter1_process.wait()` at line 534–535 already handles the Claude path correctly and would handle the Cursor path the same way after this change.

Specifically:
1. Rename/refactor `_launch_voter1_cursor_only` to return `subprocess.Popen[bytes]` using the same `subprocess.Popen` pattern as `_launch_claude_voter`, forwarding the `--timing-task-kind cursor-code-voter-validity` arg.
2. In `dispatch_voters`, remove the `if cursor_present / else` split for voter-1 launch return type. Both paths set `voter1_process = Popen(...)` and `voter1_rc = -1`.
3. Move the `if external_voter23:` waterfall dispatch block to directly follow the unified voter-1 launch (before any wait).
4. The existing `if voter1_process is not None: voter1_rc = voter1_process.wait()` at line 534 then naturally covers both Cursor and Claude paths.

## Open questions

- Is the serial ordering of voter 1 before voters 2+3 intentional for any reason (e.g., voter 1 output gates what voters 2+3 receive)? The ballot/prompt construction at lines 494–496 happens before any voter launches, so no voter-1 output is fed into voter-2/3 prompts today.
- Should `_dispatch_waterfall` (which is also a blocking `proc.run()`) be made non-blocking as well, or does it internally manage its own parallelism for the two slots it handles?

## Test plan
(no test plan section in plan-file)
