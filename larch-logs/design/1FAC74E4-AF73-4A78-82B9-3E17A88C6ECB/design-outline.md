## Proposed Design Outline

### Goals
- Unify the coder-fixer order/model policy to **Claude/Opus-4.8 → Codex/gpt-5.5 → Cursor/composer-2.5** across both fixer surfaces.
- Make the ship-pr CI fixer **agentic**: a dedicated minimal-context Opus subprocess that loops fix → local-test → push → passive-CI-wait (≤20 cycles), then bails to the operator.
- Drop version-bump conflict handling from ship-pr; `/release` owns version bumping.

### Non-goals
- No agentic loop for conflict resolution (`rebase.py`) or the pre-ship lint-fix loop (`checks.py`); those get order/model only.
- No model change for Codex (`gpt-5.5`) or Cursor (`composer-2.5`); only the Claude tier moves to `claude-opus-4-8`.
- No reintroduction of an upfront ship-pr local checks/lint gate.

### Approach sketch
- `config.py`: reorder `FIXER_TIER_ORDER` → `("claude", "codex", "cursor")`; move the Claude fixer model default to `claude-opus-4-8`.
- `ci_monitor.py`: replace the role=fix waterfall with a delegated **agentic Opus fixer** that owns the fix/local-test/push/passive-CI-wait loop; exhaustion bails to operator (`ci-fix-exhausted`). Reuse existing helpers (`verify_job_locally`, `stage_and_push`, blocking CI wait) so the LLM never polls.
- `rebase.py`: delete `_deterministic_prepass` + bump-path gating; all conflicts go straight to the reordered single-shot waterfall.
- `checks.py`: add a Claude/Opus first tier in `run_lint_fix`; keep `main-agent-required` as the final fallback.

### Surfaces in scope
- `python/config.py`, `python/agents.py`, `python/ci_monitor.py`, `python/rebase.py`, `python/checks.py`.
- Tests: `test_config.py`, `test_agents.py`, `test_ci_monitor.py`, `test_rebase.py`, `test_checks.py`, launcher/review harnesses.
- `.md` sibling contracts and docs enumerating waterfall order or tier models.

### Open questions
- Passive-CI-wait + agentic-loop mechanism: reuse `ci_monitor`'s Python helpers driving a thin Opus subprocess, vs. hand the Opus subprocess a blocking CLI verb (resolve during plan drafting).
