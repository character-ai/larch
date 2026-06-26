## Proposed Design Outline

### Goals
- Stop the lint-fix Codex stall: when the sandbox blocks Codex's `exec_command` verify, fail in seconds, not after the full 300s `_RUN_EXTERNAL_TIMEOUT`.
- Unblock the reported lint-fix path so Codex's `checks run-relevant` verify runs and Codex finishes the fix itself.
- Give every `agent launch-codex-exec` caller the same fast-fail safety net through the shared choke point.

### Non-goals
- Do not broaden Codex's sandbox beyond least-privilege; keep `workspace-write` and bring the verify command's paths inside writable roots.
- Do not change `_RUN_EXTERNAL_TIMEOUT` (300s stays; it is shared by the Codex/Cursor/Claude lint-fix tiers).
- Do not touch read-only lanes (research, validation, voter, judge, OOS-combine, design drafter).

### Approach sketch
- Fast-fail (shared, the "fix all" lever): in `launch_codex_exec_main` (`python/agents.py`), scan the Codex `*.events.jsonl` stream for `exec_command failed` / `blocked by policy` and exit early as a policy-rejection failure, mapping to the existing `main-agent-required` / `dispatch-failed` path with budget saved.
- Unblock (lint-fix): in `_build_codex_argv` / `_run_codex` (`python/checks.py`), route the verify tmpdir into an already-writable root, or grant it via `--add-dir`, so `workspace-write` permits the `checks run-relevant` spawn.
- Other workspace-write callers (plan auto-fix, review-and-fix) already verify out-of-band after Codex exits, so they need only the shared fast-fail.

### Surfaces in scope
- `python/agents.py` — `launch_codex_exec_main` event-stream fast-fail.
- `python/checks.py` — `_build_codex_argv`, `_run_codex`, verify-tmpdir routing.
- `python/test_agents.py`, lint-fix harness — launcher + lint-fix regression coverage.
- `SECURITY.md` — note any exec/sandbox posture change.

### Open questions
- Exact rejection mechanism: out-of-workspace `/tmp` write target (likely, per the run's failure log) vs. wholesale `exec_command` block. Plan drafting confirms; the unblock adapts (add-dir / relocate vs. minimal grant) without broadening posture.
