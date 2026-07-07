## Decision 1: Remove the superseded pre-#5182 agentic fixer
- **Question**: The pre-#5182 agentic fixer (`python/larch/implement/ci_agentic_fix.py`) is still dispatchable via a `ci agentic-fix` verb but is no longer called by any skill or hook. Should this design remove it as part of replacing it?
- **Resolution**: Remove it now. Delete `ci_agentic_fix.py`, its `agentic-fix` dispatch/registration in `ci.py`, the three `ci_monitor.py` helpers used only by it (`_capture_baseline`, `_rollback_to_baseline`, `_delta_paths`), `test_ci_agentic_fix.py`, and stale `skill-closure-baseline.json` / `complexity-baseline.json` entries. Avoids two competing CI-fix code paths.
- **Source**: user

## Decision 2: Split attempt budget — fixer 20 rounds, main-agent fallback 10 attempts, no re-spawn
- **Question**: After the fixer sub-agent exhausts its rounds (or no-progress bail), the main-agent inline fallback takes over. How should the shared per-run-id attempt budget account for the whole fixer episode?
- **Resolution**: The spawned fixer sub-agent gets **20** rounds (not the issue's 30) to fix CI. After the fixer fails/exhausts, the main agent gets **10** inline attempts of its own. The main agent NEVER re-spawns the fixer sub-agent for the same job/run-id after it fails — it takes over and repairs inline per `ship-pr-ci-fix.md`. The fixer's 20-round cap and the main-agent's 10-attempt cap are distinct budgets coordinated on the shared per-run-id sentinel/counter surface. This supersedes the issue title/body "30 rounds" language: total effort is now 20 (sub-agent) + 10 (main agent).
- **Source**: user

## Hard constraints carried from the issue (confirmed, not re-asked)
- ship-pr keeps its immediate bail; #5182 behavior unchanged.
- Single-runner invariant: the fixer edits the same checkout; the main agent stays idle (notification-only) while the fixer task runs.
- On fixer success, the main agent clears the stale handoff and relaunches `step-8-ship.sh` for the merge phase.
- Non-goals: no wholesale local suites; no static job allowlist; no auto-rollback. Trust the fixer's push; CI judges it.
- Kill switch `LARCH_CI_FIXER=0` restores today's inline main-agent behavior (default = new fixer path on).
