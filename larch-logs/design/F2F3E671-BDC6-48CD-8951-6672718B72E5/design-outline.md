## Proposed Design Outline

### Goals
- Port the sourced-only external-agent launcher libs in-process into `python/agents.py`: the stderr-tail carrier, residual cursor-auth / launcher-common helpers, and the codex + claude drafter launchers.
- Cut every consumer to in-process / `cli.py` and fully retire all 7 bash libs, leaving `make lint-retired-scripts` clean.
- Preserve external-CLI invocation fidelity and the drafter status-KV + vendor-failure-diagnostics contracts.

### Non-goals
- No new launcher features; minor bash-wart cleanup only where observable behavior is unchanged.
- No cursor drafter (only codex + claude drafters exist); no re-port of functions already at native parity in `agents.py` (verify, then delete).
- No changes to the in-flight G11/G3 domains beyond a surgical `design_lifecycle.py` drafter-dispatch edit.

### Approach sketch
- Extend `python/agents.py` with the `lib-failed-agent-stderr-tail` carrier functions, any residual `lib-external-launcher-common` / `lib-cursor-auth` helpers, and `launch_codex_drafter` / `launch_claude_drafter`, mirroring the existing `launch_*_implement` / `launch_*_ci` pattern and registering `agent launch-codex-drafter` / `agent launch-claude-drafter` CLI verbs.
- Repoint `python/design_lifecycle.py` drafter dispatch from `scripts/launch-*-drafter.sh` to the new CLI verbs.
- Update `python/checks.py` launcher-lib checks (repoint or retire) and rewrite parity tests that currently source the bash.
- Delete the 7 libs plus their `.md` and `test-*.sh` siblings; append to `python/migrated-scripts.tsv`; fix doc references.

### Surfaces in scope
- `python/agents.py`, `python/cli.py` (registry), `python/design_lifecycle.py`, `python/checks.py`.
- Tests: `python/test_agents.py`, `python/test_checks.py`, `python/test_collect_results.py`, plus new drafter coverage.
- Retired `scripts/` libs + their `.md`/`test-*.sh`; `python/migrated-scripts.tsv`; docs (`configuration-and-permissions.md`, `run-logs.md`, `vendor-agent-diagnostics-audit.md`).

### Open questions
- None. Parity bar, deletion completeness, and scope were resolved in Round 1.
