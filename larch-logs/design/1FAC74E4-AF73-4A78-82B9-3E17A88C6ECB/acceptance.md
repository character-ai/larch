## Acceptance

- `FIXER_TIER_ORDER` is `("claude", "codex", "cursor")`; the Claude fixer model resolves to `claude-opus-4-8`; Codex stays `gpt-5.5` (effort `high`) and Cursor stays `composer-2.5`. (`python/test_config.py`, `python/test_agents.py`)
- ship-pr CI fixing delegates to the agentic `ci agentic-fix` subprocess: one delegate per failure evaluation, ≤20 cycles of fix → local-verify → push → passive blocking `ci wait`, then `fix-exhausted` operator bail. Codex/Cursor are not used for role=fix. (`python/test_ci_agentic_fix.py`, `python/test_ci_monitor.py`)
- The agentic delegate requires `--repo-root` and runs all git/verify/push under it, reconstructs `RunContext` so pre-push run-log flush runs, enforces HEAD/forbidden-path/submodule guards and a non-empty `delta_paths` before push, and never spends LLM tokens monitoring CI. (`python/test_ci_agentic_fix.py`, `python/test_coder_delta_guards.py`)
- `launch-claude-ci` is write-capable (not `claude --print`); a new `launch-claude-lint-fix` launcher backs the checks.py Claude tier. (`python/test_agents.py`)
- `python/checks.py` `run_lint_fix` dispatches Claude → Codex → Cursor → `main-agent-required`, attempting Claude even on Claude-only hosts; `_head_change_invalid_after_dispatch` commit-acceptance is unchanged. (`python/test_checks.py`)
- `python/rebase.py` removes `_deterministic_prepass` and bump-path gating; conflicts route to the reordered single-shot per-tier loop with driver-side staging and edit-only model prompts; pre-push handoff is unconditional when enabled. (`python/test_rebase.py`, `python/test_errors.py`)
- `ci-fix-exhausted` classifies as unrecoverable (`RESUME_HINT=none`, retry cap 0) in `stall_recovery.py` and `stall-recovery-report.sh`, routing to Step 12d operator bail, not `step8-shippr`. (`python/test_stall_recovery.py`, `python/test_ship.py`, stall-recovery-report harnesses)
- Docs (external-reviewers, configuration-and-permissions, run-logs, skills, linting), SECURITY.md, and the implement references reflect the new policy; no stale version-bump-in-ship-pr or `ci-fix-exhausted → step8-shippr` prose remains.
- `make py-lint`, `make py-test`, and `make lint` all pass.
