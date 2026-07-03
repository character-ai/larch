## Proposed Design Outline

### Goals
- Stop `hook-bg-poll-guard.sh` from denying `Read`/`Bash`/`Monitor`/`TaskOutput` calls made by a spawned Claude subprocess (voter/reviewer/scout/drafter) just because a live `.bg-wait-active` marker exists somewhere under session dirs, even when that marker belongs to a different logical actor (the orchestrator's own background wait).
- Preserve the guard's original purpose: still deny the orchestrator's own polling/probing during its own immediate-background wait.
- Cover both `/design` and `/implement` automatically, since both dispatch Claude voters/reviewers through the same shared `_claude_runner.py` launch layer.

### Non-goals
- Not scoping the fix to Codex/Cursor subprocesses: confirmed via `SECURITY.md` that they never process `hooks.json` and are unaffected.
- Not a retrospective scan of historical run logs for blast radius: code fix only, per operator default.
- Not reworking `hook-no-progress-guard.sh`: a different Stop hook with its own already-fixed cross-clone bug (#5927, closed), unrelated mechanism to this PreToolUse cross-actor bug.

### Approach sketch
- Add a self-identifying env var (name TBD in plan, e.g. `LARCH_SUBPROCESS_REVIEWER=1`) defined once as a `Final` in `python/larch/core/config.py`.
- `_run_claude_with_stdin` in `_claude_runner.py` sets it in the spawned `claude --print` process's env; this single launcher already covers draft/scout/vote/review task kinds for both `/design` and `/implement`.
- `hook-bg-poll-guard.sh` checks for the var once near the top, immediately after the existing `LARCH_BG_POLL_GUARD_DISABLE` escape hatch, and exits 0 unconditionally when present, mirroring that existing pattern rather than patching individual tool-type branches.
- Update the sibling doc `scripts/hook-bg-poll-guard.md` and the `SECURITY.md` hook paragraph to document the new exemption.

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh`
- `python/larch/agents/_claude_runner.py`
- `python/larch/core/config.py`
- `scripts/hook-bg-poll-guard.md`, `scripts/test-hook-bg-poll-guard.sh`
- `SECURITY.md`

### Open questions
- None.
