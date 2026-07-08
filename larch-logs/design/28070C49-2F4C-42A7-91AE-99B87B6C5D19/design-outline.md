## Proposed Design Outline

### Goals
- Stop false-positive policy-rejection kills when Codex `aggregated_output` of completed commands contains phrases like "blocked by policy" or "Rejected(" from historical larch-log content.
- Keep fast-kill accurate for genuine rejection events in the Codex events stream.
- Fix the `run_logs.py` attempt-counter label so policy rejections report 0 retries.

### Non-goals
- Changing the Codex events stream format or protocol.
- Broader refactoring of `_run_external.py` beyond the watcher function.
- Fixing other retry or classification bugs not described in the issue.

### Approach sketch
- In `_codex_policy_rejection_excerpt`, parse the events tail as JSON lines; for each parseable line, check the event type to determine whether it is a genuine error surface (failed command event, error event, turn-failure payload) rather than `aggregated_output` of a completed command.
- Non-JSON lines (startup noise, partial writes) are skipped silently; no kill.
- In `run_logs.py`, correct the conditional so policy-rejection exec issues do not print non-zero retry counts.
- Update existing rejection tests to emit JSON-format fixture events; add a new regression test where `aggregated_output` contains trigger phrases but the process must not be killed.

### Surfaces in scope
- `python/larch/agents/_run_external.py` — `_codex_policy_rejection_excerpt` and related constants
- `python/larch/report/run_logs.py` — attempt counter suffix rendering
- `python/tests/agents/test_agents.py` — test fixtures and a new false-positive regression test

### Open questions
- None.
