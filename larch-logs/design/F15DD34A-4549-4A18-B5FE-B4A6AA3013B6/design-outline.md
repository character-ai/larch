## Proposed Design Outline

### Goals
- Port the external-agent launcher framework (~4.5k bash LOC across 19 scripts) into `python/agents.py` and possibly `python/launcher.py`, exposing importable functions and CLI verbs via `python/cli.py`
- Retire all 14 executable B4 bash scripts; update their direct bash callers to use `python3 cli.py agent ...` instead
- Preserve the 5 sourced-only lib files as bash (not retired in B4); each C-phase issue owns the lib retirement when it rewrites its last consumer

### Non-goals
- Rewriting `launch-codex-implement.sh` / `launch-cursor-implement.sh` beyond minimal executable-path updates (C4b owns full rewrite)
- Deleting or retiring sourced-only lib files (`lib-external-launcher-common.sh`, `lib-cursor-launcher-common.sh`, `lib-cursor-auth.sh`, etc.) in B4
- Porting `launch-review.sh`, `dispatch-with-waterfall.sh`, `collect-agent-results.sh` (C1a scope)

### Approach sketch
- Extend `python/agents.py` with functions for model-args resolution, Cursor auth, cursor-wrap-prompt, run-external-agent loop, degraded-tools gate, and per-tool launchers (codex-ci, cursor-ci, claude-ci, claude-review, claude-subprocess, codex-exec)
- Register CLI verbs under `python/cli.py` domain `agent` (e.g., `agent model-args`, `agent run-external-agent`, `agent launch-codex-ci`, etc.)
- Call B2 (`timing`, `token`) and B3 (`run-log`) Python functions directly (no subprocess) inside the ported launchers
- Update surviving bash callers with minimal path substitutions; post notes on C-phase issues about lib retirement

### Surfaces in scope
- `python/agents.py` (extend)
- `python/cli.py` (add `agent` domain verbs)
- `python/test_agents.py` (new colocated pytest)
- `python/migrated-scripts.tsv` (add 14 retired executables)
- `scripts/launch-review.sh`, `scripts/lint-fix-loop.sh`, `scripts/dispatch-plan-voters.sh`, `scripts/dispatch-code-voters.sh`, `scripts/dispatch-with-waterfall.sh`, `scripts/run-negotiation-round.sh`, `scripts/launch-codex-drafter.sh`, `scripts/ship-pr.sh`, `scripts/check-reviewers.sh` (minimal executable-path updates)
- `scripts/launch-codex-implement.sh`, `scripts/launch-cursor-implement.sh` (minimal executable-path updates only)
- 14 executable bash scripts to delete + 2 test harnesses to port to pytest
- C-phase issues: comments added for lib-retirement responsibility

### Open questions
- Should the Python port of `run-external-agent.sh` (background-process monitoring with PID polling and periodic progress) use `subprocess.run` with a timeout or a full async/threading approach? (architectural, for sketch phase)
